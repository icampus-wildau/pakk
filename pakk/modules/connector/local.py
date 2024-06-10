from __future__ import annotations

import logging
import os
import shutil
from typing import Type

from pakk.args.base_args import PakkArgs
from pakk.config.base import PakkConfigBase
from pakk.config.main_cfg import MainConfig
from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.pakkage.core import ConnectorAttributes
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState
from pakk.pakkage.core import PakkageState
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)


class LocalConnector(Connector):

    PRIORITY = 20
    CONFIG_CLS = None

    def __init__(self):
        super().__init__()

        self.all_pakkges_dir = MainConfig.get_config().paths.all_pakkages_dir.value

        self.additional_locations: list[str] = []

        kwargs = PakkArgs.kwargs
        # print(kwargs)
        if "location" in kwargs:
            locations_set = set()
            for location in kwargs["location"]:  # type: ignore
                if location not in self.additional_locations:
                    path = self.get_absolute_path(location)
                    if path is not None:
                        locations_set.add(path)

            self.additional_locations = list(locations_set)

        logger.debug(f"Additional local locations: {self.additional_locations}")

    @staticmethod
    def get_absolute_path(location: str) -> str | None:
        if location.startswith("/"):
            return location

        if location.startswith("~"):
            return os.path.expanduser(location)

        if location.startswith("."):
            return os.path.abspath(os.path.join(os.getcwd(), location))

        # If location is not a file path
        return None

    def discover_installed(self) -> PakkageCollection:
        """Discover all local installed pakkages."""

        logger.debug("Discovering installed pakkages...")

        all_pakkges_dir = self.all_pakkges_dir
        pakkages = PakkageCollection()

        # Go over each pakkage in the all directory and add it to the list
        for subdir, dirs, _ in os.walk(all_pakkges_dir):
            for d in dirs:
                abs_path = os.path.join(subdir, d)

                # Check if the directory contains a pakkage file
                pakkage_config = PakkageConfig.from_directory(abs_path)
                if pakkage_config is not None:
                    versions = PakkageVersions()

                    if pakkage_config.state is None:
                        logger.warning(f"Pakkage state is None for {pakkage_config.id}")
                        pakkage_config.state = PakkageState(PakkageInstallState.FETCHED)

                    if (
                        pakkage_config.state.install_state == PakkageInstallState.INSTALLED
                        or pakkage_config.state.install_state == PakkageInstallState.FAILED
                    ):
                        versions.installed = pakkage_config
                    elif (
                        pakkage_config.state.install_state == PakkageInstallState.FETCHED
                        or pakkage_config.state.install_state == PakkageInstallState.DISCOVERED
                    ):
                        versions.target = pakkage_config
                    else:
                        logger.debug(f"Unknown install state: {pakkage_config.state.install_state}")

                    pakkage = Pakkage(versions)
                    pakkages[pakkage.id] = pakkage

            # First entry gives us all the subdirectories we need to check
            break

        return pakkages

    def discover_in_dir(self, pakkages: PakkageCollection, path: str, recursive: bool = True):

        logger.debug("Discovering available local pakkages @ %s", path)

        # Check if the directory contains a pakkage file
        pakkage_config = PakkageConfig.from_directory(path)
        if pakkage_config is not None:
            versions = PakkageVersions()
            versions.available[pakkage_config.version] = pakkage_config

            if pakkage_config.state is None:
                # logger.warning(f"Pakkage state is not None for local provided {pakkage_config.id}")
                pakkage_config.state = PakkageState(PakkageInstallState.DISCOVERED)

            if pakkage_config.state.install_state == PakkageInstallState.INSTALLED:
                versions.installed = pakkage_config
            elif (
                pakkage_config.state.install_state
                == PakkageInstallState.FETCHED
                # or pakkage_config.state.install_state == PakkageInstallState.DISCOVERED
            ):
                versions.target = pakkage_config
            # else:
            #     logger.debug(f"Unknown install state: {pakkage_config.state.install_state}")

            attr = ConnectorAttributes()
            attr.url = path
            pakkage_config.set_attributes(self, attr)

            pakkage = Pakkage(versions)
            pakkages[pakkage.id] = pakkage
        else:
            # Iter each subdirectory
            if recursive:
                for subdir, dirs, _ in os.walk(path):
                    for d in dirs:

                        # Ignore paths starting with a dot
                        if d.startswith("."):
                            continue
                        abs_path = os.path.join(subdir, d)
                        self.discover_in_dir(pakkages, abs_path, recursive)

                    break

    def discover_available(self) -> PakkageCollection:
        """Discover all local available pakkages in provided local directories."""

        pakkages = PakkageCollection()

        for location_path in self.additional_locations:
            logger.info(f"Discovering local pakkages @ {location_path}")
            self.discover_in_dir(pakkages, location_path, True)

        return pakkages

    def discover(self, pakkage_ids: list[str] | None = None):
        installed_pakkages = self.discover_installed()
        available_pakkages = self.discover_available()
        return installed_pakkages.merge(available_pakkages)

    def fetch(self, pakkages_to_fetch: list[PakkageConfig]) -> None:

        fetched_dir = MainConfig.get_config().paths.fetch_dir.value
        # Fetching of local pakkages means copying the repository
        for pakkage in pakkages_to_fetch:

            attr = pakkage.get_attributes(self)
            if attr is None:
                logger.error(f"No attributes found for {pakkage.id} to fetch from local path.")
                continue

            path = attr.url
            if path is None:
                logger.error(f"No path found for {pakkage.id} to fetch from local path.")
                continue

            # Copy the directory to the fetch directory
            fetch_dir = os.path.join(fetched_dir, pakkage.id)
            name = pakkage.basename
            fetch_path = os.path.join(fetch_dir, name)

            if os.path.exists(fetch_path):
                logger.debug(f"Path already exists: {fetch_path}")
                continue

            logger.info(f"Fetching {pakkage.id} by copying {path} to {fetch_path}")
            os.makedirs(fetch_dir, exist_ok=True)
            shutil.copytree(path, fetch_path)

            pakkage.state.install_state = PakkageInstallState.FETCHED
            pakkage.local_path = fetch_path
