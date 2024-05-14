from __future__ import annotations

import inspect
import logging
import os
import re
import subprocess
from multiprocessing.pool import ThreadPool
from threading import Lock

import gitlab
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
from pakk.logger import console
from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.base import FetchedPakkages
from pakk.modules.connector.gitlab.cache import CachedProject
from pakk.modules.connector.gitlab.config import GitlabConfig
from pakk.modules.module import Module
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

        self.cached_projects: list[CachedProject] = list()
        self.discovered_pakkages: PakkageCollection = PakkageCollection()

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

    def retrieve_discovered_pakkages(self) -> DiscoveredPakkages:
        self.discovered_pakkages.clear()

        for cp in self.cached_projects:
            if len(cp.versions) == 0:
                continue

            pakk_versions = cp.pakk_version_list
            if len(pakk_versions) == 0:
                continue

            available_versions = [v.pakk_config for v in pakk_versions]
            versions = PakkageVersions(available_versions)
            p = Pakkage(versions)

            self.discovered_pakkages[p.id] = p

        return self.discovered_pakkages

    def discover(self) -> DiscoveredPakkages:
        num_workers = int(self.config.num_discover_workers.value)
        main_group_id = int(self.config.group_id.value)

        if not self.connected:
            logger.warning("Failed to connect to gitlab. Skipping discovery")
            return self.discovered_pakkages

        logger.info("Discovering projects from GitLab")
        logger.debug(f"Main group id: {main_group_id}")
        logger.debug(f"Including archived projects: {self.config.include_archived.value}")
        logger.debug(f"Using {num_workers} workers" if num_workers > 1 else None)

        main_group = self.gl.groups.get(main_group_id)
        projects = main_group.projects.list(iterator=True, get_all=True, include_subgroups=True)

        self.cached_projects.clear()

        include_archived = self.config.include_archived.value

        results = {
            "lock": Lock(),
            "projects": self.cached_projects,
            "cached": 0,
            "not cached": 0,
            "archived": 0,
            "pbar": None,
        }

        # self.print_info(f"Discovering {len(projects)} projects...")
        logger.debug(f"Looking at {len(projects)} projects...")

        filtered_group_projects = list(
            filter(lambda gp: not gp.attributes.get("archived") or include_archived, projects)
        )
        results["archived"] = len(projects) - len(filtered_group_projects)

        # with tqdm.tqdm(total=len(filtered_group_projects)) as pbar:
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ) as progress:
            pbar = progress.add_task("[cyan]Discovering projects", total=len(filtered_group_projects))

            results["pbar"] = pbar

            def append_result(cp, cached):
                # pbar.update(1)
                progress.update(pbar, advance=1)
                if cached:
                    results["cached"] += 1
                else:
                    results["not cached"] += 1

                self.cached_projects.append(cp)

            if num_workers > 1:

                def process(gp):
                    return CachedProject.from_project(self, gp)

                # with Pool(num_workers) as pool:
                with ThreadPool(num_workers) as pool:
                    for res in pool.imap_unordered(process, filtered_group_projects):
                        append_result(*res)

                pool.join()
            else:
                for gp in filtered_group_projects:
                    append_result(*CachedProject.from_project(self, gp))

        logger.debug(f"Finished loading {len(projects)} projects:")
        logger.debug(f"  {results['not cached']} loaded from gitlab api")
        logger.debug(f"  {results['cached']} loaded from cache")
        logger.debug(
            f"  {results['archived']} archived projects were skipped"
            if results["archived"] > 0
            else "No archived projects found"
        )

        dps = self.retrieve_discovered_pakkages()
        n_versions = 0
        for p_id, pakkage in dps._discovered_packages.items():
            n_versions += len(pakkage.versions.available)

        logger.info(f"Discovered {len(dps._discovered_packages)} pakk packages with {n_versions} versions")

        return dps

    def checkout_target_version(self, pakkage: Pakkage) -> Pakkage | None:
        if not pakkage.versions.is_update_candidate():
            return None

        # Get the next free pbar
        pbar_index = self._free_pbars.index(True)
        # Acquire the pbar
        self._free_pbars[pbar_index] = False
        # Get the related pbar
        pbar = self._pbars[pbar_index]

        fetched_dir = MainConfig.get_config().paths.fetch_dir.value

        target_version = pakkage.versions.target
        if target_version is None:
            raise Exception(f"Target version of {pakkage.name} is None.")

        if ATTR_GITLAB_HTTP_SOURCE in target_version.attributes and ATTR_GITLAB_SOURCE_TAG in target_version.attributes:
            url = target_version.attributes[ATTR_GITLAB_HTTP_SOURCE]
            url_with_token = self.get_gitlab_http_with_token(url)
            tag = target_version.attributes[ATTR_GITLAB_SOURCE_TAG]

            name = target_version.basename
            path = os.path.join(fetched_dir, name)

            fetch = True
            if os.path.exists(path):
                if self.install_args.refetch or self.install_args.clear_cache:
                    logger.debug(f"Directory {path} already exists. Refetching it.")

                    # delete existing directory
                    remove_dir(path)
                else:
                    # Check if the directory is empty
                    with os.scandir(path) as it:
                        if not any(it):
                            fetch = True
                            logger.debug(f"Directory {path} already exists but is empty. Refetching it.")
                            remove_dir(path)
                        else:
                            fetch = False
                            logger.debug(f"Directory {path} already exists. Skipping fetch and using local version.")

            if fetch:
                os.makedirs(path, exist_ok=True)

                # Clone the repository
                # -c advice.detachedHead=false is for ignoring the warning about detached HEAD
                # We don't need git history, so we use --depth=1
                # The --progress option is required to get the continuous progress output
                cmd = f"git clone -c advice.detachedHead=false --depth=1 --branch {tag} {url_with_token} {name} --progress"
                retry_count = 2
                tries = 0

                while tries < retry_count:
                    with subprocess.Popen(
                        cmd,
                        cwd=fetched_dir,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        bufsize=1,
                        universal_newlines=True,
                    ) as p:

                        # Capture the output of the subprocess to print the info in the pbar
                        for line in p.stdout:
                            self._pbar_progress.update(pbar, pakkage=pakkage.id, info=line.strip().replace("\r", ""))

                    if PakkageConfig.from_directory(path):
                        break

                    tries += 1
                    if tries < retry_count:
                        logger.warning(f"Fetch of {pakkage.id} failed. Retrying...")

            # Load the PakkageConfig from the fetched directory
            target_version = PakkageConfig.from_directory(path)
            if target_version is None:
                raise Exception(f"Could not load PakkageConfig from {path}")

            # If there was an installed version, copy the state
            target_version.state.copy_from(pakkage.versions.installed)
            target_version.state.install_state = PakkageInstallState.FETCHED
            target_version.local_path = path

            # Create the .pakk directory and store the state
            target_version.save_state(path)
            pakkage.versions.target = target_version

        self._free_pbars[pbar_index] = True
        self._pbar_progress.update(pbar, pakkage="Done", info="")
        return pakkage

    def fetch(self, pakkages: FetchedPakkages) -> FetchedPakkages:
        Module.print_rule(f"Fetching pakkages")

        self.install_args = InstallArgs.get()

        num_workers = int(self.config.num_fetcher_workers.value)

        # packages_to_fetch = [pakkage for pakkage in self.pakkages.values() if pakkage.versions.is_update_candidate()]
        packages_to_fetch = pakkages.pakkages_to_fetch.values()

        # try:
        if len(packages_to_fetch) == 0:
            logger.info("No pakkages to fetch.")
            return pakkages

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            # TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            TextColumn("{task.fields[pakkage]}"),
            TextColumn("{task.fields[info]}"),
            transient=True,
            console=console,
        ) as progress:
            self._pbar_progress = progress

            pbar = progress.add_task("[blue]Fetching Total:", total=len(packages_to_fetch), pakkage="", info="")

            if num_workers > 1:
                num_workers = min(num_workers, len(packages_to_fetch))
                for i in range(num_workers):
                    self._pbars.append(progress.add_task(f"[cyan]Worker{i + 1}:", total=None, pakkage="", info=""))
                    self._free_pbars.append(True)

                # Don't use multiprocessing.Pool since it will spawn new processes and not threads,
                # thus the data will not be shared.
                # See:
                # https://stackoverflow.com/questions/3033952/threading-pool-similar-to-the-multiprocessing-pool
                # https://stackoverflow.com/questions/52486811/how-to-properly-reference-to-instances-of-a-class-in-multiprocessing-pool-map
                # https://towardsdatascience.com/demystifying-python-multiprocessing-and-multithreading-9b62f9875a27
                with ThreadPool(num_workers) as pool:
                    for res in pool.imap_unordered(self.checkout_target_version, packages_to_fetch):
                        progress.update(pbar, advance=1, info="")
                        if res is not None:
                            logger.info(f"Fetched {res.name}.")
                            pakkages.fetched(res)
                pool.join()
            else:
                self._pbars.append(progress.add_task(f"[cyan]Worker{1}:", total=None, pakkage="", info=""))
                self._free_pbars.append(True)

                for pakkage in packages_to_fetch:
                    self.checkout_target_version(pakkage)
                    progress.update(pbar, advance=1, info=f"Fetching: {pakkage.name}")
                    logger.info(f"Fetched {pakkage.name}.")
                    pakkages.fetched(pakkage)

        logger.info("Done fetching")
        return pakkages
