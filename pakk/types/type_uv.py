from __future__ import annotations

import logging
import os

from extended_configparser.configuration.entries.section import ConfigSection

from pakk.config.base import TypeConfiguration
from pakk.environments.base import Environment
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.init_helper import InitConfigSection
from pakk.pakkage.init_helper import InitHelperBase
from pakk.types.base import TypeBase

logger = logging.getLogger(__name__)


class UVTypeConfiguration(TypeConfiguration):
    def __init__(self):
        super().__init__()

        self.uv_section = ConfigSection("UV")
        # self.dev_dependencies = self.uv_section.Option(
        #     "dev_dependencies",
        #     "true",
        #     "Whether to install development dependencies",
        #     long_instruction="If 'true', install both production and development dependencies. If 'false', only install production dependencies.",
        #     inquire=False,
        #     value_getter=lambda x: x.lower() == "true",
        # )

    def get_cmd_uv_sync_package(
        self,
        path: str | None = None,
    ):
        uv = Environment.get_uv()
        parts = [f"{uv} sync"]
        
        # if dev_dependencies is None:
        #     dev_dependencies = self.dev_dependencies.value
            
        # if not dev_dependencies:
        #     parts.append("--no-dev")
            
        if path is not None:
            parts.append("--project")
            parts.append(path)

        # if self.package_install_location.value is not None:
        #     parts.append(f"--target {self.package_install_location.value}")

        s = " ".join(parts)
        return s


class TypeUV(TypeBase):
    """
    Install and setup for python pakkages using UV.
    
    This type is similar to the Python type but uses UV (uv sync) instead of pip for package management.
    UV provides faster dependency resolution and installation compared to pip.
    
    Key differences from Python type:
    - Uses 'uv sync' instead of 'pip install'
    - Supports '--no-dev' flag to exclude development dependencies
    - Uses '--project' flag to specify the project directory
    - Automatically detects pyproject.toml and uv.lock files
    """

    PAKKAGE_TYPE = "UV"
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = False

    def __init__(self, pakkage_version: PakkageConfig, env: Environment):
        super().__init__(pakkage_version, env)
        self.config = UVTypeConfiguration.get_config()

    def install_package(self, path: str):
        path = self.env.get_path_in_environment(path)
        cmd = self.config.get_cmd_uv_sync_package(path)
        cmd = self.env.get_cmd_in_environment(cmd)
        self.run_commands_with_output(cmd)

    def install(self) -> None:
        """Install a Python pakkage using UV."""
        logger.info(f"Installing UV pakkage '{self.pakkage_version.id}'...")

        v = self.pakkage_version

        # Link into pakkages_dir
        self.set_status(v.name, f"Linking {v.basename} into modules directory...")
        self.symlink_pakkage_in_pakkages_dir(v)

        # Install the Python packages using UV
        self.set_status(v.name, f"Installing python package in {v.basename} using UV...")
        if v.local_path is not None:
            self.install_package(v.local_path)
        else:
            # TODO: Better exception
            raise Exception("No local path to install python package")

    def uninstall(self) -> None:
        TypeUV.unlink_pakkage_in_pakkages_dir(self.pakkage_version)


class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[InitConfigSection]:
        return [InitConfigSection("UV", [])]
    
    @staticmethod
    def is_suitable_for_directory(directory_path: str) -> bool:
        """Check if this directory contains a Python project suitable for UV."""
        uv_indicators = [
            "pyproject.toml",  # Primary UV indicator
            "uv.lock",         # UV lock file
        ]
        
        # Check for UV-specific indicators first
        if InitHelperBase._search_indicators(directory_path, uv_indicators, max_depth=2):
            return True
                
        # Check for .py files in the root directory, but be more specific
        try:
            py_files = [f for f in os.listdir(directory_path) if f.endswith('.py')]
            if len(py_files) >= 2:  # Need at least 2 Python files to be considered a Python project
                return True
        except (OSError, PermissionError):
            pass
            
        return False 