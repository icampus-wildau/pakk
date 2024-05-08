
import importlib
import inspect
import os
import pkgutil
from typing import Type
from pakk.modules.connector.base import Connector

import logging

logger = logging.getLogger(__name__)


class PakkLoader:
    __connector_sub_paths = ["modules.connector", "connector"]

    @staticmethod
    def get_connector_classes() -> list[type[Connector]]:
        
        # Get all installed python packages starting with "pakk"
        logger.debug("Fetching all installed pakk modules...")
        pakk_modules: list[tuple[str, str]] = []
        for module_path, module_name, _ in pkgutil.iter_modules():
            if module_name.startswith("pakk"):
                pakk_modules.append((module_path.path, module_name))
    
        # Get all modules that qualify as connectors
        connector_modules = []
        for module_path, pakk_module in pakk_modules:
            for sub_path in PakkLoader.__connector_sub_paths:
                sub_module_path = f"{pakk_module}.{sub_path}"
                search_path = os.path.join(module_path, sub_module_path.replace(".", os.sep))
                # p = module_path.replace(".", os.sep)
                # m = importlib.import_module(module_path)
                # np = m.__path__
                # print(p)
                # for _, module_name, _ in pkgutil.iter_modules([module_path.replace(".", os.sep)]):
                for _, module_name, _ in pkgutil.iter_modules([search_path]):
                    connector_modules.append(".".join([pakk_module, sub_path, module_name]))
        logger.debug(f"Found connector modules: {connector_modules}")
        
        # print(connector_modules)
        # return
        # Import all connector classes that inherit from Connector
        connectors: list[Type[Connector]] = []
        for module_name in connector_modules:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Connector) and obj != Connector:
                    connectors.append(obj)
        logger.debug(f"Found connectors: {connectors}")
        # print(connectors)


        # Check if connectors require configuration
        for connector in connectors:            
            if connector.is_enabled():
                if not connector.is_configured():
                    logger.error(f"Connector {connector.__name__} is enabled but not configured. Please configure it using `pakk configure {connector.__name__}`.")

            # if connector.CONFIG_CLS is not None:
                


        return connectors
    