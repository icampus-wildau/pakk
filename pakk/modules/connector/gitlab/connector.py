from __future__ import annotations

import base64
import inspect
import logging
import os
import re
import subprocess
from datetime import datetime
from multiprocessing.pool import ThreadPool

import gitlab
import gitlab.v4.objects as gl_objects
import pytz
from requests import ConnectTimeout
from rich.progress import BarColumn
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TextColumn
from rich.progress import TimeElapsedColumn
from rich.progress import TimeRemainingColumn

from pakk.args.install_args import InstallArgs
from pakk.config.main_cfg import MainConfig
from pakk.helper.file_util import remove_dir
from pakk.helper.progress import ProgressManager
from pakk.helper.progress import TaskPbar
from pakk.helper.progress import execute_process_and_display_progress
from pakk.logger import console
from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.cache import CachedRepository
from pakk.modules.connector.cache import CachedTag
from pakk.modules.connector.git_generic import GenericGitHelper
from pakk.modules.connector.gitlab.config import GitlabConfig
from pakk.modules.module import Module
from pakk.pakkage.core import ConnectorAttributes
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)

CACHING_VERSION = "0.2.0"

ATTR_GITLAB_HTTP_SOURCE = "gitlab_http"
ATTR_GITLAB_SOURCE_TAG = "gitlab_tag"


