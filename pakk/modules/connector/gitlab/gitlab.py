from __future__ import annotations

import inspect
import logging
import re
from multiprocessing.pool import ThreadPool
from threading import Lock

import gitlab
from pakk.modules.connector.gitlab.cache import CachedProject
from requests import ConnectTimeout
from rich.progress import (MofNCompleteColumn, Progress, SpinnerColumn,
                           TimeElapsedColumn)

from pakk.modules.connector.base import Connector, DiscoveredPakkages
from pakk.modules.connector.gitlab.config import GitlabConfig
from pakk.pakkage.core import Pakkage, PakkageVersions


logger = logging.getLogger(__name__)

CACHING_VERSION = "0.2.0"

ATTR_GITLAB_HTTP_SOURCE = "gitlab_http"
ATTR_GITLAB_SOURCE_TAG = "gitlab_tag"


class GitlabConnector(Connector):

    CONFIG_CLS = GitlabConfig

    gl_instance: gitlab.Gitlab | None = None

    def __init__(self, **kwargs):
        super().__init__()

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
        self.discovered_pakkages: DiscoveredPakkages = DiscoveredPakkages()

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
        self.discovered_pakkages.discovered_packages.clear()

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
        logger.debug(
            f"Including archived projects: {self.config.include_archived.value}"
        )
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
        logger.debug(f"  {results['archived']} archived projects were skipped" if results["archived"] > 0 else None)

        dps = self.retrieve_discovered_pakkages()
        n_versions = 0
        for p_id, pakkage in dps.discovered_packages.items():
            n_versions += len(pakkage.versions.available)

        logger.info(f"Discovered {len(dps.discovered_packages)} pakk packages with {n_versions} versions")

        return dps
