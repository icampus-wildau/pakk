from __future__ import annotations

import logging
import os

from extended_configparser.parser import ExtendedConfigParser

from pakk.config.base import PakkConfigBase
from pakk.helper.loader import PakkLoader
from pakk.logger import console
from pakk.setup.base import SetupBase

logger = logging.getLogger(__name__)


class SetupRequiredException(Exception):
    pass


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
    def require_setups(setups: list[SetupBase | type[SetupBase]], run_if_not_up_to_date: bool = True):
        not_up_to_date = PakkSetupChecker.check_setups(setups)
        if len(not_up_to_date) > 0:
            if run_if_not_up_to_date:
                logger.info(f"Running required setup routines {len(not_up_to_date)}.")
                failed = PakkSetupChecker.run_setups(not_up_to_date)
                if len(failed) > 0:
                    logger.error("Some setup routines failed.")
                    raise SetupRequiredException(
                        f"Failed to run setup routines: {', '.join([f'{f.NAME}@{f.VERSION}' for f in failed])}"
                    )
            else:
                raise SetupRequiredException(
                    f"Setup routines are not up to date: {', '.join([f'{f.NAME}@{f.VERSION}' for f in not_up_to_date])}"
                )

    @staticmethod
    def check_setups(setups: list[SetupBase | type[SetupBase]]) -> list[SetupBase]:
        """Check the given setups if they are up to date.

        Parameters
        ----------
        setups : list[SetupBase  |  type[SetupBase]]
            Setups to check.

        Returns
        -------
        list[SetupBase]
            All setups that are not up to date.
        """
        routines = PakkSetupChecker.get_setup_routines()
        not_up_to_date: list[SetupBase] = []
        for setup in setups:
            if isinstance(setup, type):
                routine = next((r for r in routines if isinstance(r, setup)), None)
                if routine is not None:
                    if not routine.is_up_to_date():
                        logger.info(f"Setup routine {routine.NAME} is not up to date.")
                        not_up_to_date.append(routine)
            else:
                if not setup.is_up_to_date():
                    not_up_to_date.append(setup)

        not_up_to_date.sort(key=lambda x: x.PRIORITY)
        return not_up_to_date

    @staticmethod
    def check_all_setups(also_run: bool = False, reset_configs: bool = False):

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
    def run_setups(setup_routines: list[SetupBase] | None = None) -> list[SetupBase]:
        parser: ExtendedConfigParser | None = None
        failed_setups: list[SetupBase] = []

        if setup_routines is None:
            setup_routines = PakkSetupChecker.get_setup_routines()
        for setup_routine in setup_routines:
            if parser is None:
                parser = setup_routine.parser
                if os.path.exists(PakkSetupChecker.path):
                    parser.read(PakkSetupChecker.path)
            if not setup_routine.is_up_to_date():
                console.rule(f"Setup routine '{setup_routine.NAME} @ {setup_routine.VERSION}'")
                logger.info(f">>> Starting setup routine '{setup_routine.NAME}'")
                if setup_routine.run_setup_with_except(reset_sudo=True):
                    setup_routine.save_setup_version()
                else:
                    logger.error(f"<<< Setup routine '{setup_routine.NAME}' failed.")
                    failed_setups.append(setup_routine)

        if parser is not None:
            logger.info("Saving setup versions")
            with open(PakkSetupChecker.path, "w") as file:
                parser.write(file)

        if len(failed_setups) > 0:
            console.rule("[red]Failed setup routines")
            logger.error(f"Failed to run setup routines: {', '.join([f.NAME for f in failed_setups])}")
            return failed_setups

        logger.info("All setup routines are up to date.")
        return failed_setups
