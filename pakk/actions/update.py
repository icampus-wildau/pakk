from __future__ import annotations

import logging
import os
import subprocess
import sys

# import pakk.config.pakk_config as cfg
from pakk import ROOT_DIR
from pakk.args.base_args import PakkArgs
from pakk.config.main_cfg import MainConfig
from pakk.connector.base import PakkageCollection
from pakk.connector.local import LocalConnector
from pakk.environments.base import Environment
from pakk.helper.lockfile import PakkLock

# from pakk.discoverer.base import DiscoveredPakkagesMerger
# from pakk.discoverer.discoverer_local import DiscovererLocal

logger = logging.getLogger(__name__)


def is_git_repo_clean(dir: str):
    try:
        # Run 'git status --porcelain' to get the status of the repo
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True, cwd=dir)

        # If the output is empty, the repo is clean
        if result.stdout.strip() == "":
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        return False


def remote_branch_exists(remote_name: str, branch_name: str):
    try:
        # Run 'git ls-remote --heads' to list all branches on the remote
        result = subprocess.run(
            ["git", "ls-remote", "--heads", remote_name, branch_name], capture_output=True, text=True, check=True
        )

        # Check if the output contains the branch
        if result.stdout.strip():
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        return False


def wait_for_internet(timeout=1, interval=1, max_wait=10):
    import time

    import requests

    url = "http://www.google.com"
    total_wait = 0
    while True:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                logger.info(f"Internet connection is available after {total_wait} seconds of waiting.")
                break
        except requests.ConnectionError:
            logger.info("No internet connection. Waiting...")
        time.sleep(interval)
        total_wait += interval
        if max_wait and total_wait >= max_wait:
            logger.warning(f"Maximum wait time of {max_wait} seconds reached. Exiting.")
            return False

    return True


def _self_update():
    config = MainConfig.get_config()
    project_dir = os.path.abspath(os.path.join(ROOT_DIR, ".."))
    project_url = config.autoupdate.project_url.value
    update_channel = config.autoupdate.update_channel.value
    pip = Environment.get_pip()

    pakk_is_git_repo = os.path.exists(os.path.join(project_dir, ".git"))

    # Check if project dir is a git repository
    if pakk_is_git_repo:
        if is_git_repo_clean(project_dir):
            if not remote_branch_exists("origin", update_channel):
                logger.warning(f"Given update channel {update_channel} does not exist on remote.")
                return

            # If so, pull from channel and install
            cmd = f"cd {project_dir} && git pull origin {update_channel} && {pip} install -e ."
            logger.info(f"Executing self update command: {cmd}")
            os.system(cmd)
            return
        else:
            logger.warning("Skipping pakk selfupdate because it has uncommitted changes.")
            return

    if update_channel == "pip":
        cmd = f"{pip} install --upgrade pakk-package-manager"
        logger.info(f"Executing self update via pip: {cmd}")
        os.system(cmd)
        return

    if not project_url.startswith("https"):
        logger.error("Auto update is enabled but the project url is not a valid https url.")
        return

    logger.info(f"Executing self update via git ({project_url}) using channel '{update_channel}'...")

    # Otherwise, pip install the project from the given channel
    cmd = f"{pip} install --upgrade git+{project_url}@{update_channel}"
    logger.info(f"Executing self update command: {cmd}")
    os.system(cmd)
    return


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

    wait_for_internet()

    # Execute a self update by pulling the latest version from gitlab
    if flag_self:
        _self_update()

    from pakk.actions.install import install
    from pakk.cli import catched_execution

    install_kwargs = {
        "upgrade": True,
    }

    PakkArgs.update(**install_kwargs)

    if flag_all or (not flag_self and len(pakkage_names) == 0):
        logger.info("Updating all pakkages...")
        pakkages = PakkageCollection()
        pakkages.discover([LocalConnector()])
        lock.unlock()
        catched_execution(install, list(pakkages.keys()), **install_kwargs)
        return

    if len(pakkage_names) > 0:
        logger.info(f"Updating pakkages: {pakkage_names}")
        lock.unlock()
        catched_execution(install, pakkage_names, **install_kwargs)
        return
