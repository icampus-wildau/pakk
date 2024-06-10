from __future__ import annotations

import logging
import os

# import pakk.config.pakk_config as cfg
from pakk import ROOT_DIR
from pakk.args.base_args import PakkArgs
from pakk.config.main_cfg import MainConfig
from pakk.helper.lockfile import PakkLock
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.local import LocalConnector

# from pakk.modules.discoverer.base import DiscoveredPakkagesMerger
# from pakk.modules.discoverer.discoverer_local import DiscovererLocal

logger = logging.getLogger(__name__)


def update(pakkage_names: list[str] | str, **kwargs: str):

    config = MainConfig.get_config()

    lock = PakkLock("update")
    if not lock.access:
        logger.error("Wait for the other pakk process to finish to continue.")
        return

    flag_all = kwargs.get("all", False)
    flag_auto = kwargs.get("auto", False)
    flag_self = kwargs.get("selfupdate", False)

    execute = not flag_auto or config.autoupdate.enabled_for_pakk.value
    if not execute:
        logger.info("Auto update disabled, skipping...")
        return

    # Execute a self update by pulling the latest version from gitlab
    if flag_self:
        project_dir = os.path.abspath(os.path.join(ROOT_DIR, ".."))
        project_url = config.autoupdate.project_url.value
        update_channel = config.autoupdate.update_channel.value

        if update_channel == "pip":
            logger.info("Executing self update via pip...")
            os.system(f"pip install --upgrade pakk")
            return

        if not project_url.startswith("https"):
            logger.error("Auto update is enabled but the project url is not a valid https url.")
            return

        logger.info(f"Executing self update via git ({project_url}) using channel '{update_channel}'...")

        # Check if project dir is a git repository
        if os.path.exists(os.path.join(project_dir, ".git")):
            # If so, pull from channel and install
            cmd = f"cd {project_dir} && git pull origin {update_channel} && pip install -e ."
            logger.info(f"Executing command: {cmd}")
            os.system(cmd)
            return

        # Otherwise, pip install the project from the given channel
        cmd = f"pip install --upgrade git+{project_url}@{update_channel}"
        logger.info(f"Executing command: {cmd}")
        os.system(cmd)
        return

    from pakk.actions.install import install

    install_kwargs = {
        "upgrade": True,
    }

    PakkArgs.update(**install_kwargs)

    if flag_all or (not flag_self and len(pakkage_names) == 0):
        logger.info("Updating all pakkages...")
        pakkages = PakkageCollection()
        pakkages.discover([LocalConnector()])
        lock.unlock()
        install(list(pakkages.keys()), **install_kwargs)
        return

    if len(pakkage_names) > 0:
        logger.info(f"Updating pakkages: {pakkage_names}")
        lock.unlock()
        install(pakkage_names, **install_kwargs)
        return
