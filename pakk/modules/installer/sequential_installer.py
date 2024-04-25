from __future__ import annotations

import logging
from multiprocessing.pool import ThreadPool
from typing import Callable

from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn, BarColumn, TimeRemainingColumn, \
    MofNCompleteColumn

from pakk.pakk.args.install_config import InstallConfig
from pakk.config.pakk_config import Sections as CfgSections
from pakk.logger import Logger, ProgressTasks
from pakk.modules.dependency_tree.tree import DependencyTree
from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage, PakkageInstallState, PakkageConfig

logger = logging.getLogger(__name__)


class InstallerSequential(Module):
    """
    Installer that install all pakkages sequentially.
    """

    SECTION_NAME = "Installer"

    CONFIG_REQUIREMENTS = {
        CfgSections.SUBDIRS: ["fetched_dir", "all_pakkges_dir"]
    }

    def __init__(self, pakkages: dict[str, Pakkage], dependency_tree: DependencyTree):
        """
        Initialize the installer.
        The dependency tree is used to determine the order in which the pakkages are installed.

        Parameters
        ----------
        pakkages: dict[str, Pakkage]
            The pakkages to install.
        dependency_tree: DependencyTree
            The dependency tree of the pakkages from the Resolver Step.
        """
        super().__init__()

        self.pakkages = pakkages
        self.deptree = dependency_tree

        self.fetched_dir: str = self.config.get_abs_path("fetched_dir") # type: ignore
        self.all_pakkges_dir: str = self.config.get_abs_path("all_pakkges_dir") # type: ignore

        self.status_callback: Callable[[str], None] | None = None
        self.tasks = None

        self.install_config = InstallConfig.get()

        self.pakkages_to_uninstall: list[Pakkage] = []
        self.pakkages_to_install: list[Pakkage] = []

        self._init_package_assignments()

    def _init_package_assignments(self):
        # Check if pakkages needs to be installed, updated or uninstalled
        pakkages_to_install = []
        pakkages_to_uninstall = []

        for pakkage in self.pakkages.values():
            if pakkage.versions.is_update_candidate():
                pakkages_to_install.append(pakkage)

                if pakkage.versions.target is None:
                    raise ValueError(f"Target version of {pakkage.name} is None")

                if pakkage.versions.installed is None:
                    logger.info(f"Will install {pakkage.name} ({pakkage.versions.target.version})")
                else:
                    logger.info(f"Will update {pakkage.name} ({pakkage.versions.installed.version} -> {pakkage.versions.target.version})")
                    pakkages_to_uninstall.append(pakkage)
            elif pakkage.versions.target is not None:
                if pakkage.versions.reinstall and pakkage.versions.installed is not None:
                    logger.info(f"Will reinstall {pakkage.name} ({pakkage.versions.installed.version})")
                    pakkages_to_uninstall.append(pakkage)
                    pakkages_to_install.append(pakkage)
                else:
                    if pakkage.versions.installed is None:
                        raise ValueError(f"Installed version of {pakkage.name} is None")
                    logger.debug(f"Skipping {pakkage.name} as it is already up to date ({pakkage.versions.installed.version})")

        self.pakkages_to_uninstall: list[Pakkage] = pakkages_to_uninstall
        self.pakkages_to_install: list[Pakkage] = pakkages_to_install

    def _install_pakkage(self, pakkage: Pakkage) -> Pakkage:

        logger.info(f"Start installation of '{pakkage.name}'...")
        v = pakkage.versions.target
        if v is None:
            raise ValueError(f"Target version of {pakkage.name} is None")

        # Move to installed dir
        new_dir = self.all_pakkges_dir
        logger.debug(f"Moving {v.name} to {new_dir}")
        v.move_to(new_dir)

        def callback(pakkage_name, info):
            logger.info(f"[cyan]{pakkage_name}[/cyan]: {info}")

        for pakk_type in v.pakk_types:
            logger.info(f" -> Installing {v.name} with [blue]{pakk_type.__class__.__name__}[/blue]")
            pakk_type.status_callback = callback
            pakk_type.install()

        pakkage.versions.installed = v
        pakkage.versions.installed.save_state()

        return pakkage

    def uninstall(self):
        if len(self.pakkages_to_uninstall) > 0:
            Module.print_rule(f"Uninstalling pakkages")
            logger.info(f"Uninstalling {len(self.pakkages_to_uninstall)} packages...")

            for pakkage in self.pakkages_to_uninstall:
                v: PakkageConfig = pakkage.versions.installed
                logger.info(f"Uninstalling {v.name} ({v.version})")
                for pakk_type in v.pakk_types:
                    pakk_type.uninstall()

                v.state.install_state = PakkageInstallState.UNINSTALLED
                v.save_state()

                # Move to fetched dir
                if not self.install_config.refetch:
                    new_dir = self.fetched_dir
                    v.move_to(new_dir)
                else:
                    v.delete_directory()

                pakkage.versions.installed = None

    def install(self) -> dict[str, Pakkage]:
        """Install all the packages with the configured setup and installation modules."""

        if len(self.pakkages_to_install) > 0:
            Module.print_rule(f"Installing pakkages")
            logger.info(f"Installing {len(self.pakkages_to_install)} packages...")

            package_names_to_install = set([p.id for p in self.pakkages_to_install])
            name_generations = self.deptree.get_topological_generations(reversed=True)

            pakkage_generations = []

            for name_generation in name_generations:
                pakkage_generation = []
                for name in name_generation:
                    if name in package_names_to_install:
                        pakkage_generation.append(name)
                pakkage_generations.append(pakkage_generation)

            for pakkage_generation in pakkage_generations:
                pakkages = [self.pakkages[name] for name in pakkage_generation]

                for pakkage in pakkages:
                    # Logger.get_console().rule
                    self._install_pakkage(pakkage)
                    logger.info(f"Finished installation of {pakkage.name}.")
                    Logger.get_console().print("")

        elif len(self.pakkages_to_install) == 0:
            logger.info(f"Everything up to date, no packages to install :)")

        return self.pakkages
