from __future__ import annotations

import logging
from typing import Generic
from typing import Type
from typing import TypeVar

from pakk.config.base import ConnectorConfiguration
from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage

logger = logging.getLogger(__name__)


class DiscoveredPakkages:
    def __init__(self):
        # self.quiet = quiet

        self._discovered_packages: dict[str, Pakkage] = dict()
        self.shortened_ids: dict[str, list[str]] = dict()
        self._undiscovered_packages: set[str] = set()

    def clear(self):
        self._discovered_packages.clear()
        self.shortened_ids.clear()
        self._undiscovered_packages.clear()

    def add_discovered_pakkage(self, pakkage: Pakkage):
        self._discovered_packages[pakkage.id] = pakkage

    def __getitem__(self, key: str) -> Pakkage | None:
        if key in self._discovered_packages:
            return self._discovered_packages[key]
        
        if key in self.shortened_ids:
            if len(self.shortened_ids[key]) == 1:
                return self._discovered_packages[self.shortened_ids[key][0]]
            
        return None
    
    def __len__(self):
        return len(self._discovered_packages)
    
    def __iter__(self):
        return iter(self._discovered_packages)
    
    def values(self):
        return self._discovered_packages.values()
    
    def items(self):
        return self._discovered_packages.items()
    
    def keys(self):
        return self._discovered_packages.keys()

    def __setitem__(self, key: str, value: Pakkage):
        self._discovered_packages[key] = value
        self._undiscovered_packages.discard(key)

        splits = key.split("/")
        if len(splits) == 2:
            group = splits[0]
            id = splits[1]
            
            if id not in self.shortened_ids:
                self.shortened_ids[id] = []

            self.shortened_ids[id].append(key)
            

    def merge(self, new_pakkages: DiscoveredPakkages) -> DiscoveredPakkages:
        """Merge the discovered pakkages."""

        self._undiscovered_packages.update(new_pakkages._undiscovered_packages)

        for id, pakkage in new_pakkages._discovered_packages.items():
            if id in self._discovered_packages:
                versions = self._discovered_packages[id].versions
                versions.available.update(pakkage.versions.available)
                versions.installed = pakkage.versions.installed
            else:
                self._discovered_packages[id] = pakkage

            self._undiscovered_packages.discard(id)
        
        for id, shortened_ids in new_pakkages.shortened_ids.items():
            if id not in self.shortened_ids:
                self.shortened_ids[id] = []
            
            self.shortened_ids[id].extend(shortened_ids)

        return self

    @staticmethod
    def discover(connectors: list[Connector], quiet: bool = False) -> DiscoveredPakkages:

        if not quiet:
            Module.print_rule(f"Discovering pakkages")

        pakkages = DiscoveredPakkages()
        for connector in connectors:
            discovered_pakkages = connector.discover()
            pakkages.merge(discovered_pakkages)

        # Check if all installed versions are also available, otherwise there are problems with reinstalling
        for pakkage in pakkages._discovered_packages.values():
            if (
                pakkage.versions.installed
                and len(pakkage.versions.available) > 0
                and pakkage.versions.installed.version not in pakkage.versions.available
            ):
                logger.warn(
                    f"Inconsistency detected for pakkage {pakkage.id}: installed version {pakkage.versions.installed.version} is not available in the discovered versions {pakkage.versions.available}"
                )

        return pakkages


class FetchedPakkages:
    def __init__(self):
        # self.quiet = quiet

        self.pakkages_to_fetch: dict[str, Pakkage] = dict()
        self.fetched_packages: dict[str, Pakkage] = dict()

    def __getitem__(self, key: str) -> Pakkage:
        return self.fetched_packages[key]

    def __setitem__(self, key: str, value: Pakkage):
        self.fetched_packages[key] = value

    def merge(self, new_pakkages: FetchedPakkages) -> FetchedPakkages:
        """Merge the fetched pakkages."""

        self.undiscovered_packages.update(new_pakkages.undiscovered_packages)

        for id, pakkage in new_pakkages.discovered_packages.items():
            if id in self.fetched_packages:
                versions = self.fetched_packages[id].versions
                versions.available.update(pakkage.versions.available)
                versions.installed = pakkage.versions.installed
            else:
                self.fetched_packages[id] = pakkage

            self.undiscovered_packages.discard(id)

        return self

    def fetched(self, pakkage: Pakkage):
        self.fetched_packages[pakkage.id] = pakkage
        self.pakkages_to_fetch.pop(pakkage.id, None)

    def fetch(self, connectors: list[Connector], quiet: bool = False) -> FetchedPakkages:

        if not quiet:
            Module.print_rule(f"Discovering pakkages")

        pakkages = DiscoveredPakkages()
        for connector in connectors:
            discovered_pakkages = connector.discover()
            pakkages.merge(discovered_pakkages)

        # Check if all installed versions are also available, otherwise there are problems with reinstalling
        for pakkage in pakkages.discovered_packages.values():
            if (
                pakkage.versions.installed
                and len(pakkage.versions.available) > 0
                and pakkage.versions.installed.version not in pakkage.versions.available
            ):
                logger.warn(
                    f"Inconsistency detected for pakkage {pakkage.id}: installed version {pakkage.versions.installed.version} is not available in the discovered versions {pakkage.versions.available}"
                )

        return pakkages


C = TypeVar("C", bound=ConnectorConfiguration)


class Connector(Module, Generic[C]):

    PRIORITY = 100
    """The priority of the connector. The lower the number, the higher the priority."""

    CONFIG_CLS: Type[C] | None = None
    """
    The configuration class used for the connector.
    If None, this connector does not require a configuration.
    """

    def __init__(self, **kwargs):
        """Create a new connector."""
        super().__init__()
        # self.config = self.CONFIG_CLS.get_config() if self.CONFIG_CLS else None

    @classmethod
    def is_configured(cls):
        """Check if the connector is configured."""
        return cls.CONFIG_CLS is None or cls.CONFIG_CLS.exists()

    @classmethod
    def is_enabled(cls) -> bool:
        """
        Check if the connector is enabled.
        Override this method to implement a custom check.
        """
        if cls.CONFIG_CLS is None:
            return True
        return cls.CONFIG_CLS.exists() and cls.CONFIG_CLS.get_config().is_enabled()

    def discover(self) -> DiscoveredPakkages:
        """Discover all the packages with the implemented discoverer."""
        raise NotImplementedError()

    def fetch(self) -> FetchedPakkages:
        """Fetch all the packages with the implemented fetcher."""
        raise NotImplementedError()
