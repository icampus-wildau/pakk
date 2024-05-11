from __future__ import annotations

import os

from pakk.config.pakk_config import Sections
from pakk.modules.environments.base import Environment
from pakk.modules.environments.python.python_local import PythonEnvironment
from pakk.pakkage.core import PakkageConfig


class Ros2Environment(Environment):
    SECTION_NAME = "Env.ROS2"

    CONFIG_REQUIREMENTS = {
        Sections.SUBDIRS: ["all_pakkges_dir"],
        SECTION_NAME: [
            "ws_dir",
        ],
        PythonEnvironment.SECTION_NAME: [
            "python_package_path",
        ],
    }

    def __init__(self):
        super().__init__()

        self.path_ros_ws = self.config.get_abs_path("ws_dir", Ros2Environment.SECTION_NAME)
        self.path_ros_ws_src = os.path.join(self.path_ros_ws, "src")
        self.path_python_packages = self.config.get_abs_path(
            "python_package_path", PythonEnvironment.SECTION_NAME, none_if_val_is="None"
        )

    def get_path_in_environment(self, path: str) -> str:
        """
        Get the path in the environment for the given local path.
        By default, the path is returned unchanged.

        Parameters
        ----------
        path:
            The path to get the path in the environment for.
        """
        return path

    @staticmethod
    def get_cmd_colcon_list_packages(search_path: str):
        """Get the colcon command to list all packages in the given path."""
        return f"colcon list --names-only --paths {search_path}"

    @staticmethod
    def get_cmd_colcon_build(package_names: list[str], symlink_install: bool = False):
        """Get the colcon command to build the given packages."""
        return (
            f'colcon build {"--symlink-install " if symlink_install else ""}--packages-select {" ".join(package_names)}'
        )

    def get_ros_package_names(self, pakkage_version: PakkageConfig) -> list[str]:
        """
        Get the names of the ROS packages for the given pakkage.
        Parameters
        ----------
        pakkage_version:
            The pakkage version to get the ROS2 package names for.

        Returns
        -------
        list[str]: The names of the ROS packages in the pakkage.
        """
        raise NotImplementedError()

    def build_ros_packages(self, pakkage_version: PakkageConfig, package_names: list[str]):
        """
        Build the ROS packages in the given pakkage version.

        Parameters
        ----------
        pakkage_version:
            The pakkage version the ros packages are built for.
        package_names:
            The names of the ROS packages to build.
        """
        raise NotImplementedError()
