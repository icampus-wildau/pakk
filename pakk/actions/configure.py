from __future__ import annotations

import logging
from typing import Type

from pakk.config.base import PakkConfigBase
from pakk.config.main_cfg import MainConfig
from pakk.helper.loader import PakkLoader
from pakk.logger import Logger
from pakk.modules.module import Module

logger = logging.getLogger(__name__)


def configure(**kwargs):
    # f = Figlet(font='cyberlarge')
    verbose = kwargs.get("verbose", False)
    reset = kwargs.get("reset", False)

    console = Logger.get_console()
    Module.print_rule("Pakk Configuration")

    configs_specified = kwargs.get("configuration", None)
    configs_are_specified = len(configs_specified) > 0 if configs_specified is not None else False

    configs_cls: dict[str, Type[PakkConfigBase]] = dict()
    configs_cls["main"] = MainConfig

    connectors = PakkLoader.get_connector_classes(False)
    types = PakkLoader.get_type_classes()
    for type in types:
        if type.CONFIG_CLS is not None:
            configs_cls[type.__name__] = type.CONFIG_CLS

    for connector in connectors:
        if connector.CONFIG_CLS is not None:
            configs_cls[connector.__name__] = connector.CONFIG_CLS

    if configs_specified is not None:
        configs_cls = {k: v for k, v in configs_cls.items() if k == configs_specified}

    if len(configs_cls) == 0:
        console.print("No files to configure found.")
        return

    for config_name, config_cls in configs_cls.items():
        config = config_cls.get_config()

        if configs_are_specified or not config.exists():
            Module.print_rule(f"Configuring {config_name}")
            console.print(f"Configuring {config_name} at {config.config_path}")
            config.inquire(not reset)
            config.write()
            console.print(f"Finished configuration of {config_name} at {config.config_path}!")
        else:
            console.print(
                f"Configuration file {config.config_path} already exists. Use 'pakk configure {config_name}' to explicitly configure  it."
            )
