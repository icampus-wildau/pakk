import os
from typing import Type
from pakk.config.base import PakkConfigBase
from pakk.config.main_cfg import MainConfig
from pakk.modules.connector.base import Connector, DiscoveredPakkages
from pakk.pakkage.core import Pakkage, PakkageConfig, PakkageInstallState, PakkageState, PakkageVersions

import logging

logger = logging.getLogger(__name__)


class LocalConnector(Connector):

    PRIORITY = 20
    CONFIG_CLS: Type[PakkConfigBase] = None

    def __init__(self, **kwargs):
        self.all_pakkges_dir = MainConfig.get_config().paths.all_pakkages_dir.value

    def discover(self):
        """Discover all local installed pakkages."""

        all_pakkges_dir = self.all_pakkges_dir
        pakkages = DiscoveredPakkages()

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

                    if pakkage_config.state.install_state == PakkageInstallState.INSTALLED:
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
