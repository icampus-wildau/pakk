from __future__ import annotations

import builtins
import logging
import os
import re

from rich.table import Table

import pakk.config.pakk_config as cfg
from pakk.args.base_args import BaseArgs
from pakk.config.pakk_config import Sections
from pakk.helper.file_util import remove_dir
from pakk.helper.lockfile import PakkLock
from pakk.logger import Logger
from pakk.modules.discoverer.base import DiscoveredPakkagesMerger
from pakk.modules.discoverer.discoverer_local import DiscovererLocal
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState
from pakk.pakkage.core import PakkageState
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)


def clean(**kwargs: str):
    base_config = BaseConfig.set(**kwargs)
    config = cfg.get()

    lock = PakkLock("clean")
    if not lock.access:
        return

    # flag_all = kwargs.get("all", False)
    # flag_available = kwargs.get("available", False)
    # flag_types = kwargs.get("types", False) or kwargs.get("extended", False)
    logger.info("Cleaning pakkages...")

    all_pakkges_dir: str = config.get_abs_path("all_pakkges_dir", Sections.SUBDIRS)  # type: ignore

    pakkages = {}

    # Go over each pakkage in the all directory and add it to the list
    for subdir, dirs, _ in os.walk(all_pakkges_dir):
        for d in dirs:
            abs_path = os.path.join(subdir, d)

            # Check if the directory contains a pakkage file
            pakkage_config = PakkageConfig.from_directory(abs_path)
            if pakkage_config is not None:
                versions = PakkageVersions()

                if pakkage_config.id is None or pakkage_config.state is None:
                    logger.warning(f"Removing {abs_path} because pakk.cfg or state is None.")
                    remove_dir(abs_path)
                elif pakkage_config.state.install_state == PakkageInstallState.FETCHED:
                    logger.warning(f"Removing {pakkage_config.id} because it is fetched but not installed.")
                    remove_dir(abs_path)
                else:
                    if (current_basename := os.path.basename(abs_path)) != pakkage_config.basename:
                        logger.warning(
                            f"Pakkage {pakkage_config.id} has a different name than its directory.\n\tRenaming .../{current_basename} to .../{pakkage_config.basename}..."
                        )
                        # Rename the directory
                        os.rename(abs_path, os.path.join(subdir, pakkage_config.basename))

        # First entry gives us all the subdirectories we need to check
        break

    return

    return pakkages

    # Check if pakk.cfg is missing or empty
    for pakkage in pakkages_discovered.values():
        # remove_dir(pakkage.)
        versions = pakkage.versions
        if pakkage.id is None:
            pakkage: Pakkage

            target = versions.target
            if target is not None:
                path = target.local_path
                logger.warn(f"Removing pakkage from {path} because its pakk.cfg is empty...")
                # remove_dir(path)
            else:
                logger.warn(f"Skipping pakkage {pakkage.id} because it has no target...")
        else:
            logger.info(f"Skipping pakkage {pakkage.id} because it has an id...")


if __name__ == "__main__":
    kwargs = {
        "all": True,
        # "types": True,
        # "extended": True,
    }

    clean(**kwargs)
