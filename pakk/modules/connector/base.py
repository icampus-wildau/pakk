from __future__ import annotations

import logging
from typing import Type
from typing import TypeVar

from pakk.config.base import ConnectorConfiguration
from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState
from pakk.pakkage.core import PakkageVersions

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

    ####################################################################################################################
    ### Collection functions
    ####################################################################################################################

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

            if pakkage.id not in self.id_abbreviations[id]:
                self.id_abbreviations[id].append(pakkage.id)

    def get_pakkage(self, id: str) -> Pakkage | None:
        """Get a pakkage by its id or its abbreviation."""

        if id in self.pakkages:
            return self.pakkages[id]

        if id in self.id_abbreviations:
            if len(self.id_abbreviations[id]) == 1:
                return self.pakkages[self.id_abbreviations[id][0]]

        return None

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
            for id in ids:
                if id not in self.id_abbreviations[abbr]:
                    self.id_abbreviations[abbr].append(id)

        # Merge ids_to_be_installed
        self.ids_to_be_installed.update(new_pakkages.ids_to_be_installed)

        return self

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

    ####################################################################################################################
    ### Calculated properties
    ####################################################################################################################

    @property
    def pakkages_to_fetch(self) -> dict[str, Pakkage]:
        """Get all pakkages that have versions to be fetched."""
        return {pakkage.id: pakkage for pakkage in self.pakkages.values() if pakkage.versions.is_update_candidate()}

    @property
    # def pakkage_configs_to_fetch(self) -> list[Tuple[Pakkage, PakkageConfig]]:
    def pakkage_configs_to_fetch(self) -> list[PakkageConfig]:
        """Get all pakkage versions that have to be fetched."""
        pakkages = self.pakkages_to_fetch
        versions = [p.versions.target for p in pakkages.values() if p.versions.target is not None]
        # versions = [(p, p.versions.target) for p in pakkages.values() if p.versions.target is not None]
        return versions

    @property
    def startable_pakkages(self) -> list[PakkageConfig]:
        """Get all pakkages that are startable."""
        return [
            p.versions.installed
            for p in self.pakkages.values()
            if p.versions.installed is not None and p.versions.installed.is_startable()
        ]

    ####################################################################################################################
    ### Connector functions
    ####################################################################################################################

    def discover(
        self, connectors: list[Connector], pakkage_ids: list[str] | None = None, quiet: bool = False
    ) -> PakkageCollection:
        """
        Discover pakkages with the given connectors.
        The discovery process addes packages to the collection.
        """

        if not quiet:
            Module.print_rule(f"Discovering pakkages")

        for connector in connectors:
            discovered_pakkages = connector.discover(pakkage_ids)
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

        pakkages_to_fetch = self.pakkages_to_fetch
        configs_to_fetch = self.pakkage_configs_to_fetch

        for connector in connectors:

            configs = [p for p in configs_to_fetch if connector.is_fetchable(p)]
            # pakkages, configs = zip(*pakkage_tuples)
            if len(configs) > 0:
                logger.info(f"{connector.__class__.__name__}: fetching {len(configs)} pakkages")
                connector.fetch(configs)

        for pakkage in pakkages_to_fetch.values():
            # If there was an installed version, copy the state
            if pakkage.versions.target is not None:
                if pakkage.versions.target.state.install_state == PakkageInstallState.FETCHED:
                    pakkage.versions.target.state.copy_from(pakkage.versions.installed)
                    pakkage.versions.target.save_state()
                else:
                    logger.error(
                        f"Target version {pakkage.versions.target.version} of {pakkage.id} has not been fetched properly."
                    )

        logger.info(f"Finished fetching of {len(pakkages_to_fetch)} pakkages.")

        return self


C = TypeVar("C", bound=ConnectorConfiguration)


class Connector(Module):

    PRIORITY = 100
    """The priority of the connector. The lower the number, the higher the priority."""

    CONFIG_CLS: Type[ConnectorConfiguration] | None = None
    """
    The configuration class used for the connector.
    If None, this connector does not require a configuration.
    """

    def __init__(self, **kwargs):  # pakkages: PakkageCollection,
        """Create a new connector."""
        super().__init__()

        # self.pakkages = pakkages
        # """The pakkage collection to work on."""

        # self.config = self.CONFIG_CLS.get_config() if self.CONFIG_CLS else None

    @property
    def connector_attributes_key(self):
        return self.__class__.__module__ + "." + self.__class__.__name__

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

    def discover(self, pakkage_ids: list[str] | None = None) -> PakkageCollection:
        """Discover pakkages with the connector.

        Parameters
        ----------
        pakkage_ids : list[str] | None
            If given, contains a list of names that should be discovered. If None, all pakkages should be discovered.
            This is used for connectors, that cannot fetch all available pakkages by default but instead need a name.
        Returns
        -------
        PakkageCollection
            A pakkage collection with the discovered pakkages.

        """

        logger.error("Discover method not implemented for %s", self.__class__.__name__)
        raise NotImplementedError()

    def is_fetchable(self, pakkage_config: PakkageConfig) -> bool:
        """
        Check if a pakkage can be fetched by the connector.
        By default it checks, if the pakkage config has a fitting connector attribute.
        """
        return self.connector_attributes_key in pakkage_config.connector_attributes

    def fetch(self, pakkages_to_fetch: list[PakkageConfig]) -> None:
        """
        Fetch all the packages with the implemented fetcher.
        The fetch method should set the local_path attribute and the state to FETCHED.
        """
        logger.error("Fetch method not implemented for %s", self.__class__.__name__)
        raise NotImplementedError()
