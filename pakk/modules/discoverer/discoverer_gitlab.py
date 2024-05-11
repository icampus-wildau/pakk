from __future__ import annotations

import base64
import logging
import os
import tempfile
from datetime import datetime
from functools import cmp_to_key
from multiprocessing.pool import ThreadPool
from threading import Lock
from typing import Dict

import jsons
import semver
from gitlab.v4.objects import GroupProject
from requests import ConnectTimeout
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TimeElapsedColumn
from semver.version import Version

import pakk.config.pakk_config as cfg
from pakk.config.pakk_config import Sections
from pakk.helper import gitlab_util
from pakk.helper.gitlab_util import get_gitlab_http_with_token
from pakk.helper.gitlab_util import get_gitlab_instance as get_gl
from pakk.modules.discoverer.base import (
    Discoverer,  # , DiscoveredPackage, DiscoveredVersion
)
from pakk.pakk.args.install_config import InstallConfig
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)

CACHING_VERSION = "0.2.0"

ATTR_GITLAB_HTTP_SOURCE = "gitlab_http"
ATTR_GITLAB_SOURCE_TAG = "gitlab_tag"


class CachedProjectTag:
    def __init__(self, pakk_config: PakkageConfig = None):
        self.commit = ""
        self.tag = ""
        self.last_activity_at: datetime = datetime.now()

        self.pakk_config: PakkageConfig = pakk_config
        self.is_pakk_version = False

    @property
    def version(self) -> str:
        v = self.tag
        if v.startswith("v"):
            v = v[1:]
        return v

    @staticmethod
    def load_tags(cached_project: CachedProject) -> dict[str, CachedProjectTag]:
        gl_project = get_gl().projects.get(cached_project.id)
        project_tags = gl_project.tags.list()

        tags = dict()
        if len(project_tags) == 0:
            return tags

        for tag in project_tags:
            pt = CachedProjectTag()
            pt.tag = tag.attributes["name"]

            # Don't normalize the tags here, because you need to know the branch name for cloning.
            # if pt.tag.startswith("v"):
            #     pt.tag = pt.tag[1:]

            pt.commit = tag.attributes["commit"]["id"]
            pt.last_activity_at = tag.attributes["commit"]["committed_date"]  # created_at

            if (
                pt.tag in cached_project.versions
                and pt.last_activity_at == cached_project.versions[pt.tag].last_activity_at
            ):
                pt = cached_project.versions[pt.tag]
            else:
                # Load the pakk information from the tag
                # TODO: http.client.RemoteDisconnected: Remote end closed connection without response
                # TODO: urllib3.exceptions.ProtocolError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
                # TODO: requests.exceptions.ConnectionError ("Connection aborted.", ...)
                repo_tree = gl_project.repository_tree(ref=pt.commit, all=True)
                pakk_files = cfg.get().pakk_configuration_files
                for item in repo_tree:
                    if item["name"] in pakk_files:
                        file_info = gl_project.repository_blob(item["id"])
                        file_content = base64.b64decode(file_info["content"])
                        pakk_content_str = file_content.decode("utf-8")

                        temp_file = tempfile.NamedTemporaryFile(
                            mode="w+", prefix="z", suffix=item["name"], delete=False
                        )
                        temp_file.write(pakk_content_str)
                        temp_file.flush()
                        temp_file.close()

                        pakk_cfg = PakkageConfig.from_file(temp_file.name)
                        os.remove(temp_file.name)

                        if pakk_cfg is not None:
                            pt.pakk_config = pakk_cfg

                            pt.pakk_config.attributes[ATTR_GITLAB_HTTP_SOURCE] = cached_project.http_url_to_repo
                            pt.pakk_config.attributes[ATTR_GITLAB_SOURCE_TAG] = pt.tag

                            pt.is_pakk_version = True
                        else:
                            logger.warning("Failed to load pakk configuration from %s", item["name"])

            tags[pt.tag] = pt

        return tags

    @staticmethod
    def compare(a: CachedProjectTag, b: CachedProjectTag) -> int:
        return Version.parse(a.version).compare(b.version)
        # return semver.compare(a.version, b.version)


