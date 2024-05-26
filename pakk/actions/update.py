from __future__ import annotations

import builtins
import logging
import os
import re

from rich.table import Table

import pakk.config.pakk_config as cfg
from pakk import ROOT_DIR
from pakk.args.base_args import BaseArgs
from pakk.helper.lockfile import PakkLock
from pakk.logger import Logger
from pakk.modules.discoverer.base import DiscoveredPakkagesMerger
from pakk.modules.discoverer.discoverer_local import DiscovererLocal

logger = logging.getLogger(__name__)


def update(pakkage_names: list[str] | str, **kwargs: str):
    config = cfg.get()

    lock = PakkLock("update")
    if not lock.access:
        logger.error("Wait for the other pakk process to finish to continue.")
        return

    flag_all = kwargs.get("all", False)
    flag_auto = kwargs.get("auto", False)
    flag_self = kwargs.get("selfupdate", False)

    execute = not flag_auto or config.getboolean("AutoUpdate", "enabled", fallback=False)
    if not execute:
        logger.info("Auto update disabled, skipping...")
        return

    # Execute a self update by pulling the latest version from gitlab
    if flag_self:
        projet_dir = os.path.abspath(os.path.join(ROOT_DIR, ".."))
        project_access_token = config.get("AutoUpdate", "project_access_token", fallback=None)
        project_url = config.get("AutoUpdate", "project_url", fallback=None)

        if project_access_token is None or project_url is None:
            logger.error("Auto update is enabled but no project access token or project url is configured.")
            return

        if not project_url.startswith("https"):
            logger.error("Auto update is enabled but the project url is not a valid https url.")
            return

        logger.info("Executing self update...")
        project_url = project_url.replace("https://", f"https://pakk:{project_access_token}@")
        cmd = f"cd {projet_dir} && git pull {project_url} && pip install -e ."
        logger.info(f"Executing command: {cmd}")
        os.system(cmd)
        # os.system(f"cd {projet_dir} && git pull {project_url} && pip install -e .")

    from pakk.actions.install import install

    install_kwargs = {
        "upgrade": True,
    }

    if flag_all or (not flag_self and len(pakkage_names) == 0):
        logger.info("Updating all pakkages...")
        discoverer = DiscoveredPakkagesMerger([DiscovererLocal()])
        pakkages_discovered = discoverer.merge()
        lock.unlock()
        install(pakkages_discovered.keys(), **install_kwargs)
        return

    if len(pakkage_names) > 0:
        logger.info(f"Updating pakkages: {pakkage_names}")
        lock.unlock()
        install(pakkage_names, **install_kwargs)
        return
