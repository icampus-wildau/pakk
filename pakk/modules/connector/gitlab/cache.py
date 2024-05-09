from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from datetime import datetime
from functools import cmp_to_key
from typing import TYPE_CHECKING, Any

from pakk.config.main_cfg import MainConfig

if TYPE_CHECKING:
    from pakk.modules.connector.gitlab.gitlab import GitlabConnector

# import jsons
import jsonpickle
from gitlab.v4.objects import GroupProject
from semver.version import Version

from pakk.args.install_args import InstallArgs
from pakk.pakkage.core import CompactPakkageConfig, PakkageConfig

logger = logging.getLogger(__name__)

CACHING_VERSION = "0.2.0"

ATTR_GITLAB_HTTP_SOURCE = "gitlab_http"
ATTR_GITLAB_SOURCE_TAG = "gitlab_tag"


class CachedProjectTag:
    def __init__(self, pakk_config: CompactPakkageConfig = None):
        self.commit = ""
        self.tag = ""
        self.last_activity_at: datetime = datetime.now()

        self.pakk_config: CompactPakkageConfig = pakk_config
        self.is_pakk_version = False

    @property
    def version(self) -> str:
        v = self.tag
        if v.startswith("v"):
            v = v[1:]
        return v

    @staticmethod
    def load_tags(connector: GitlabConnector, cached_project: CachedProject) -> dict[str, CachedProjectTag]:
        
        gl_project = connector.get_gitlab_instance().projects.get(cached_project.id)
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
                # pakk_files = cfg.get().pakk_configuration_files
                pakk_files = MainConfig.get_config().pakk_cfg_files

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
                            pakk_cfg = CompactPakkageConfig.from_pakkage_config(pakk_cfg)
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


class CachedProject:
    def __init__(self, versions: dict[str, CachedProjectTag] | None = None):
        self.V = "0.0.0"

        self.id: str = ""
        self.name: str = ""
        self.description: str = ""

        self.default_branch: str = ""
        self.last_activity_at: str = ""
        self.http_url_to_repo: str = ""
        self.ssh_url_to_repo: str = ""

        self.name_with_namespace: str = ""
        self.path_with_namespace: str = ""

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
    def file_dir(self) -> str:
        return MainConfig.get_config().paths.cache_dir.value

    @property
    def file_path(self):
        return os.path.join(self.file_dir, self.file_name)

    def save(self):
        """Save the project as single json file to the cache directory."""
        # json_str = jsons.dumps(self, strip_properties=True, strip_privates=True, strip_class_variables=True)
        json_str: str = jsonpickle.encode(self) #, make_refs=True) # , unpicklable=False
        # json_str: str = json.dumps(self, cls=CachedProjectEncoder, check_circular=False)
        # json_str = jsonpickle.encode(self)
        with open(self.file_path, "w") as f:
            f.write(json_str)

    @staticmethod
    def load(cp: CachedProject) -> CachedProject | None:
        file_path = cp.file_path
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                json_str = f.read()
                # cp = jsons.loads(json_str, CachedProject)
                cp = jsonpickle.decode(json_str)
                # cp = json.loads(json_str, cls=CachedProjectDecoder)
                return cp

        return None

    @staticmethod
    def from_project(connector: GitlabConnector, project: GroupProject) -> tuple[CachedProject, bool]:
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

        ic = InstallArgs.get()
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
        cp.versions = CachedProjectTag.load_tags(connector, loaded_cp or cp)
        cp.save()

        return cp, False

    # @property
    # def http_with_token(self):
    #     return self.connector.get_gitlab_http_with_token(self.http_url_to_repo)



class CachedProjectEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)       
    
    def strip_privates(self, dict: Any):
        return {k: v for k, v in dict.items() if not k.startswith("_")}
    

    def default(self, o):
        if isinstance(o, CachedProject):
            members = o.__dict__.copy()
            members = self.strip_privates(members)
            return members
        elif isinstance(o, CachedProjectTag):
            members = o.__dict__.copy()
            members = self.strip_privates(members)
            return members
        elif isinstance(o, CompactPakkageConfig):
            members = o.__dict__.copy()
            members = self.strip_privates(members)
            return members

        # d = o.__dict__.copy()
        d = o
        return d


class CachedProjectDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def decode(self, s: str):
        obj = json.loads(s)
        if "versions" in obj:
            versions = obj["versions"]
            for key in versions:
                versions[key] = CachedProjectTag(**versions[key])

        return CachedProject(**obj)
    