from __future__ import annotations

import os

from pakk.config.pakk_config import Sections
from pakk.modules.discoverer.base import Discoverer
from pakk.pakkage.core import Pakkage, PakkageState, PakkageVersions, PakkageConfig, PakkageInstallState

import logging

logger = logging.getLogger(__name__)

class DiscovererLocal(Discoverer):
    CONFIG_REQUIREMENTS = {
        Sections.SUBDIRS: ["all_pakkges_dir"]
    }

    def __init__(self):
        super().__init__()

    def discover(self) -> dict[str, Pakkage]:
        """Discover all local fetched and installed pakkages."""

        all_pakkges_dir: str = self.config.get_abs_path("all_pakkges_dir", Sections.SUBDIRS) # type: ignore

        pakkages = {}

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
                    elif pakkage_config.state.install_state == PakkageInstallState.FETCHED or pakkage_config.state.install_state == PakkageInstallState.DISCOVERED:
                        versions.target = pakkage_config
                    else:
                        logger.debug(f"Unknown install state: {pakkage_config.state.install_state}")

                    pakkage = Pakkage(versions)
                    pakkages[pakkage.id] = pakkage

            # First entry gives us all the subdirectories we need to check
            break

        return pakkages