class CachedProject:
    def __init__(self, versions: dict[str, CachedProjectTag] | None = None):
        self.V = "0.0.0"

        self.id = ""
        self.name = ""
        self.description = ""

        self.default_branch = ""
        self.last_activity_at = ""
        self.http_url_to_repo = ""
        self.ssh_url_to_repo = ""

        self.name_with_namespace = ""
        self.path_with_namespace = ""

        self.versions: dict[str, CachedProjectTag] = versions or dict()

    @property
    def version_list(self):
        if len(self.versions) == 0:
            return []

        try:
            tag_list = sorted(self.versions.values(), key=cmp_to_key(CachedProjectTag.compare), reverse=True)
        except Exception as e:
            # logger.error("Failed to sort tags: %s", e)
            print("Failed to sort tags:", e)
            tag_list = list(self.versions.values())

        return tag_list

    @property
    def pakk_version_list(self):
        return [v for v in self.version_list if v.is_pakk_version]

    @property
    def file_name(self):
        return f"{self.id}__{self.name}.json"

    @property
    def file_dir(self):
        return cfg.get_path("cache_dir")

    @property
    def file_path(self):
        return os.path.join(self.file_dir, self.file_name)

    def save(self):
        """Save the project as single json file to the cache directory."""
        json_str = jsons.dumps(self, strip_properties=True, strip_privates=True, strip_class_variables=True)
        with open(self.file_path, "w") as f:
            f.write(json_str)

    @staticmethod
    def load(cp: CachedProject) -> CachedProject | None:
        file_path = cp.file_path
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                json_str = f.read()
                cp = jsons.loads(json_str, CachedProject)
                return cp

        return None

    @staticmethod
    def from_project(project: GroupProject) -> tuple[CachedProject, bool]:
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

        cp = CachedProject()

        cp.V = CACHING_VERSION
        cp.id = project.attributes["id"]
        cp.default_branch = project.attributes["default_branch"]
        cp.last_activity_at = project.attributes["last_activity_at"]
        cp.description = project.attributes["description"]
        cp.http_url_to_repo = project.attributes["http_url_to_repo"]
        cp.ssh_url_to_repo = project.attributes["ssh_url_to_repo"]
        cp.name = project.attributes["name"]
        cp.name_with_namespace = project.attributes["name_with_namespace"]
        cp.path_with_namespace = project.attributes["path_with_namespace"]

        ic = InstallConfig.get()
        if not ic.clear_cache:
            # If there are no new changes on the project, we can use the cached version
            loaded_cp = CachedProject.load(cp)
            if (
                loaded_cp is not None
                and loaded_cp.last_activity_at == cp.last_activity_at
                and loaded_cp.V == CACHING_VERSION
            ):
                return loaded_cp, True
        else:
            loaded_cp = None

        # Otherwise load all the tags
        cp.versions = CachedProjectTag.load_tags(loaded_cp or cp)
        cp.save()

        return cp, False

    @property
    def http_with_token(self):
        return get_gitlab_http_with_token(self.http_url_to_repo)


class DiscovererGitlabCached(Discoverer):
    CONFIG_REQUIREMENTS = {
        Sections.GITLAB_CONNECTION: ["url", "private_token"],
        Sections.GITLAB_PROJECTS: ["group_id"],
        Sections.SUBDIRS: ["cache_dir"],
        Sections.DISCOVERER_GITLAB: ["num_workers"],
    }

    def __init__(self, use_cache: bool = True):
        super().__init__()

        self.gl = gitlab_util.get_gitlab_instance()
        self.connected = False
        try:
            self.gl.auth()
            self.connected = True
        except ConnectTimeout as e:
            logger.error("Failed to connect to gitlab: %s", e)
            pass

        self.cached_projects: list[CachedProject] = list()
        self.discovered_pakkages: dict[str, Pakkage] = dict()

        self.use_cache = use_cache

    def retrieve_discovered_pakkages(self) -> dict[str, Pakkage]:
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

    def discover(self) -> dict[str, Pakkage]:
        num_workers = int(self.config.get(Sections.DISCOVERER_GITLAB, "num_workers"))
        main_group_id = int(self.config.get(Sections.GITLAB_PROJECTS, "group_id"))

        if not self.connected:
            logger.warning("Failed to connect to gitlab. Skipping discovery")
            return self.discovered_pakkages

        logger.info("Discovering projects from GitLab")
        logger.debug(f"Main group id: {main_group_id}")
        logger.debug(
            f"Including archived projects: {self.config.getboolean(Sections.GITLAB_PROJECTS, 'include_archived')}"
        )
        logger.debug(f"Using {num_workers} workers" if num_workers > 1 else None)

        main_group = self.gl.groups.get(main_group_id)
        projects = main_group.projects.list(iterator=True, get_all=True, include_subgroups=True)

        self.cached_projects.clear()

        include_archived = self.config.getboolean(Sections.GITLAB_PROJECTS, "include_archived")

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
                # with Pool(num_workers) as pool:
                with ThreadPool(num_workers) as pool:
                    for res in pool.imap_unordered(CachedProject.from_project, filtered_group_projects):
                        append_result(*res)

                pool.join()
            else:
                for gp in filtered_group_projects:
                    append_result(*CachedProject.from_project(gp))

        logger.debug(f"Finished loading {len(projects)} projects:")
        logger.debug(f"  {results['not cached']} loaded from gitlab api")
        logger.debug(f"  {results['cached']} loaded from cache")
        logger.debug(f"  {results['archived']} archived projects were skipped" if results["archived"] > 0 else None)

        dps = self.retrieve_discovered_pakkages()
        n_versions = 0
        for p_id, pakkage in dps.items():
            n_versions += len(pakkage.versions.available)

        logger.info(f"Discovered {len(dps)} pakk packages with {n_versions} versions")

        return dps
