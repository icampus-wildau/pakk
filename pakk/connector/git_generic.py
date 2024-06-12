from __future__ import annotations

import logging
import os
import subprocess

from pakk.args.install_args import InstallArgs
from pakk.config.main_cfg import MainConfig
from pakk.helper.file_util import remove_dir
from pakk.helper.progress import TaskPbar
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState

logger = logging.getLogger(__name__)


class GenericGitHelper:
    @staticmethod
    def fetch_pakkage_version_with_git(
        target_version: PakkageConfig, url: str, branch: str, task: TaskPbar | None
    ) -> None:

        # Get the destination path
        fetched_dir = MainConfig.get_config().paths.fetch_dir.value
        name = target_version.basename
        path = os.path.join(fetched_dir, name)

        args = InstallArgs.get()

        fetch = True
        if os.path.exists(path):
            if args.refetch or args.clear_cache:
                logger.debug(f"Directory {path} already exists. Refetching it.")

                # delete existing directory
                remove_dir(path)
            else:
                # Check if the directory is empty
                with os.scandir(path) as it:
                    if not any(it):
                        fetch = True
                        logger.debug(f"Directory {path} already exists but is empty. Refetching it.")
                        remove_dir(path)
                    else:
                        fetch = False
                        logger.debug(f"Directory {path} already exists. Skipping fetch and using local version.")

        if fetch:
            os.makedirs(path, exist_ok=True)

            # Clone the repository
            # -c advice.detachedHead=false is for ignoring the warning about detached HEAD
            # We don't need git history, so we use --depth=1
            # The --progress option is required to get the continuous progress output
            cmd = f"git clone -c advice.detachedHead=false --depth=1 --branch {branch} {url} {name} --progress"
            retry_count = 2
            tries = 0

            while tries < retry_count:
                with subprocess.Popen(
                    cmd,
                    cwd=fetched_dir,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                ) as p:

                    # Capture the output of the subprocess to print the info in the pbar
                    if p.stdout is not None:
                        for line in p.stdout:
                            if task is not None:
                                task.update(pakkage=target_version.id, info=line.strip().replace("\r", ""))
                            # self._pbar_progress.update(pbar, pakkage=target_version.id, info=line.strip().replace("\r", ""))

                if PakkageConfig.from_directory(path):
                    break

                tries += 1
                if tries < retry_count:
                    logger.warning(f"Fetch of {target_version.id} failed. Retrying...")

        # Load the PakkageConfig from the fetched directory
        if PakkageConfig.from_directory(path) is None:
            raise Exception(f"Could not load PakkageConfig from {path}")

        # Set the state to fetched and the local_path
        target_version.state.install_state = PakkageInstallState.FETCHED
        target_version.local_path = path

        if task is not None:
            task.update(pakkage="Done", info="")
