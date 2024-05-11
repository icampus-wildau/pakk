from __future__ import annotations

import importlib
import logging
from types import ModuleType
from typing import TypeVar

from pakk.config import pakk_config
from pakk.logger import Logger

logger = logging.getLogger(__name__)

imported_classes: dict[str, type] = {}
imported_modules: dict[str, ModuleType] = {}

T = TypeVar("T")


class PakkModuleNotFoundException(Exception):
    def __init__(self, section: str, module_name: str, class_name: str | None = None):
        self.section = section
        self.module_name = module_name
        self.class_name = class_name

        if class_name is None:
            self.message = f"Module '{module_name}' defined in '[{section}]' could not be imported."
        else:
            self.message = f"Class '{class_name}' from '{module_name}' defined in '[{section}]' does not exist."

        super().__init__(Logger.get_plain_text(self.message))


class ModuleImporter:
    def __init__(self):
        pass

    @staticmethod
    def import_modules(cfg_section: str, cls: T = type) -> list[T]:
        cfg = pakk_config.get()

        # Import the defined setup and installation modules
        type_module_names = cfg[cfg_section]
        return_list = []

        logger.debug(f"Import configured classes from {cfg_section}")
        for module_name in type_module_names:
            name = type_module_names[module_name]
            return_list.append(ModuleImporter.import_type(module_name, name, cfg_section))

        return return_list

    @staticmethod
    def import_type(module_name: str, default_class_name: str = None, source_section: str = None) -> type:  # type: ignore
        """Import the given type by the module and class name."""

        global imported_classes
        global imported_modules

        if module_name in imported_classes:
            return imported_classes[module_name]

        if ":" in module_name:
            n_module, n_class = module_name.split(":")
        else:
            n_module = module_name
            n_class = default_class_name

        if n_module in imported_modules:
            module = imported_modules[n_module]
        else:
            try:
                module = importlib.import_module(n_module)
            except ModuleNotFoundError as e:
                raise PakkModuleNotFoundException(source_section, n_module, None) from e

            imported_modules[n_module] = module

        if not hasattr(module, n_class):
            raise PakkModuleNotFoundException(source_section, n_module, n_class)
            # raise Exception(f"Module {module_name} for installer does not have class {n_class}.")

        cls = getattr(module, n_class)
        imported_classes[module_name] = cls
        logger.debug(f"Imported class {n_class} from module {n_module}")

        return cls

    @staticmethod
    def get_class_from_module(module_name: str, class_name: str) -> type | None:
        """Get the class from the given module by name."""

        global imported_classes
        global imported_modules

        if not module_name in imported_classes:
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError as e:
                return None

        m = imported_modules.get(module_name, None)
        if not hasattr(m, class_name):
            return None

        return getattr(m, class_name)
