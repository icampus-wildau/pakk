from __future__ import annotations

import logging
import os

from pakk.config.pakk_config import Sections
from pakk.modules.discoverer.base import Discoverer
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)


class DiscovererLocalInstallable(Discoverer):
    CONFIG_REQUIREMENTS = {Sections.SUBDIRS: ["all_pakkges_dir"]}

    def __init__(self, pakkage_paths: str | list[str]):
        super().__init__()
        self.paths = pakkage_paths
        self.path_replacements: dict[str, str] = {}

    def discover(self) -> dict[str, Pakkage]:
        """Discover installable pakkages from a local directory."""

        all_pakkges_dir: str = self.config.get_abs_path("all_pakkges_dir", Sections.SUBDIRS)  # type: ignore

        pakkages = {}

        # Go over each directory and add it to the list if it contains a pakkage file
        for p in self.paths:
            for subdir, dirs, _ in os.walk(p):
                for d in dirs + [subdir]:
                    abs_path = os.path.join(subdir, d)

                    # Check if the directory contains a pakkage file
                    pakkage_config = PakkageConfig.from_directory(abs_path)
                    if pakkage_config is not None:
                        versions = PakkageVersions([pakkage_config])

                        pakkage = Pakkage(versions)
                        pakkages[pakkage.id] = pakkage
                        self.path_replacements[abs_path] = pakkage.id

                # First entry gives us all the subdirectories we need to check
                break

        return pakkages
