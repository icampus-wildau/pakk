from __future__ import annotations

import logging

from pakk.modules.environments.base import EnvironmentBase
from pakk.modules.environments.linux import LinuxEnvironment
from pakk.modules.environments.parts.python import EnvPartPython
from pakk.modules.types.base import TypeBase
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.init_helper import ConfigOption, ConfigSection, InitHelperBase

logger = logging.getLogger(__name__)


class TypePython(TypeBase):
    """
    Install and setup for python pakkages.
    """

    PAKKAGE_TYPE: str = "Python"
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = False

    def __init__(self, pakkage_version: PakkageConfig, env: EnvironmentBase | None = None):
        env = env or pakkage_version.get_environment(LinuxEnvironment)
        super().__init__(pakkage_version, env)

    def install_package(self, path: str, editable=True):
        path = self.env.get_path_in_environment(path)
        if isinstance(self.env, EnvPartPython):
            cmd = self.env.get_cmd_pip_install_package(path, editable)
            # TODO: Adapt output callback
            self.run_commands_with_output(cmd)

    def install(self) -> None:
        """Install a ROS pakkage."""
        logger.info(f"Installing Python pakkage '{self.pakkage_version.id}'...")

        v = self.pakkage_version

        # Link into pakkages_dir
        self.set_status(v.name, f"Linking {v.basename} into modules directory...")
        self.symlink_pakkage_in_pakkages_dir(v)

        # Install the Python packages
        self.set_status(v.name, f"Installing python package in {v.basename}...")
        self.install_package(v.local_path)

    def uninstall(self) -> None:
        TypePython.unlink_pakkage_in_pakkages_dir(self.pakkage_version)

class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[ConfigSection]:
        return [ConfigSection("Python", [])]
