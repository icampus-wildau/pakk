from __future__ import annotations

import logging
import os
import re

import pytz
from github import Github
from github.ContentFile import ContentFile
from github.Organization import Organization
from github.PaginatedList import PaginatedList
from github.Repository import Repository

from pakk.args.install_args import InstallArgs
from pakk.config.main_cfg import MainConfig
from pakk.helper.progress import ProgressManager
from pakk.helper.progress import TaskPbar
from pakk.helper.progress import execute_process_and_display_progress
from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.cache import CachedRepository
from pakk.modules.connector.cache import CachedTag
from pakk.modules.connector.git_generic import GenericGitHelper
from pakk.modules.connector.github.config import GithubConfig
from pakk.pakkage.core import ConnectorAttributes
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)


class GithubConnector(Connector):
    CONFIG_CLS = GithubConfig

    def __init__(self):
        super().__init__()
        self.config = GithubConfig.get_config()

        self._token = self.config.private_token.value

        # TODO: Catch connection exceptions
        self._github = Github(self._token)

    def get_organization(self, name: str) -> Organization:
        return self._github.get_organization(name)

    def get_repos_of_organization(self, organization: Organization) -> PaginatedList[Repository]:
        return organization.get_repos()

    def get_repo(self, name: str) -> Repository:
        return self._github.get_repo(name)

    def get_cache_dir_path(self):
        return self.config.cache_dir.value

    def get_repo_cache_file_path(self, repo: Repository) -> str:
        name = repo.full_name.replace("/", "_")
        return os.path.join(self.get_cache_dir_path(), name + ".json")

    def _get_cached_repo(
        self, repo: Repository, existing_cached_repo: CachedRepository | None = None
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

    def _update_cache(self, pakkage_ids: list[str] | None = None):
        """Helper method to update the cached projects"""

        # Discovering on GitHub only works for known organizations
        org_names = self.config.cached_organizations.value

        # Add new organizations if pakkage_ids are given
        if pakkage_ids is not None:
            for id in pakkage_ids:
                splits = id.split("/")
                if len(splits) == 2:
                    org_name, repo_name = splits
                    if org_name not in org_names:
                        logger.info(f"Adding organization '{org_name}' to cache")
                        org_names.append(org_name)

        # Write back the updated organizations
        self.config.cached_organizations.value = org_names

        if len(org_names) == 0:
            logger.info("No organizations to discover. Specify Github-Pakk-IDs to cache github projects.")
            return

        logger.info(f"Updating GitHub cache...")

        for org_name in org_names:
            # Find the organization
            logger.debug(f"Updating cache for organization '{org_name}':")
            org = self._github.get_organization(org_name)

            # # List all repos in the organization
            # for repo in org.get_repos():

            def process_repo(repo: Repository):
                # Load the cached repository
                cache_file_path = self.get_repo_cache_file_path(repo)
                if InstallArgs.get().clear_cache:
                    cache_file = None
                else:
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

            n_public = org.total_private_repos or 0
            n_private = org.public_repos or 0

            execute_process_and_display_progress(
                items=org.get_repos(),
                item_processing_callback=process_repo,
                num_workers=int(self.config.num_discover_workers.value),
                item_count=n_public + n_private,
                message=f"Updating github cache for {org_name}",
            )

    def discover(self, pakkage_ids: list[str] | None) -> PakkageCollection:
        discovered_pakkages = PakkageCollection()
        logger.info("Discovering projects from GitHub")

        self._update_cache(pakkage_ids)
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
            num_workers=self.config.num_fetcher_workers.value,
            summary_description="[blue]Fetching pakkages from GitHub:",
            worker_description="[cyan]Fetcher {}:",
            text_fields=["pakkage", "info"],
        )

        manager.execute()

    @staticmethod
    def get_github_http_with_token(http_url_to_repo: str, token: str | None = None) -> str:
        """
        Return the http url with the token directly in the url included.
        For Github the form is the following: https://oauth2:{token}@{http_url}
        See: https://stackoverflow.com/questions/42148841/github-clone-with-oauth-access-token

        Parameters
        ----------
        http_url_to_repo: str
            The http url to the git repo.
        token: str
            The token to use for authentication.

        Returns
        -------
        str: The http url with the token included.

        """
        if token is None:
            token = GithubConfig.get_config().private_token.value

        http = re.sub(r"https+://", "", http_url_to_repo)
        return f"https://oauth2:{token}@{http}"

    def checkout_version(self, target_version: PakkageConfig, task: TaskPbar) -> None:

        # Check if gitlab attributes are set
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

        # Get the url to download the repository
        url_with_token = self.get_github_http_with_token(url)

        # Fetch the pakkage version
        GenericGitHelper.fetch_pakkage_version_with_git(target_version, url_with_token, tag, task)
