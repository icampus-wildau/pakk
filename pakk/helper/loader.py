
import importlib
import inspect
import os
import pkgutil
from pakk.modules.connector.base import Connector

import logging

logger = logging.getLogger(__name__)


class PakkLoader:
    __connector_sub_paths = ["modules.connector", "connector"]

    @staticmethod
    def get_connectors():
        
        # Get all installed python packages starting with "pakk"
        logger.debug("Fetching all installed pakk modules...")
        pakk_modules: list[str] = []
        for _, module_name, _ in pkgutil.iter_modules():
            if module_name.startswith("pakk"):
                pakk_modules.append(module_name)
    
        # Get all modules that qualify as connectors
        connector_modules = []
        for pakk_module in pakk_modules:
            for sub_path in PakkLoader.__connector_sub_paths:
                module_path = f"{pakk_module}.{sub_path}"

                for _, module_name, _ in pkgutil.iter_modules([module_path.replace(".", os.sep)]):
                    connector_modules.append(".".join([pakk_module, sub_path, module_name]))
        logger.debug(f"Found connector modules: {connector_modules}")
        
        print(connector_modules)
        # return
        # Import all connector classes that inherit from Connector
        connectors = []
        for module_name in connector_modules:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Connector) and obj != Connector:
                    connectors.append(obj)
        logger.debug(f"Found connectors: {connectors}")
        print(connectors)
        return connectors
    
        return

if __name__ == "__main__":
    PakkLoader.get_connectors()