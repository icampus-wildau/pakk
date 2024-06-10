from __future__ import annotations

import logging
import os
import tempfile

from extended_configparser.parser import ExtendedConfigParser

from pakk.modules.environments.base import EnvironmentBase
from pakk.modules.manager.systemd.unit_generator import PakkAutoUpdateService
from pakk.modules.manager.systemd.unit_generator import PakkParentService
from pakk.modules.manager.systemd.unit_generator import PakkServiceFileBase
from pakk.modules.manager.systemd.unit_generator import ServiceFile
from pakk.setup.base import SetupBase

logger = logging.getLogger(__name__)


class ServiceSetup(SetupBase):
    NAME = "pakk_service"
    VERSION = "1.0.0"
    PRIORITY = 60

    def __init__(self, parser: ExtendedConfigParser, environment: EnvironmentBase):
        super().__init__(parser, environment)

    def run_setup(self) -> bool:
        # Init pakk service
        logger.info("Setup pakk services")

        services: list[PakkServiceFileBase] = [PakkParentService(), PakkAutoUpdateService()]
        logger.info(f"Creating directory '{ServiceFile.PATH}' for service files")
        self.system(f"sudo mkdir -p {ServiceFile.PATH}")

        temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        temp_file.flush()
        temp_file.close()
        temp_file_path = temp_file.name
        for s in services:
            logger.info(f"Creating service file for '{s.service_file.name}'")
            with open(temp_file_path, "w") as f:
                f.write(s.service_file.content)

            logger.info(f"Copying {temp_file_path} to '{s.service_file.filepath}'")
            self.system(f"sudo cp {temp_file_path} {s.service_file.filepath}")

        # Remove temp file
        logger.info(f"Cleaning up temp file '{temp_file_path}'")
        self.system(f"rm {temp_file_path}")

        logger.info(f"Reloading systemctl daemon")
        self.system(f"sudo systemctl daemon-reload")

        for s in services:
            logger.info(f"Enabling '{s.service_file.filepath}'")
            self.system(f"sudo systemctl enable {s.service_file.filepath}")

        return True
