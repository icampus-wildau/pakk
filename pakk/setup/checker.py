from __future__ import annotations

import logging
import os

from extended_configparser.parser import ExtendedConfigParser

from pakk.config.base import PakkConfigBase
from pakk.helper.loader import PakkLoader
from pakk.logger import console
from pakk.setup.base import SetupBase

logger = logging.getLogger(__name__)


class PakkSetupChecker:
    _setup_routines: list[SetupBase] = []
    path = os.path.abspath(os.path.join(PakkConfigBase.get_configs_dir(), "setup_routines.cfg"))

    @staticmethod
    def get_setup_routines() -> list[SetupBase]:
        if len(PakkSetupChecker._setup_routines) == 0:
            PakkSetupChecker._setup_routines = PakkLoader.get_setup_routines()
            # Sort setup routines by priority
            PakkSetupChecker._setup_routines.sort(key=lambda x: x.PRIORITY)

        return PakkSetupChecker._setup_routines

    @staticmethod
    def check_setups(also_run: bool = False, reset_configs: bool = False):

        non_up_to_date_setups: list[str] = []

        if reset_configs:
            logger.info("Resetting setup configurations.")
            parser = ExtendedConfigParser()
            with open(PakkSetupChecker.path, "w") as file:
                parser.write(file)

        for setup_routine in PakkSetupChecker.get_setup_routines():
            if not setup_routine.is_up_to_date():
                logger.debug(f"Setup routine {setup_routine.NAME} is not up to date.")
                non_up_to_date_setups.append(setup_routine.NAME)

        if len(non_up_to_date_setups) > 0:
            logger.info("Some setup routines are not up to date.")
            if also_run:
                logger.info("Running setup routines.")
                return PakkSetupChecker.run_setups()
        else:
            logger.info("All setup routines are up to date.")

        return len(non_up_to_date_setups) == 0

    @staticmethod
    def run_setups():
        parser: ExtendedConfigParser | None = None
        failed_setups = []

        for setup_routine in PakkSetupChecker.get_setup_routines():
            if parser is None:
                parser = setup_routine.parser
                if os.path.exists(PakkSetupChecker.path):
                    parser.read(PakkSetupChecker.path)
            if not setup_routine.is_up_to_date():
                console.rule(f"Setup routine '{setup_routine.NAME}'")
                logger.info(f">>> Starting setup routine '{setup_routine.NAME}'")
                if setup_routine.run_setup_with_except(reset_sudo=True):
                    setup_routine.save_setup_version()
                else:
                    logger.error(f"<<< Setup routine '{setup_routine.NAME}' failed.")
                    failed_setups.append(setup_routine.NAME)

        if parser is not None:
            logger.info("Saving setup versions")
            with open(PakkSetupChecker.path, "w") as file:
                parser.write(file)

        if len(failed_setups) > 0:
            console.rule("[red]Failed setup routines")
            logger.error(f"Failed to run setup routines: {', '.join(failed_setups)}")
            return False

        logger.info("All setup routines are up to date.")
        return True
