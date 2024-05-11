from __future__ import annotations

import os

from pakk.modules.environments.dockerbase import DockerEnvironment
from pakk.modules.environments.ros2.base import Ros2Environment
from pakk.modules.module import Module
from pakk.pakkage.core import PakkageConfig


class DefaultRos2DockerEnvironment(DockerEnvironment):
    IMAGE_NAME = "pakk_ros2"

    ENV_PYTHONPATH = "PYTHONPATH"
    ENV_MOUNTED_WS_DIR = "MNT_WS_DIR"
    ENV_MOUNTED_PYTHON_PACKAGE_DIR = "MNT_PYTHON_PACKAGE_DIR"

    ENV_VALUES = {
        ENV_MOUNTED_WS_DIR: "/ws",
        ENV_MOUNTED_PYTHON_PACKAGE_DIR: "/python-packages",
    }

    @classmethod
    def ws_path(cls) -> str:
        return cls.ENV_VALUES[cls.ENV_MOUNTED_WS_DIR]

    @classmethod
    def ws_src_path(cls) -> str:
        return os.path.join(cls.ws_path(), "src")

    @classmethod
    def python_package_path(cls) -> str:
        return cls.ENV_VALUES[cls.ENV_MOUNTED_PYTHON_PACKAGE_DIR]

    def __init__(self, image_name: str = None):
        super().__init__(image_name or self.IMAGE_NAME)

        # TODO: Adapt for arm64 devices
        self.dockerfile.base_image = "ros:humble-ros-base-jammy"

        # Install and update pip and setuptools
        self.dockerfile.add_lines(
            *[
                "RUN apt update && apt install -y python3-pip",
                "RUN pip install -U pip",
                "RUN pip install setuptools==58.2.0",
            ]
        )

        # Setup ENVs
        self.dockerfile.add_lines(
            *[
                f"ENV {self.ENV_PYTHONPATH}={self.python_package_path()}:${self.ENV_PYTHONPATH}",
                f"ENV {self.ENV_MOUNTED_WS_DIR}={self.ws_path()}",
                f"ENV {self.ENV_MOUNTED_PYTHON_PACKAGE_DIR}={self.python_package_path()}",
            ]
        )


class SharedRos2DockerEnvironment(DockerEnvironment, Ros2Environment):  # Environment

    CONFIG_REQUIREMENTS = DockerEnvironment.CONFIG_REQUIREMENTS | Ros2Environment.CONFIG_REQUIREMENTS

    def __init__(self, pakkage_version: PakkageConfig):
        super().__init__(f"pakk_ros2_{pakkage_version.basename}")

        base_cls = DefaultRos2DockerEnvironment
        base_cls.require_image()
        self.dockerfile.base_image = base_cls.IMAGE_NAME

        # Mount ws dir
        self.mounts[base_cls.ws_path()] = self.path_ros_ws
        # Mount python package dir
        self.mounts[base_cls.python_package_path()] = self.path_python_packages

    def get_path_in_environment(self, path: str) -> str:
        return self.get_mnt_destination_path(path)

    def get_cmd_in_environment(self, cmd: str) -> str:
        return self.get_docker_command(cmd)

    def setup(self):
        # Add apt install instructions to the image and build it
        if len(self.apt_dependencies) > 0:
            self.dockerfile.add_lines(*[f"RUN apt update && apt install -y {' '.join(self.apt_dependencies)}"])
        self.build_image()

        # TODO: Only install packages that are not already installed in the mounted dir
        # Install python packages inside the container with the python package dir as target
        cmds = []
        cmds.append(self.get_cmd_pip_install_dependencies())

        # TODO: Add this to the dockerfile
        cmds.append(self.get_cmd_setup_scripts())

        cmds = [c for c in cmds if c is not None]

        for cmd in cmds:
            c = self.get_cmd_in_environment(cmd)
            self.run_commands_with_output(c)

    def get_cmd_pip_install_dependencies(self):
        """Get the command to install all python dependencies."""
        cmd = super().get_cmd_pip_install_dependencies()
        if cmd is not None:
            cmd += f" -t ${DefaultRos2DockerEnvironment.ENV_MOUNTED_PYTHON_PACKAGE_DIR}"
        return cmd

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

        src_dir = DefaultRos2DockerEnvironment.ws_src_path()
        pakkage_dir = os.path.join(src_dir, pakkage_basename)

        search_path = os.path.join(pakkage_dir, "*").replace("\\", "/")

        cmds = [self.get_cmd_colcon_list_packages(search_path)]

        cmd = self.get_docker_command(cmds)
        result = Module.run_commands(cmd)
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
        cmds = [
            f"cd {DefaultRos2DockerEnvironment.ws_path()}",
            self.get_cmd_colcon_build(package_names, symlink_install=False),
        ]
        cmd = self.get_docker_command(cmds)

        def callback(line):
            self.set_status(pakkage_version.name, line)

        # TODO: switch to dynamic output
        result = Module.run_commands_with_output(cmd, callback=callback, catch_dynamic_output=False)
        return result

    def _get_source_cmd(self):
        return f"source ${DefaultRos2DockerEnvironment.ENV_MOUNTED_WS_DIR}/src/install/setup.bash"

    def get_docker_command(self, commands: str | list[str], include_source_cmd=False):
        if isinstance(commands, str):
            commands = [commands]
        if include_source_cmd:
            commands = [self._get_source_cmd()] + commands
        return super().get_docker_command(commands)

    def get_interactive_docker_command(self, commands: str | list[str] = None):
        if commands is None:
            commands = ["bash"]
        elif isinstance(commands, str):
            commands = [commands]

        commands = [self._get_source_cmd()] + commands
        end_cmd = " && ".join(commands)

        cmd = super().get_interactive_docker_command()

        return cmd + f' bash -c "{end_cmd}"'
