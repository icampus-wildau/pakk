from __future__ import annotations

import logging
from typing import Generic
from typing import Type
from typing import TypeVar

from pakk.config.base import ConnectorConfiguration
from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage

logger = logging.getLogger(__name__)


class PakkageCollection:
    """Collection of pakkages."""

    def __init__(self):

        self.pakkages: dict[str, Pakkage] = dict()
        """Available pakkages in the collection stored by their id as key."""

        self.undiscovered_packages: set[str] = set()
        """Pakkages that have not been discovered yet or couldn't be discovered."""

        self.id_abbreviations: dict[str, list[str]] = dict()
        """
        Abbreviations for pakkage ids.
        E.g. 'icampus-wildau/ros-i2c' can be abbreviated to 'ros-i2c'.
        Since the abbreviation is not unique, a list of possible ids is stored.
        """

        self.ids_to_be_installed: set[str] = set()
        """Pakkages that are to be installed."""

    def add_pakkage(self, pakkage: Pakkage):
        """
        Add a pakkage to the collection.
        Takes care of pakkage id abbreviations.
        """
        self.pakkages[pakkage.id] = pakkage
        self.undiscovered_packages.discard(pakkage.id)

        splits = pakkage.id.split("/")
        if len(splits) == 2:
            group = splits[0]
            id = splits[1]

            if id not in self.id_abbreviations:
                self.id_abbreviations[id] = []

            self.id_abbreviations[id].append(pakkage.id)

    def get_pakkage(self, id: str) -> Pakkage | None:
        """Get a pakkage by its id or its abbreviation."""

        if id in self.pakkages:
            return self.pakkages[id]

        if id in self.id_abbreviations:
            if len(self.id_abbreviations[id]) == 1:
                return self.pakkages[self.id_abbreviations[id][0]]

        return None

    def __len__(self):
        return len(self.pakkages)

    def __iter__(self):
        return iter(self.pakkages)

    def values(self):
        return self.pakkages.values()

    def items(self):
        return self.pakkages.items()

    def keys(self):
        return self.pakkages.keys()

    def __getitem__(self, key: str) -> Pakkage | None:
        return self.pakkages.get(key, None)

    def __setitem__(self, key: str, value: Pakkage):
        return self.add_pakkage(value)

    @property
    def pakkages_to_fetch(self) -> dict[str, Pakkage]:
        return {pakkage.id: pakkage for pakkage in self.pakkages.values() if pakkage.versions.is_update_candidate()}

    def merge(self, new_pakkages: PakkageCollection) -> PakkageCollection:
        """Merge PakkageCollection objects."""

        # Merge pakkages
        for new_id, new_pakkage in new_pakkages.pakkages.items():
            if new_id in self.pakkages:
                versions = self.pakkages[new_id].versions
                # Dont just update here.
                # Connectors are sorted by priority, so the first connector that discovers a pakkage is the source of truth.
                # versions.available.update(new_pakkage.versions.available)

                for new_version in new_pakkage.versions.available:
                    if new_version not in versions.available:
                        versions.available[new_version] = new_pakkage.versions.available[new_version]
                    else:
                        # Dont overwrite the installed version here
                        logger.debug(
                            "Skipping version %s for %s, because it is already available in the pakkage collection.",
                            new_version,
                            new_id,
                        )

                versions.installed = (
                    versions.installed if versions.installed is not None else new_pakkage.versions.installed
                )
            else:
                self.add_pakkage(new_pakkage)

        # Merge undiscovered_packages
        self.undiscovered_packages.update(new_pakkages.undiscovered_packages)
        self.undiscovered_packages.difference_update(self.pakkages.keys())

        # Merge id_abbreviations
        for abbr, ids in new_pakkages.id_abbreviations.items():
            if abbr not in self.id_abbreviations:
                self.id_abbreviations[abbr] = []
            self.id_abbreviations[abbr].extend(ids)

        # Merge ids_to_be_installed
        self.ids_to_be_installed.update(new_pakkages.ids_to_be_installed)

        return self

    ####################################################################################################################
    ### Connector functions
    ####################################################################################################################

    def discover(self, connectors: list[Connector], quiet: bool = False) -> PakkageCollection:
        """
        Discover pakkages with the given connectors.
        The discovery process addes packages to the collection.
        """

        if not quiet:
            Module.print_rule(f"Discovering pakkages")

        for connector in connectors:
            discovered_pakkages = connector.discover()
            self.merge(discovered_pakkages)

        # Check if all installed versions are also available, otherwise there are problems with reinstalling
        for pakkage in self.pakkages.values():
            if (
                pakkage.versions.installed
                and len(pakkage.versions.available) > 0
                and pakkage.versions.installed.version not in pakkage.versions.available
            ):
                logger.warn(
                    f"Inconsistency detected for pakkage {pakkage.id}: installed version {pakkage.versions.installed.version} is not available in the discovered versions {pakkage.versions.available}"
                )

        return self

    def fetch(self, connectors: list[Connector], quiet: bool = False) -> PakkageCollection:
        """
        Fetch pakkages with the given connectors.
        The fetching process looks at target versions of the pakkages in the collection and downloads them.
        A resolver should set a target version before fetching.
        """

        if not quiet:
            Module.print_rule(f"Fetching pakkages")

        for connector in connectors:
            connector.fetch(self.pakkages_to_fetch)

        return self


