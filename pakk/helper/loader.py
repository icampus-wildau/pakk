from __future__ import annotations

import importlib
import inspect
import logging
import os
import pkgutil
from typing import Type
from typing import TypeVar

from extended_configparser.parser import ExtendedConfigParser

from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.environments.loader import get_current_environment
from pakk.modules.environments.loader import get_current_environment_cls
from pakk.modules.types.base import TypeBase
from pakk.setup.base import SetupBase

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PakkLoader:
    __connector_sub_paths = ["modules.connector", "connector"]
    __types_sub_paths = ["modules.types", "types"]
    __setup_sub_paths = ["modules.connector", "connector", "modules.types", "types", "setup"]

    __pakk_modules: list[tuple[str, str]] = []

    @staticmethod
    def __get_pakk_modules() -> list[tuple[str, str]]:
        if len(PakkLoader.__pakk_modules) > 0:
            return PakkLoader.__pakk_modules

        # Get all installed python packages starting with "pakk"
        logger.debug("Fetching all installed pakk modules...")
        pakk_modules: list[tuple[str, str]] = []
        for module_path, module_name, _ in pkgutil.iter_modules():
            if module_name.startswith("pakk"):
                pakk_modules.append((module_path.path, module_name))  # type: ignore

        PakkLoader.__pakk_modules = pakk_modules
        return pakk_modules

    @staticmethod
    def __get_pakk_sub_modules(paths: list[str]) -> list[str]:
        pakk_modules = PakkLoader.__get_pakk_modules()
        sub_modules: list[str] = []
        for module_path, pakk_module in pakk_modules:
            for sub_path in paths:
                sub_module_path = f"{pakk_module}.{sub_path}"
                search_path = os.path.join(module_path, sub_module_path.replace(".", os.sep))
                for _, module_name, _ in pkgutil.iter_modules([search_path]):
                    sub_modules.append(".".join([pakk_module, sub_path, module_name]))
        return sub_modules

    @staticmethod
    def get_module_subclasses(module_names: str | list[str], base_class: type[T]) -> list[type[T]]:
        if isinstance(module_names, str):
            module_names = [module_names]

        classes = []
        for module_name in module_names:
            module = importlib.import_module(module_name)
            for name, cls in inspect.getmembers(
                module, lambda x: inspect.isclass(x) and issubclass(x, base_class) and x != base_class
            ):
                classes.append(cls)
        return classes

    @staticmethod
    def get_connector_classes(skip_disabled: bool = True) -> list[type[Connector]]:

        connector_modules = PakkLoader.__get_pakk_sub_modules(PakkLoader.__connector_sub_paths)
        logger.debug(f"Found connector modules: {connector_modules}")

        # Import all connector classes that inherit from Connector
        connectors = PakkLoader.get_module_subclasses(connector_modules, Connector)
        logger.debug(f"Found connectors: {connectors}")

        valid_connectors: list[type[Connector]] = []
        # Check if connectors require configuration
        for connector in connectors:
            if skip_disabled and not connector.is_enabled():
                logger.info(f"Skipping disabled connector '{connector.__name__}'.")
                continue

            if skip_disabled and not connector.is_configured():
                logger.error(
                    f"Connector {connector.__name__} is enabled but not configured. Please configure it using `pakk configure {connector.__name__}`."
                )
                continue

            valid_connectors.append(connector)

            # if connector.CONFIG_CLS is not None:

        # Sort connectors by PRIORITY
        valid_connectors.sort(key=lambda x: x.PRIORITY)

        return valid_connectors

    @staticmethod
    def get_connector_instances():
        connectors = PakkLoader.get_connector_classes()
        instances = []
        for connector_cls in connectors:
            connector = connector_cls()
            instances.append(connector)
        return instances

    @staticmethod
    def get_type_classes() -> list[type[TypeBase]]:
        type_modules = PakkLoader.__get_pakk_sub_modules(PakkLoader.__types_sub_paths)
        logger.debug(f"Found type modules: {type_modules}")

        # Import all type classes that inherit from TypeBase
        types = PakkLoader.get_module_subclasses(type_modules, TypeBase)
        logger.debug(f"Found types: {types}")

        return types

    @staticmethod
    def get_setup_routines() -> list[SetupBase]:
        setup_modules = PakkLoader.__get_pakk_sub_modules(PakkLoader.__setup_sub_paths)
        logger.debug(f"Found setup modules: {setup_modules}")

        setup_routines_cls = PakkLoader.get_module_subclasses(setup_modules, SetupBase)
        logger.debug(f"Found setup routines: {setup_routines_cls}")

        from pakk.setup.checker import PakkSetupChecker

        parser = ExtendedConfigParser()
        parser.read(PakkSetupChecker.path)

        env = get_current_environment()
        setup_routines: list[SetupBase] = []
        for setup_cls in setup_routines_cls:
            try:
                setup_routines.append(setup_cls(parser, env))
            except Exception as e:
                logger.error(f"Error while creating setup routine '{setup_cls.__name__}': {e}")

        return setup_routines
