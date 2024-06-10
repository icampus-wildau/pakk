from __future__ import annotations

import os

from pakk.config import pakk_config
from pakk.config.pakk_config import Sections
from pakk.modules.environments.dockerbase import DockerEnvironment
from pakk.modules.environments.ros2.base import Ros2Environment
from pakk.modules.module import Module
from pakk.pakkage.core import PakkageConfig


class LocalRos2Environment(Ros2Environment):
    CONFIG_REQUIREMENTS = Ros2Environment.CONFIG_REQUIREMENTS

    def __init__(self, pakkage_version: PakkageConfig):
        super().__init__()
        self.pakkage_version = pakkage_version

    def get_path_in_environment(self, path: str) -> str:
        return super().get_path_in_environment(path)

    def get_cmd_pip_install_dependencies(self):
        """Get the command to install all python dependencies."""
        cmd = super().get_cmd_pip_install_dependencies()
        if cmd is None:
            return None
        if self.path_python_packages is not None:
            cmd += f" -t {self.path_python_packages}"
        return cmd

    def get_interactive_cmd_in_environment(self, cmd: str) -> str:
        source_cmd = self.path_ros_ws + "/install/setup.bash"
        return f'bash -c "source {source_cmd} && {cmd}"'

    def get_ros_package_names(self, pakkage_basename: str) -> list[str]:
        """
        Get the names of the ROS packages for the given pakkage.
        Parameters
        ----------
        pakkage_basename:
            The basename of the pakkage (as path.join(ros_ws_src_path, pakkage_basename) should be the location of the pakkage).

        Returns
        -------
        list[str]: The names of the ROS packages in the pakkage.
        """

        src_dir = self.path_ros_ws_src
        pakkage_dir = os.path.join(src_dir, pakkage_basename)

        search_path = os.path.join(pakkage_dir, "*").replace("\\", "/")

        cmds = [self.get_cmd_colcon_list_packages(search_path)]

        result = Module.run_commands(cmds)
        return [n for n in result.splitlines() if n != ""]

    def build_ros_packages(self, pakkage_version: PakkageConfig, package_names: list[str]):
        """
        Build the ROS packages in the given pakkage.

        Parameters
        ----------
        package_names:
            The names of the ROS packages to build.

        """

        # --symlink-install is needed since the packages are symlinked into the workspace
        # Otherwise some "error in 'egg_base'" error occurs
        # See https://answers.ros.org/question/364060/colcon-fails-to-build-python-package-error-in-egg_base/
        cmds = [f"cd {self.path_ros_ws}", self.get_cmd_colcon_build(package_names, symlink_install=False)]

        def callback(line):
            self.set_status(pakkage_version.name, line)

        # TODO: switch to dynamic output
        result = Module.run_commands_with_output(cmds, callback=callback, catch_dynamic_output=False)
        return result

    def _get_source_cmd(self):
        return f"source ${self.path_ros_ws}/src/install/setup.bash"