# class DiscoveredPakkages:
#     def __init__(self):
#         # self.quiet = quiet

#         self._discovered_packages: dict[str, Pakkage] = dict()
#         self.shortened_ids: dict[str, list[str]] = dict()
#         self._undiscovered_packages: set[str] = set()

#     def clear(self):
#         self._discovered_packages.clear()
#         self.shortened_ids.clear()
#         self._undiscovered_packages.clear()

#     def add_discovered_pakkage(self, pakkage: Pakkage):
#         self._discovered_packages[pakkage.id] = pakkage

#     def __getitem__(self, key: str) -> Pakkage | None:
#         if key in self._discovered_packages:
#             return self._discovered_packages[key]

#         if key in self.shortened_ids:
#             if len(self.shortened_ids[key]) == 1:
#                 return self._discovered_packages[self.shortened_ids[key][0]]

#         return None

#     def __len__(self):
#         return len(self._discovered_packages)

#     def __iter__(self):
#         return iter(self._discovered_packages)

#     def values(self):
#         return self._discovered_packages.values()

#     def items(self):
#         return self._discovered_packages.items()

#     def keys(self):
#         return self._discovered_packages.keys()

#     def __setitem__(self, key: str, value: Pakkage):
#         self._discovered_packages[key] = value
#         self._undiscovered_packages.discard(key)

#         splits = key.split("/")
#         if len(splits) == 2:
#             group = splits[0]
#             id = splits[1]

#             if id not in self.shortened_ids:
#                 self.shortened_ids[id] = []

#             self.shortened_ids[id].append(key)


#     def merge(self, new_pakkages: DiscoveredPakkages) -> DiscoveredPakkages:
#         """Merge the discovered pakkages."""

#         self._undiscovered_packages.update(new_pakkages._undiscovered_packages)

#         for id, pakkage in new_pakkages._discovered_packages.items():
#             if id in self._discovered_packages:
#                 versions = self._discovered_packages[id].versions
#                 versions.available.update(pakkage.versions.available)
#                 versions.installed = pakkage.versions.installed
#             else:
#                 self._discovered_packages[id] = pakkage

#             self._undiscovered_packages.discard(id)

#         for id, shortened_ids in new_pakkages.shortened_ids.items():
#             if id not in self.shortened_ids:
#                 self.shortened_ids[id] = []

#             self.shortened_ids[id].extend(shortened_ids)

