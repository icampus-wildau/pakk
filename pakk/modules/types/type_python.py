from __future__ import annotations

import logging

from extended_configparser.configuration.entries.section import ConfigSection

from pakk.config.base import TypeConfiguration
from pakk.modules.environments.base import EnvironmentBase
from pakk.modules.types.base import TypeBase
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.init_helper import InitConfigSection
from pakk.pakkage.init_helper import InitHelperBase

logger = logging.getLogger(__name__)


class PythonTypeConfiguration(TypeConfiguration):
    def __init__(self):
        super().__init__()

        self.python_section = ConfigSection("Python")
        self.package_install_location = self.python_section.Option(
            "package_install_location",
            "default",
            "Location where the python packages are installed",
            long_instruction="If 'default' use the default path for python packages, otherwise override this value with a specific path.",
            inquire=False,
            is_dir=True,
            value_getter=lambda x: x if x != "default" else None,
        )

    # @staticmethod
    def get_cmd_pip_install_package(
        self,
        path: str | None = None,
        editable=True,
        requirements_file: str | None = None,
        packages: list[str] | None = None,
    ):
        parts = ["pip install"]
        if path is not None:
            if editable:
                parts.append("-e")
            parts.append(path)

        if requirements_file is not None:
            parts.append("-r")
            parts.append(requirements_file)

        if packages is not None:
            parts.extend(packages)

        if len(parts) == 1:
            raise ValueError("No path, requirements file or packages to install")

        if self.package_install_location.value is not None:
            parts.append(f"-t {self.package_install_location.value}")

        s = " ".join(parts)
        return s


class TypePython(TypeBase):
    """
    Install and setup for python pakkages.
    """

    PAKKAGE_TYPE: str = "Python"
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = False

    def __init__(self, pakkage_version: PakkageConfig, env: EnvironmentBase):
        super().__init__(pakkage_version, env)
        self.config = PythonTypeConfiguration.get_config()

    def install_package(self, path: str, editable=True):
        path = self.env.get_path_in_environment(path)
        cmd = self.config.get_cmd_pip_install_package(path, editable)
        cmd = self.env.get_cmd_in_environment(cmd)
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
        if v.local_path is not None:
            self.install_package(v.local_path)
        else:
            # TODO: Better exception
            raise Exception("No local path to install python package")

    def uninstall(self) -> None:
        TypePython.unlink_pakkage_in_pakkages_dir(self.pakkage_version)


class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[InitConfigSection]:
        return [InitConfigSection("Python", [])]
