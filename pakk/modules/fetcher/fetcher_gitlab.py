from __future__ import annotations

import logging
import os
import subprocess
from multiprocessing.pool import ThreadPool

from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn, BarColumn, TimeRemainingColumn, \
    MofNCompleteColumn

import pakk.config.pakk_config as cfg
from pakk.pakk.args.install_config import InstallConfig
from pakk.helper.file_util import remove_dir
from pakk.helper.gitlab_util import get_gitlab_http_with_token
from pakk.logger import console, Logger
from pakk.modules.discoverer.discoverer_gitlab import ATTR_GITLAB_HTTP_SOURCE, ATTR_GITLAB_SOURCE_TAG
from pakk.modules.fetcher.base import Fetcher
from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage, PakkageInstallState, PakkageConfig

logger = logging.getLogger(__name__)


class PakkageContainer:
    def __init__(self, pakkage: Pakkage, pid: int):
        self.pakkage = pakkage
        self.pid = pid


class FetcherGitlab(Fetcher):
    CONFIG_REQUIREMENTS = {
        cfg.Sections.GITLAB_CONNECTION: ["private_token"],
        cfg.Sections.SUBDIRS: ["fetched_dir"],
        cfg.Sections.FETCHER_GITLAB: ["num_workers"]
    }

    def __init__(self, pakkages: dict[str, Pakkage]):
        super().__init__(pakkages)

        self.config = cfg.get()
        self.install_config = InstallConfig.get()

        self.fetched_dir: str = self.config.get_abs_path('fetched_dir', cfg.Sections.SUBDIRS) # type: ignore

        # Progress object for pbars
        self.pbar_progress = None
        # Pbar tasks for multiple workers
        self.pbars = []
        # Array storing free pbar indices, workers select the next free index
        self.free_pbars = []

    def checkout_target_version(self, pakkage: Pakkage) -> Pakkage | None:
        if not pakkage.versions.is_update_candidate():
            return None

        # Get the next free pbar
        pbar_index = self.free_pbars.index(True)
        # Acquire the pbar
        self.free_pbars[pbar_index] = False
        # Get the related pbar
        pbar = self.pbars[pbar_index]

        target_version = pakkage.versions.target
        if target_version is None:
            raise Exception(f"Target version of {pakkage.name} is None.")

        if ATTR_GITLAB_HTTP_SOURCE in target_version.attributes and ATTR_GITLAB_SOURCE_TAG in target_version.attributes:
            url = target_version.attributes[ATTR_GITLAB_HTTP_SOURCE]
            url_with_token = get_gitlab_http_with_token(url)
            tag = target_version.attributes[ATTR_GITLAB_SOURCE_TAG]

            name = target_version.basename
            path = os.path.join(self.fetched_dir, name)

            fetch = True
            if os.path.exists(path):
                if self.install_config.refetch or self.install_config.clear_cache:
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
                cmd = f"git clone -c advice.detachedHead=false --depth=1 --branch {tag} {url_with_token} {name} --progress"
                retry_count = 2
                tries = 0

                while tries < retry_count:
                    with subprocess.Popen(
                            cmd,
                            cwd=self.fetched_dir,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=1,
                            universal_newlines=True,
                    ) as p:

                        # Capture the output of the subprocess to print the info in the pbar
                        for line in p.stdout:
                            self.pbar_progress.update(pbar, pakkage=pakkage.id, info=line.strip().replace("\r", ""))

                    if PakkageConfig.from_directory(path):
                        break
                    
                    tries += 1
                    if tries < retry_count:
                        logger.warning(f"Fetch of {pakkage.id} failed. Retrying...")

            # Load the PakkageConfig from the fetched directory
            target_version = PakkageConfig.from_directory(path)
            if target_version is None:
                raise Exception(f"Could not load PakkageConfig from {path}")

            # If there was an installed version, copy the state
            target_version.state.copy_from(pakkage.versions.installed)
            target_version.state.install_state = PakkageInstallState.FETCHED
            target_version.local_path = path

            # Create the .pakk directory and store the state
            target_version.save_state(path)
            pakkage.versions.target = target_version

        self.free_pbars[pbar_index] = True
        self.pbar_progress.update(pbar, pakkage="Done", info="")
        return pakkage

    def fetch(self) -> dict[str, Pakkage]:
        Module.print_rule(f"Fetching pakkages")

        num_workers = int(self.config.get(cfg.Sections.FETCHER_GITLAB, "num_workers"))

        packages_to_fetch = [pakkage for pakkage in self.pakkages.values() if pakkage.versions.is_update_candidate()]

        # try:
        if len(packages_to_fetch) == 0:
            logger.info("No pakkages to fetch.")
            return self.pakkages

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                # TaskProgressColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                TimeElapsedColumn(),
                TextColumn("{task.fields[pakkage]}"),
                TextColumn("{task.fields[info]}"),
                transient=True,
                console=console
        ) as progress:
            self.pbar_progress = progress

            pbar = progress.add_task("[blue]Fetching Total:", total=len(packages_to_fetch), pakkage="", info="")

            if num_workers > 1:
                num_workers = min(num_workers, len(packages_to_fetch))
                for i in range(num_workers):
                    self.pbars.append(progress.add_task(f"[cyan]Worker{i + 1}:", total=None, pakkage="", info=""))
                    self.free_pbars.append(True)

                # Don't use multiprocessing.Pool since it will spawn new processes and not threads,
                # thus the data will not be shared.
                # See:
                # https://stackoverflow.com/questions/3033952/threading-pool-similar-to-the-multiprocessing-pool
                # https://stackoverflow.com/questions/52486811/how-to-properly-reference-to-instances-of-a-class-in-multiprocessing-pool-map
                # https://towardsdatascience.com/demystifying-python-multiprocessing-and-multithreading-9b62f9875a27
                with ThreadPool(num_workers) as pool:
                    for res in pool.imap_unordered(self.checkout_target_version, packages_to_fetch):
                        progress.update(pbar, advance=1, info="")
                        if res is not None:
                            logger.info(f"Fetched {res.name}.")
                pool.join()
            else:
                self.pbars.append(progress.add_task(f"[cyan]Worker{1}:", total=None, pakkage="", info=""))
                self.free_pbars.append(True)

                for pakkage in packages_to_fetch:
                    self.checkout_target_version(pakkage)
                    progress.update(pbar, advance=1, info=f"Fetching: {pakkage.name}")
                    logger.info(f"Fetched {pakkage.name}.")

        logger.info("Done fetching")
        return self.pakkages
