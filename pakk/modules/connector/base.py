from __future__ import annotations

import logging
from typing import Type

from pakk.config.base import ConnectorConfiguration
from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage

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

    def merge(self, new_pakkages: DiscoveredPakkages) -> DiscoveredPakkages:
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


class Connector(Module):

    PRIORITY = 100
    """The priority of the connector. The lower the number, the higher the priority."""

    CONFIG_CLS: Type[ConnectorConfiguration] | None = None
    """
    The configuration class used for the connector.
    If None, this connector does not require a configuration.
    """

    def __init__(self):
        super().__init__()

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
