from __future__ import annotations

import logging
import os

from extended_configparser.parser import ExtendedConfigParser

from pakk import ROOT_DIR
from pakk.config.main_cfg import MainConfig
from pakk.modules.environments.base import EnvironmentBase
from pakk.setup.base import SetupBase

logger = logging.getLogger(__name__)


class PakkGroupSetup(SetupBase):
    NAME = "groups"
    VERSION = "1.0.0"
    PRIORITY = 50

    def __init__(self, parser: ExtendedConfigParser, environment: EnvironmentBase):
        super().__init__(parser, environment)

    def run_setup(self) -> bool:

        main_cfg = MainConfig.get_config()
        path_section = main_cfg[main_cfg.paths.pakk_dir_section.name]
        dirs: list[str] = [ROOT_DIR]
        for option in path_section:
            dirs.append(path_section[option])

        # Create pakk group
        logger.info(f"Setting up groups for pakk...")
        logger.info(f"Creating group '{self.group_name}'")
        self.system(f"sudo groupadd {self.group_name} -f")

        # Get the user name:
        user_name = os.environ.get("USER")
        logger.info(f"Adding user '{user_name}' to group '{self.group_name}'")
        self.system(f"sudo usermod -a -G {self.group_name} {user_name}")

        # Assign pakk package and data directory to pakk group
        for dir in dirs:
            logger.info(f"Assigning '{dir}' to group '{self.group_name}' and grant write access")
            self.system(f"sudo chgrp -R {self.group_name} {dir}")
            self.system(f"sudo chmod -R g+w {dir}")

        return True
