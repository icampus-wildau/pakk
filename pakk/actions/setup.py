from __future__ import annotations

import logging
import os

from pakk.args.base_args import BaseArgs
from pakk.config.main_cfg import MainConfig
from pakk.setup.checker import PakkSetupChecker

# from pyfiglet import Figlet

# Probably using https://github.com/CITGuru/PyInquirer

logger = logging.getLogger(__name__)


def setup(**kwargs):
    base_config = BaseArgs.set(**kwargs)
    flag_verbose = base_config.verbose
    reset = kwargs.get("reset", False)

    # Check if executed on linux
    if os.name != "posix":
        logger.error("This command is only available on linux")
        return

    logger.info("Starting pakk setup")

    # Check if config exists
    config = MainConfig.get_config()

    # Check and run all setup routines
    PakkSetupChecker.check_all_setups(also_run=True, reset_configs=reset)

    return


if __name__ == "__main__":
    setup()
