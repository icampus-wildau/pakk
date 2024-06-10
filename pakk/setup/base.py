from __future__ import annotations

import logging
import os

from extended_configparser.parser import ExtendedConfigParser

from pakk.modules.environments.base import EnvironmentBase

logger = logging.getLogger(__name__)


class CommandFailedException(Exception):
    pass


class SetupBase:
    VERSION = "0.0.1"
    NAME = "pakk"
    PRIORITY = 100

    def __init__(self, parser: ExtendedConfigParser, environment: EnvironmentBase):
        self.parser = parser
        self.group_name = "pakk"
        self.user_name = os.environ.get("USER")
        self.environment = environment

    def system(self, command: str, ignore_exit_codes: list[int] = []):
        """Wrapper for os.system that raises an exception if the command fails."""
        code = os.system(command)
        if code != 0:
            if code not in ignore_exit_codes:
                raise CommandFailedException(f"Command '{command}' failed with code '{code}'")

        return code

    def run_setup_with_except(self, reset_sudo: bool = True) -> bool:
        success = False
        try:
            success = self.run_setup()
        except CommandFailedException as e:
            print(e)

        if reset_sudo:
            self.system("sudo -k")

        return success

    def run_setup(self) -> bool:
        raise NotImplementedError

    def save_setup_version(self):
        self.parser.set("Setup", self.NAME, self.VERSION)

    def get_configured_version(self) -> str | None:
        return self.parser.get("Setup", self.NAME, fallback=None)

    def is_up_to_date(self):
        # logger.info(f"Checking if {self.NAME} is up to date... {self.get_configured_version()} / {self.VERSION}")
        if self.get_configured_version() is None:
            return False
        return self.get_configured_version() == self.VERSION
