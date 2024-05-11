from __future__ import annotations

import logging
from datetime import datetime
from typing import TypeVar

from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage

logger = logging.getLogger(__name__)


class Discoverer(Module):
    def __init__(self, config_requirements: dict[str, list[str]] | None = None):
        super().__init__(config_requirements)

    def discover(self) -> dict[str, Pakkage]:
        """Discover all the packages with the implemented discoverer."""
        raise NotImplementedError()


# DiscovererType = TypeVar("DiscovererType", bound=Discoverer)


class DiscoveredPakkagesMerger:
    def __init__(self, discoverers: list[Discoverer], quiet: bool = False):
        self.discoverers = discoverers
        self.quiet = quiet

    def merge(self) -> dict[str, Pakkage]:
        """Merge the discovered pakkages from all the discoverers."""
        pakkages: dict[str, Pakkage] = {}

        if not self.quiet:
            Module.print_rule(f"Discovering pakkages")

        for discoverer in self.discoverers:
            discovered_pakkages = discoverer.discover()

            for id, pakkage in discovered_pakkages.items():
                if id in pakkages:
                    versions = pakkages[id].versions
                    versions.available.update(pakkage.versions.available)
                    versions.installed = pakkage.versions.installed
                else:
                    pakkages[id] = pakkage

        # Check if all installed versions are also available, otherwise there are problems with reinstalling
        for pakkage in pakkages.values():
            if (
                pakkage.versions.installed
                and len(pakkage.versions.available) > 0
                and pakkage.versions.installed.version not in pakkage.versions.available
            ):
                logger.warn(
                    f"Inconsistency detected for pakkage {pakkage.id}: installed version {pakkage.versions.installed.version} is not available in the discovered versions {pakkage.versions.available}"
                )

        return pakkages
