from __future__ import annotations

import json
import os
from datetime import datetime

import pytz

from pakk.args.install_args import InstallArgs
from pakk.pakkage.core import PakkageConfig

CACHING_VERSION = "0.1.0"


class CachedRepository:
    def __init__(self):

        self.id: str = ""
        self.url: str = ""
        self.last_activity: datetime = datetime.now()
        self.tags: dict[str, CachedTag] = dict()
        self.caching_version: str = CACHING_VERSION

    def to_json_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "last_activity": self.last_activity.isoformat(),
            "tags": [tag.to_json_dict() for tag in self.tags.values()],
            "cache_version": self.caching_version,
        }

    def __str__(self):
        return f"Repo {self.id} ({len(self.tags)} tags)"

    def __repr__(self):
        return self.__str__()

    def to_json(self):
        return json.dumps(self.to_json_dict())

    @staticmethod
    def from_json_dict(d: dict) -> CachedRepository | None:
        try:
            repo = CachedRepository()
            if d["cache_version"] != CACHING_VERSION:
                return None

            repo.id = d["id"]
            dt = datetime.fromisoformat(d["last_activity"])
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            repo.last_activity = dt

            repo.url = d["url"]

            tags = [CachedTag.from_json_dict(tag) for tag in d["tags"]]
            repo.tags = {tag.tag: tag for tag in tags if tag is not None}
            return repo
        except KeyError:
            return None

    @staticmethod
    def from_file(file_path: str) -> None | CachedRepository:
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r") as f:
            return CachedRepository.from_json_dict(json.load(f))

    def write(self, file_path: str):
        json_str = json.dumps(self.to_json_dict(), indent=2)
        with open(file_path, "w") as f:
            f.write(json_str)

    @staticmethod
    def from_directory(dir_path: str, recursive: bool = True) -> list[CachedRepository]:
        repos = []
        # if InstallArgs.get().clear_cache:
        #     return repos

        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    repo = CachedRepository.from_file(file_path)
                    if repo is not None:
                        repos.append(repo)
            if not recursive:
                break
        return repos


class CachedTag:
    def __init__(self):
        self.tag: str = ""
        self.commit: str = ""
        self.last_activity: datetime = datetime.now()

        self.pakk_config_str: str = ""
        self.is_pakk_version = False
        self.cache_version: str = CACHING_VERSION

    def to_json_dict(self):
        return {
            "tag": self.tag,
            "commit": self.commit,
            "last_activity": self.last_activity.isoformat(),
            "pakk_config_str": self.pakk_config_str,
            "is_pakk_version": self.is_pakk_version,
            "cache_version": self.cache_version,
        }

    def to_json(self):
        return json.dumps(self.to_json_dict())

    @staticmethod
    def from_json_dict(d: dict[str, str]) -> CachedTag | None:
        try:
            if d["cache_version"] != CACHING_VERSION:
                return None

            tag = CachedTag()
            tag.tag = d["tag"]
            tag.commit = d["commit"]
            dt = datetime.fromisoformat(d["last_activity"])
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            tag.last_activity = dt
            tag.pakk_config_str = d["pakk_config_str"]
            tag.is_pakk_version = d["is_pakk_version"]
            return tag
        except KeyError:
            return None

    @property
    def pakk_config(self) -> PakkageConfig:
        return PakkageConfig.from_string(self.pakk_config_str)

    @property
    def version(self) -> str:
        v = self.tag
        if v.startswith("v"):
            v = v[1:]
        return v
