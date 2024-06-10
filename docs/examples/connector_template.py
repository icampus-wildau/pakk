from __future__ import annotations

import logging
import os

import pytz
from extended_configparser.configuration.entries.section import ConfigSection
from github.ContentFile import ContentFile
from github.Repository import Repository

from pakk.config.base import ConnectorConfiguration
from pakk.config.main_cfg import MainConfig
from pakk.helper.progress import ProgressManager
from pakk.helper.progress import TaskPbar
from pakk.helper.progress import execute_process_and_display_progress
from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.cache import CachedRepository
from pakk.modules.connector.cache import CachedTag
from pakk.pakkage.core import ConnectorAttributes
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)


class MyConnectorConfig(ConnectorConfiguration):
    NAME = "my_connector.cfg"

    def __init__(self):
        super().__init__()

        self.section = ConfigSection("MyConnector")
        self.enabled = self.section.ConfirmationOption("enabled", True, "Enable the connector", inquire=True)

        self.private_token = self.section.Option(
            "private_token",
            "",
            "Private token for the Connector",
            value_getter=lambda x: None if (x == "" or x.lower() == "none") else x,
            inquire=self.is_enabled,
        )

        self.cache_dir = self.section.Option(
            "cache_dir",
            r"${Pakk.Subdirs:cache_dir}/my_connector",
            "Directory for the cache files",
            inquire=False,
            is_dir=True,
        )

    def is_enabled(self) -> bool:
        return self.enabled.value


class MyConnector(Connector):
    CONFIG_CLS = MyConnectorConfig

    def __init__(self):
        super().__init__()
        self.config = MyConnectorConfig.get_config()

        self._token = self.config.private_token.value

    def get_cache_dir_path(self):
        return self.config.cache_dir.value

    def get_repo_cache_file_path(self, repo: Repository) -> str:
        name = repo.full_name.replace("/", "_")
        return os.path.join(self.get_cache_dir_path(), name + ".json")

    def _get_cached_repo(
        self, repo: "RepositoryObject", existing_cached_repo: CachedRepository | None = None
    ) -> CachedRepository:

        cached_repo = existing_cached_repo or CachedRepository()
        pakk_cfg_file_name = MainConfig.get_config().pakk_cfg_files[0]

        cached_repo.id = repo.full_name
        cached_repo.url = repo.clone_url
        cached_repo.last_activity = repo.pushed_at

        # Get all tags, skip if the tag is already in the cache
        for tag in repo.get_tags():
            if tag.name in cached_repo.tags:
                logger.debug(f"Tag {tag.name} already in cache")
                continue

            commit = tag.commit
            if commit is None:
                continue

            # Check if the tag is a pakk version
            pakk_config_str = ""
            is_pakk_version = False
            try:
                # Get root directory contents
                contents: list[ContentFile] = repo.get_contents("", ref=tag.name)  # type: ignore
                file_exists = any(file.path == pakk_cfg_file_name for file in contents)
                if file_exists:
                    file_content: ContentFile = repo.get_contents(pakk_cfg_file_name, ref=tag.name)  # type: ignore
                    pakk_config_str = file_content.decoded_content.decode("utf-8")
                    is_pakk_version = True

                logger.debug(f"\t Added {tag.name} (pakk version: {is_pakk_version})")
            except Exception as e:
                logger.warning(f"Error checking file presence in tag {tag.name} of repo {repo.name}: {str(e)}")

            cached_tag = CachedTag()
            cached_tag.tag = tag.name
            cached_tag.commit = commit.sha
            cached_tag.last_activity = tag.commit.commit.committer.date
            cached_tag.pakk_config_str = pakk_config_str
            cached_tag.is_pakk_version = is_pakk_version

            cached_repo.tags[tag.name] = cached_tag

        return cached_repo

    def _update_cache(self):
        """Helper method to update the cached projects"""

        # Connect to the Connector
        # Search for changed projects
        # Update the cache by storing CachedRepository

        def process_repo(repo: "RepositoryObject"):
            # Load the cached repository
            cache_file_path = self.get_repo_cache_file_path(repo)
            cache_file = CachedRepository.from_file(cache_file_path)

            repo_dt = repo.pushed_at
            if repo_dt.tzinfo is None:
                repo_dt = pytz.utc.localize(repo_dt)

            if cache_file is not None and repo_dt <= cache_file.last_activity:
                # Use cached repository
                logger.debug(f"Using cached repository for {repo.name}")
                return

            logger.debug(f"Updating cache for repo {repo.name}")

            cache_file = self._get_cached_repo(repo, cache_file)
            cache_file.write(cache_file_path)

        repos = self.get_repos()
        execute_process_and_display_progress(
            items=repos,
            item_processing_callback=process_repo,
            num_workers=4,
            item_count=len(repos),
            message=f"Updating connector cache",
        )

    def discover(self, pakkage_ids: list[str] | None = None) -> PakkageCollection:
        discovered_pakkages = PakkageCollection()
        logger.info("Discovering projects from MyConnector")

        self._update_cache()
        repos = CachedRepository.from_directory(self.get_cache_dir_path())

        n_repos, n_tags, n_pakk = 0, 0, 0

        for repo in repos:
            n_repos += 1
            pakkage_versions = PakkageVersions()
            for tag in repo.tags.values():
                n_tags += 1
                if not tag.is_pakk_version:
                    continue

                n_pakk += 1

                pakk_cfg = tag.pakk_config
                # Set attributes for the fetch process
                attr = ConnectorAttributes()
                attr.url = repo.url
                attr.branch = tag.tag
                attr.commit = tag.commit
                pakk_cfg.set_attributes(self, attr)

                pakkage_versions.available[tag.version] = pakk_cfg

            if len(pakkage_versions.available) == 0:
                continue

            pakkage = Pakkage(pakkage_versions)
            discovered_pakkages[pakkage.id] = pakkage

        logger.info(f"Discovered {n_repos} repositories with {n_tags} tags, {n_pakk} pakk versions")

        return discovered_pakkages

    def fetch(self, pakkages_to_fetch: list[PakkageConfig]):

        manager = ProgressManager(
            items=pakkages_to_fetch,
            item_processing_callback=self.checkout_version,
            num_workers=4,
            summary_description="[blue]Fetching pakkages from GitHub:",
            worker_description="[cyan]Fetcher {}:",
            text_fields=["pakkage", "info"],
        )

        manager.execute()

    def checkout_version(self, target_version: PakkageConfig, task: TaskPbar) -> None:

        # Check if connector attributes from the fetch process are set
        attr = target_version.get_attributes(self)
        if attr is None:
            logger.error(f"Connector {self.__class__} not in target_version.connector_attributes")
            # return target_version
            return

        url = attr.url
        tag = attr.branch

        if url is None or tag is None:
            logger.error(f"URL or tag is None for {target_version.id}: {url}@{tag}")
            # return target_version
            return

        # Fetch the target version
        fetched_dir = MainConfig.get_config().paths.fetch_dir.value
        name = target_version.basename
        path = os.path.join(fetched_dir, name)

        self._fetch_to_path(target_version, url, tag, path)

        # Set the state to fetched and the local_path
        target_version.state.install_state = PakkageInstallState.FETCHED
        target_version.local_path = path