#         return self

#     @staticmethod
#     def discover(connectors: list[Connector], quiet: bool = False) -> DiscoveredPakkages:

#         if not quiet:
#             Module.print_rule(f"Discovering pakkages")

#         pakkages = DiscoveredPakkages()
#         for connector in connectors:
#             discovered_pakkages = connector.discover()
#             pakkages.merge(discovered_pakkages)

#         # Check if all installed versions are also available, otherwise there are problems with reinstalling
#         for pakkage in pakkages._discovered_packages.values():
#             if (
#                 pakkage.versions.installed
#                 and len(pakkage.versions.available) > 0
#                 and pakkage.versions.installed.version not in pakkage.versions.available
#             ):
#                 logger.warn(
#                     f"Inconsistency detected for pakkage {pakkage.id}: installed version {pakkage.versions.installed.version} is not available in the discovered versions {pakkage.versions.available}"
#                 )

#         return pakkages


# class FetchedPakkages:
#     def __init__(self):
#         # self.quiet = quiet

#         self.pakkages_to_fetch: dict[str, Pakkage] = dict()
#         self.fetched_packages: dict[str, Pakkage] = dict()

#     def __getitem__(self, key: str) -> Pakkage:
#         return self.fetched_packages[key]

#     def __setitem__(self, key: str, value: Pakkage):
#         self.fetched_packages[key] = value

#     def merge(self, new_pakkages: FetchedPakkages) -> FetchedPakkages:
#         """Merge the fetched pakkages."""

#         self.undiscovered_packages.update(new_pakkages.undiscovered_packages)

#         for id, pakkage in new_pakkages.discovered_packages.items():
#             if id in self.fetched_packages:
#                 versions = self.fetched_packages[id].versions
#                 versions.available.update(pakkage.versions.available)
#                 versions.installed = pakkage.versions.installed
#             else:
#                 self.fetched_packages[id] = pakkage

#             self.undiscovered_packages.discard(id)

#         return self

#     def fetched(self, pakkage: Pakkage):
#         self.fetched_packages[pakkage.id] = pakkage
#         self.pakkages_to_fetch.pop(pakkage.id, None)

#     def fetch(self, connectors: list[Connector], quiet: bool = False) -> FetchedPakkages:

#         if not quiet:
#             Module.print_rule(f"Discovering pakkages")

#         pakkages = DiscoveredPakkages()
#         for connector in connectors:
#             discovered_pakkages = connector.discover()
#             pakkages.merge(discovered_pakkages)

#         # Check if all installed versions are also available, otherwise there are problems with reinstalling
#         for pakkage in pakkages.discovered_packages.values():
#             if (
#                 pakkage.versions.installed
#                 and len(pakkage.versions.available) > 0
#                 and pakkage.versions.installed.version not in pakkage.versions.available
#             ):
#                 logger.warn(
#                     f"Inconsistency detected for pakkage {pakkage.id}: installed version {pakkage.versions.installed.version} is not available in the discovered versions {pakkage.versions.available}"
#                 )

#         return pakkages


C = TypeVar("C", bound=ConnectorConfiguration)


class Connector(Module):

    PRIORITY = 100
    """The priority of the connector. The lower the number, the higher the priority."""

    CONFIG_CLS: Type[ConnectorConfiguration] | None = None
    """
    The configuration class used for the connector.
    If None, this connector does not require a configuration.
    """

    def __init__(self, pakkages: PakkageCollection, **kwargs):
        """Create a new connector."""
        super().__init__()

        self.pakkages = pakkages
        """The pakkage collection to work on."""

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

    def discover(self) -> PakkageCollection:
        """Discover all the packages with the implemented discoverer."""
        raise NotImplementedError()

    def fetch(self, pakkages_to_fetch: dict[str, Pakkage]) -> FetchedPakkages:
        """Fetch all the packages with the implemented fetcher."""
        raise NotImplementedError()