class GitlabConnector(Connector):

    CONFIG_CLS = GitlabConfig

    gl_instance: gitlab.Gitlab | None = None

    def __init__(self, pakkages: PakkageCollection, **kwargs):
        super().__init__(pakkages)

        logger.info("Initilizing GitLab connector...")
        self.config = GitlabConfig.get_config()

        self.gl = self.get_gitlab_instance()
        self.connected = False
        try:
            self.gl.auth()
            self.connected = True
        except ConnectTimeout as e:
            logger.error("Failed to connect to gitlab: %s", e)
            pass

        # Progress object for pbars
        self._pbar_progress = None
        # Pbar tasks for multiple workers
        self._pbars = []
        # Array storing free pbar indices, workers select the next free index
        self._free_pbars = []

    @staticmethod
    def get_gitlab_instance() -> gitlab.Gitlab:
        # private token or personal token authentication (self-hosted GitLab instance)
        if GitlabConnector.gl_instance is not None:
            return GitlabConnector.gl_instance

        c = GitlabConfig.get_config()

        # Get the signature of the object constructor
        signature = inspect.signature(gitlab.Gitlab.__init__)

        # Create dictionary with the arguments for the constructor
        # init_dict = dict(c["GitLab.Connection"])
        # for key in set(init_dict.keys()) - set(signature.parameters.keys()):
        #     if key in init_dict:
        #         del init_dict[key]

        # gl = gitlab.Gitlab(**init_dict)
        gl = gitlab.Gitlab.from_config("GitLab.Connection", [c.get_path()])
        return gl

    @staticmethod
    def get_gitlab_http_with_token(http_url_to_repo: str, token: str | None = None):
        """
        Return the http url with the token directly in the url included.
        For GitLab the form is the following: https://oauth2:{token}@{http_url}

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
            token = GitlabConfig.get_config().private_token.value

        http = re.sub(r"https+://", "", http_url_to_repo)
        return f"https://oauth2:{token}@{http}"

    def get_cache_dir_path(self):
        return self.config.cache_dir.value

    def get_repo_cache_file_path(self, repo: gl_objects.GroupProject) -> str:
        name = (str(repo.attributes["id"]) + "_" + repo.attributes["name"]).replace("/", "_")
        # name = repo.full_name.replace("/", "_")
        return os.path.join(self.get_cache_dir_path(), name + ".json")

    @staticmethod
    def datetime_string_to_datetime(s: str) -> datetime:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt

    def _get_cached_repo(
        self, project: gl_objects.GroupProject, existing_cache_project: CachedRepository | None
    ) -> CachedRepository:
        """
        Load the project from the cache or from the gitlab api if cached version
        is deprecated and cache it.

        Parameters
        ----------
        project: GroupProject
            The project object from the gitlab groups api

        Returns
        -------
        tuple[CachedProject, bool]
            The cached project and a boolean if the project was loaded from the cache

        """

        cache_project = existing_cache_project or CachedRepository()
        cache_project.id = project.attributes["id"]
        cache_project.url = project.attributes["http_url_to_repo"]
        cache_project.last_activity = GitlabConnector.datetime_string_to_datetime(
            project.attributes["last_activity_at"]
        )

        pakk_files = MainConfig.get_config().pakk_cfg_files

        # Load project to access tags
        gl_project = self.gl.projects.get(cache_project.id)
        tags = gl_project.tags.list()
        for tag in tags:

            tag_str = tag.attributes["name"]
            last_activity = GitlabConnector.datetime_string_to_datetime(tag.attributes["commit"]["committed_date"])

            if tag_str in cache_project.tags and cache_project.tags[tag_str].last_activity >= last_activity:
                continue

            cached_tag = CachedTag()
            cached_tag.tag = tag_str
            cached_tag.commit = tag.attributes["commit"]["id"]
            cached_tag.last_activity = last_activity

            # Load the pakk information from the tag
            # TODO: http.client.RemoteDisconnected: Remote end closed connection without response
            # TODO: urllib3.exceptions.ProtocolError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
            # TODO: requests.exceptions.ConnectionError ("Connection aborted.", ...)
            repo_tree = gl_project.repository_tree(ref=cached_tag.commit, all=True)

            for item in repo_tree:
                if item["name"] in pakk_files:
                    file_info = gl_project.repository_blob(item["id"])
                    file_content = base64.b64decode(file_info["content"])  # type: ignore
                    pakk_content_str = file_content.decode("utf-8")
                    # pakk_cfg = PakkageConfig.from_string(pakk_content_str)

                    cached_tag.pakk_config_str = pakk_content_str
                    cached_tag.is_pakk_version = True
                    cache_project.tags[cached_tag.tag] = cached_tag
                    break
                    # if pakk_cfg is None:
                    #     logger.warning("Failed to load pakk configuration from %s", item["name"])
                    #     continue
            # else:
            #     logger.warning("Failed to load pakk configuration from %s", item["name"])

        return cache_project

    def _update_cache(self) -> list[CachedRepository]:
        """Helper method to update the cached projects"""
        cached_projects: list[CachedRepository] = list()
        if not self.connected:
            logger.warning("Failed to connect to gitlab. Skipping discovery")
            return cached_projects

        num_workers = int(self.config.num_discover_workers.value)
        main_group_id = int(self.config.group_id.value)

        logger.info("Updating GitLab cache...")
        logger.debug(f"Main group id: {main_group_id}")
        logger.debug(f"Including archived projects: {self.config.include_archived.value}")
        logger.debug(f"Using {num_workers} workers" if num_workers > 1 else None)

        main_group = self.gl.groups.get(main_group_id)

        projects = main_group.projects.list(iterator=True, get_all=True, include_subgroups=True)
        include_archived = self.config.include_archived.value

        logger.debug(f"Looking at {len(projects)} projects...")

        filtered_group_projects: list[gl_objects.GroupProject] = list(
            filter(lambda gp: include_archived or not gp.attributes.get("archived"), projects)
        )  # type: ignore

        def project_processing(gp: gl_objects.GroupProject):
            cache_file_path = self.get_repo_cache_file_path(gp)
            cached_project = CachedRepository.from_file(cache_file_path)

            repo_dt = self.datetime_string_to_datetime(gp.attributes["last_activity_at"])

            if cached_project is not None and cached_project.last_activity >= repo_dt:
                logger.debug(f"Skipping {gp.attributes['name']} because it is up to date.")
                cached_projects.append(cached_project)
                return

            logger.debug(f"Updating cache for Gitlab repo {gp.attributes['name']}")

            cached_project = self._get_cached_repo(gp, cached_project)
            if cached_project is not None:
                cached_project.write(cache_file_path)
                cached_projects.append(cached_project)

        execute_process_and_display_progress(
            items=filtered_group_projects,
            item_processing_callback=project_processing,
            num_workers=num_workers,
            message="Updating gitlab cache",
        )

        return cached_projects

    def discover(self) -> PakkageCollection:
        discovered_pakkages = PakkageCollection()
        if not self.connected:
            logger.warning("Failed to connect to gitlab. Skipping discovery")
            return discovered_pakkages

        logger.info("Discovering projects from GitLab")

        cached_projects = self._update_cache()
        n_projects = 0
        n_tags = 0
        n_pakk = 0

        for project in cached_projects:
            pakkage_versions = PakkageVersions()
            is_valid_pakkage = False
            n_projects += 1
            for tag in project.tags.values():
                n_tags += 1
                if not tag.is_pakk_version:
                    continue

                n_pakk += 1
                pakk_cfg = tag.pakk_config

                # Set attributes for the fetch process
                attr = ConnectorAttributes()
                attr.url = project.url
                attr.branch = tag.tag
                attr.commit = tag.commit
                pakk_cfg.set_attributes(self, attr)

                pakkage_versions.available[pakk_cfg.version] = pakk_cfg
                is_valid_pakkage = True

            if is_valid_pakkage:
                pakkage = Pakkage(pakkage_versions)
                discovered_pakkages[pakkage.id] = pakkage

        logger.info(f"Discovered {n_projects} gitlab projects with {n_tags} tags ({n_pakk} pakk versions)")

        return discovered_pakkages

    # def _checkout_version(self, target_version: PakkageConfig) -> PakkageConfig:

    #     # Get the next free pbar
    #     pbar_index = self._free_pbars.index(True)
    #     # Acquire the pbar
    #     self._free_pbars[pbar_index] = False
    #     # Get the related pbar
    #     pbar = self._pbars[pbar_index]

    #     attr = target_version.get_attributes(self)

    #     if attr is None:
    #         logger.error(f"Connector {self.__class__} not in target_version.connector_attributes")
    #         return target_version

    #     url = attr.url
    #     tag = attr.branch
    #     fetched_dir = MainConfig.get_config().paths.fetch_dir.value

    #     if url is None or tag is None:
    #         logger.error(f"URL or tag is None for {target_version.id}: {url}@{tag}")
    #         return target_version

    #     url_with_token = self.get_gitlab_http_with_token(url)

    #     name = target_version.basename
    #     path = os.path.join(fetched_dir, name)

    #     fetch = True
    #     if os.path.exists(path):
    #         if self.install_args.refetch or self.install_args.clear_cache:
    #             logger.debug(f"Directory {path} already exists. Refetching it.")

    #             # delete existing directory
    #             remove_dir(path)
    #         else:
    #             # Check if the directory is empty
    #             with os.scandir(path) as it:
    #                 if not any(it):
    #                     fetch = True
    #                     logger.debug(f"Directory {path} already exists but is empty. Refetching it.")
    #                     remove_dir(path)
    #                 else:
    #                     fetch = False
    #                     logger.debug(f"Directory {path} already exists. Skipping fetch and using local version.")

    #     if fetch:
    #         os.makedirs(path, exist_ok=True)

    #         # Clone the repository
    #         # -c advice.detachedHead=false is for ignoring the warning about detached HEAD
    #         # We don't need git history, so we use --depth=1
    #         # The --progress option is required to get the continuous progress output
    #         cmd = f"git clone -c advice.detachedHead=false --depth=1 --branch {tag} {url_with_token} {name} --progress"
    #         retry_count = 2
    #         tries = 0

    #         while tries < retry_count:
    #             with subprocess.Popen(
    #                 cmd,
    #                 cwd=fetched_dir,
    #                 shell=True,
    #                 stdout=subprocess.PIPE,
    #                 stderr=subprocess.STDOUT,
    #                 bufsize=1,
    #                 universal_newlines=True,
    #             ) as p:

    #                 # Capture the output of the subprocess to print the info in the pbar
    #                 for line in p.stdout:
    #                     self._pbar_progress.update(pbar, pakkage=target_version.id, info=line.strip().replace("\r", ""))

    #             if PakkageConfig.from_directory(path):
    #                 break

    #             tries += 1
    #             if tries < retry_count:
    #                 logger.warning(f"Fetch of {target_version.id} failed. Retrying...")

    #     # Load the PakkageConfig from the fetched directory
    #     if PakkageConfig.from_directory(path) is None:
    #         raise Exception(f"Could not load PakkageConfig from {path}")

    #     # Set the state to fetched and the local_path
    #     target_version.state.install_state = PakkageInstallState.FETCHED
    #     target_version.local_path = path

    #     self._free_pbars[pbar_index] = True
    #     self._pbar_progress.update(pbar, pakkage="Done", info="")
    #     return target_version

    # def checkout_target_version(self, pakkage: Pakkage) -> Pakkage | None:
    #     target_version = pakkage.versions.target
    #     if target_version is None:
    #         raise Exception(f"Target version of {pakkage.name} is None.")

    #     self._checkout_version(target_version)
    #     return pakkage

    # def _fetch(self, pakkages_to_fetch: list[PakkageConfig]):
    #     Module.print_rule(f"Fetching pakkages from GitLab")

    #     self.install_args = InstallArgs.get()

    #     num_workers = int(self.config.num_fetcher_workers.value)

    #     # packages_to_fetch = [pakkage for pakkage in self.pakkages.values() if pakkage.versions.is_update_candidate()]
    #     # packages_to_fetch = pakkages.pakkages_to_fetch.values()

    #     # try:
    #     if len(pakkages_to_fetch) == 0:
    #         logger.info("No pakkages to fetch.")
    #         # return pakkages
    #         return

    #     with Progress(
    #         SpinnerColumn(),
    #         TextColumn("[progress.description]{task.description}"),
    #         BarColumn(),
    #         # TaskProgressColumn(),
    #         MofNCompleteColumn(),
    #         TimeRemainingColumn(),
    #         TimeElapsedColumn(),
    #         TextColumn("{task.fields[pakkage]}"),
    #         TextColumn("{task.fields[info]}"),
    #         transient=True,
    #         console=console,
    #     ) as progress:
    #         self._pbar_progress = progress

    #         pbar = progress.add_task("[blue]Fetching Total:", total=len(pakkages_to_fetch), pakkage="", info="")

    #         if num_workers > 1:
    #             num_workers = min(num_workers, len(pakkages_to_fetch))
    #             for i in range(num_workers):
    #                 self._pbars.append(progress.add_task(f"[cyan]Worker{i + 1}:", total=None, pakkage="", info=""))
    #                 self._free_pbars.append(True)

    #             # Don't use multiprocessing.Pool since it will spawn new processes and not threads,
    #             # thus the data will not be shared.
    #             # See:
    #             # https://stackoverflow.com/questions/3033952/threading-pool-similar-to-the-multiprocessing-pool
    #             # https://stackoverflow.com/questions/52486811/how-to-properly-reference-to-instances-of-a-class-in-multiprocessing-pool-map
    #             # https://towardsdatascience.com/demystifying-python-multiprocessing-and-multithreading-9b62f9875a27
    #             with ThreadPool(num_workers) as pool:
    #                 for res in pool.imap_unordered(self.checkout_version, pakkages_to_fetch):
    #                     progress.update(pbar, advance=1, info="")
    #                     if res is not None:
    #                         logger.info(f"Fetched {res.name}.")
    #                         # pakkages.fetched(res)
    #             pool.join()
    #         else:
    #             self._pbars.append(progress.add_task(f"[cyan]Worker{1}:", total=None, pakkage="", info=""))
    #             self._free_pbars.append(True)

    #             for pakkage in pakkages_to_fetch:
    #                 self.checkout_version(pakkage)
    #                 progress.update(pbar, advance=1, info=f"Fetching: {pakkage.name}")
    #                 logger.info(f"Fetched {pakkage.name}.")
    #                 # pakkages.fetched(pakkage)

    #     logger.info("Done fetching from GitLab")
    #     # return pakkages
    #     return

    def fetch(self, pakkages_to_fetch: list[PakkageConfig]):

        manager = ProgressManager(
            items=pakkages_to_fetch,
            item_processing_callback=self.checkout_version,
            num_workers=self.config.num_fetcher_workers.value,
            summary_description="[blue]Fetching pakkages from GitLab:",
            worker_description="[cyan]Fetcher {}:",
            text_fields=["pakkage", "info"],
        )

        manager.execute()

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
        url_with_token = self.get_gitlab_http_with_token(url)

        # Fetch the pakkage version
        GenericGitHelper.fetch_pakkage_version_with_git(target_version, url_with_token, tag, task)
