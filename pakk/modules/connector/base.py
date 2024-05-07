from __future__ import annotations

from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage

import logging
logger = logging.getLogger(__name__)



class DiscoveredPakkages:
    def __init__(self):
        # self.quiet = quiet
        
        self.discovered_packages: dict[str, Pakkage] = dict()
        self.undiscovered_packages: set[str] = set()

    def __getitem__(self, key: str) -> Pakkage:
        return self.discovered_packages[key]
    
    def __setitem__(self, key: str, value: Pakkage):
        self.discovered_packages[key] = value

    def merge(self, new_pakkages: DiscoveredPakkages) -> dict[str, Pakkage]:
        """Merge the discovered pakkages."""

        self.undiscovered_packages.update(new_pakkages.undiscovered_packages)

        for id, pakkage in new_pakkages.discovered_packages.items():
            if id in self.discovered_packages:
                versions = self.discovered_packages[id].versions
                versions.available.update(pakkage.versions.available)
                versions.installed = pakkage.versions.installed
            else:
                self.discovered_packages[id] = pakkage
            
            self.undiscovered_packages.discard(id)
    
    @staticmethod
    def discover(connectors: list[Connector], quiet: bool = False) -> DiscoveredPakkages:

        if not quiet:
            Module.print_rule(f"Discovering pakkages")

        pakkages = DiscoveredPakkages()
        for connector in connectors:
            discovered_pakkages = connector.discover()
            pakkages.merge(discovered_pakkages)

        # Check if all installed versions are also available, otherwise there are problems with reinstalling
        for pakkage in pakkages.discovered_packages.values():
            if pakkage.versions.installed and len(pakkage.versions.available) > 0 and pakkage.versions.installed.version not in pakkage.versions.available:
                logger.warn(f"Inconsistency detected for pakkage {pakkage.id}: installed version {pakkage.versions.installed.version} is not available in the discovered versions {pakkage.versions.available}")

        return pakkages

class Connector(Module):
    def __init__(self, pakkages: dict[str, Pakkage]):
        super().__init__()
        self.pakkages = pakkages

    def discover(self) -> DiscoveredPakkages:
        """Discover all the packages with the implemented discoverer."""
        raise NotImplementedError()

    def fetch(self) -> dict[str, Pakkage]:
        """Fetch all the packages with the implemented fetcher."""
        raise NotImplementedError()

