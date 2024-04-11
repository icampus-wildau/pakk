from __future__ import annotations

import logging
import os
from pakk.helper.file_util import remove_dir

from pakk.modules.environments.base import EnvironmentBase
from pakk.modules.environments.linux import LinuxEnvironment
from pakk.modules.environments.parts.ros2 import EnvPartROS2
from pakk.modules.types.base import TypeBase
from pakk.modules.types.base_instruction_parser import RunInstructionParser
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.init_helper import ConfigOption, ConfigSection, InitHelperBase

logger = logging.getLogger(__name__)


class RosStartInstructionParser(RunInstructionParser):
    INSTRUCTION_NAME = ["start", "local"]
    # DEFAULT_SUBINSTRUCTION = "launch"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)
        if not isinstance(environment, EnvPartROS2):
            raise TypeError(f"Environment must be of type '{EnvPartROS2.__name__}'")
        self.ros_env: EnvPartROS2 = environment

        self.script = None

        self.local = True

    def has_cmd(self):
        return self.script is not None

    def get_cmd(self):
        local_env = f"export ROS_LOCALHOST_ONLY={1 if self.local else 0}"
        cmds = [
            self.ros_env.get_cmd_setup_ws(),
            local_env,
            self.env.get_cmd_in_environment(f"ros2 launch {self.script}")
        ]
        return " && ".join(cmds)

    def parse_start(self, instruction_content: str):
        self.script = instruction_content.strip(' "')

    def parse_local(self, instruction_content: str):
        self.local = instruction_content.strip(' "').lower() in ["true", "yes", "1"]


class TypeRos2(TypeBase):
    """
    General setup instructions.
    """

    PAKKAGE_TYPE: str = "ROS2"
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = False

    SECTION_NAME = "Type.ROS2"

    # CONFIG_REQUIREMENTS = TypeBase.CONFIG_REQUIREMENTS | {
    #     SECTION_NAME: ["dockerized"]
    # }

    INSTRUCTION_PARSER = [
        RosStartInstructionParser,
    ]

    def __init__(self, pakkage_version: PakkageConfig, env: EnvironmentBase | None = None):
        env = env or pakkage_version.get_environment(LinuxEnvironment)
        super().__init__(pakkage_version, env)

        self.install_type.is_combinable_with_children = True

    def get_ros_package_names(self) -> list[str]:
        """
        Get the names of the ROS packages for the given pakkage.

        Returns
        -------
        list[str]: The names of the ROS packages in the pakkage.
        """
        if isinstance(self.env, EnvPartROS2):
            src_dir = self.env.path_ros_ws_src
            # pakkage_dir = os.path.join(src_dir, self.pakkage_version.basename)
            pakkage_dir = os.path.join(src_dir, self.pakkage_version.id)

            search_path = os.path.join(pakkage_dir, "*").replace("\\", "/")

            cmds = [
                self.env.get_cmd_colcon_list_packages(search_path)
            ]

            result = self.run_commands(cmds, cwd=self.env.path_ros_ws)
            return [n for n in result.splitlines() if n != ""]
        else:
            raise NotImplementedError()

    def build_ros_packages(self, package_names: list[str]):
        """
        Build the ROS packages in the given pakkage version.

        Parameters
        ----------
        package_names:
            The names of the ROS packages to build.
        """

        # Is symlink really needed?
        # --symlink-install could be needed since the packages are symlinked into the workspace
        # Otherwise some "error in 'egg_base'" error can occur
        # See https://answers.ros.org/question/364060/colcon-fails-to-build-python-package-error-in-egg_base/

        if isinstance(self.env, EnvPartROS2):
            cmds = [
                self.env.get_cmd_colcon_build(package_names, symlink_install=False)
            ]

            code, _, _ = self.run_commands_with_returncode(
                cmds, cwd=self.env.path_ros_ws, print_output=True
            )

            # If the packages could not be built, try to delete the build and install directories
            if code == 2:
                logger.warning("Build failed. Trying to delete build and install directories...")
                for p in package_names:
                    for d in ["build", "install"]:
                        path = os.path.join(self.env.path_ros_ws, d, p)
                        if os.path.exists(path):
                            remove_dir(path)

                logger.warning("Trying to build again...")
                code, _, _ = self.run_commands_with_returncode(
                    cmds, cwd=self.env.path_ros_ws, print_output=True
                )

    def install(self) -> None:
        """Install a ROS pakkage."""
        logger.info(f"Installing ROS2 pakkage '{self.pakkage_version.id}'...")

        v = self.pakkage_version
        self.env: LinuxEnvironment

        # Link into pakkages_dir
        self.set_status(v.name, f"Linking {v.basename} into modules directory...")
        self.symlink_pakkage_in_pakkages_dir(v)

        # Link into ROS workspace
        self.set_status(v.name, f"Linking {v.basename} into ROS workspace...")
        # Don't use v.basename here. ROS supports atm only one version simultaneously, thus it should always be the same name
        ros_src_pakkage_path = os.path.join(self.env.path_ros_ws_src, v.id)
        self.symlink_pakkage_to(v, ros_src_pakkage_path)

        # return
        # Get ROS packages present in the pakkage
        self.set_status(v.name, f"Retrieving ROS packages in {v.basename}...")
        ros_p_names = self.get_ros_package_names()

        # Build the ROS packages
        self.set_status(v.name, f"Building ROS packages in {v.basename}...")
        out = self.build_ros_packages(ros_p_names)

    @staticmethod
    def install_multiple(types: list[TypeRos2]):
        """
        Install multiple ROS pakkages simultaneously.

        Parameters
        ----------
        types:
            The ROS pakkages to install.
        """
        if len(types) == 0:
            return
        logger.info(f"Installing ROS2 pakkages for {[t.pakkage_version.id for t in types]}...")

        ros_p_names = []

        # Link into pakkages_dir
        for t in types:
            t.set_status(t.pakkage_version.name, f"Linking {t.pakkage_version.basename} into ROS2 modules dir...")
            t.symlink_pakkage_in_pakkages_dir(t.pakkage_version)

            # Link into ROS workspace
            # Don't use v.basename here. ROS supports atm only one version simultaneously, thus it should always be the same name
            t.set_status(t.pakkage_version.name, f"Linking {t.pakkage_version.basename} into ROS workspace...")
            ros_src_pakkage_path = os.path.join(t.env.path_ros_ws_src, t.pakkage_version.id)
            t.symlink_pakkage_to(t.pakkage_version, ros_src_pakkage_path)

            # Get ROS packages present in the pakkage
            t.set_status(t.pakkage_version.name, f"Retrieving ROS package names in {t.pakkage_version.basename}...")
            ros_p_names.extend(t.get_ros_package_names())

        # Build the ROS packages
        logger.info(f"Building ROS packages for {[t.pakkage_version.id for t in types]}...")
        types[0].build_ros_packages(ros_p_names)

    def uninstall(self) -> None:
        TypeRos2.unlink_pakkage_in_pakkages_dir(self.pakkage_version)
        ros_src_pakkage_path = os.path.join(self.env.path_ros_ws_src, self.pakkage_version.id)
        TypeRos2.unlink_pakkage_from(ros_src_pakkage_path)


class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[ConfigSection]:
        from InquirerPy import inquirer
        sections: list[ConfigSection] = []
        ros_options: list[ConfigOption] = []

        launchable = inquirer.confirm("Is the ROS2 pakkage startable?", default=False).execute()

        if launchable:
            package_name = inquirer.text("Name of the launchable ROS2 pakkage:").execute()
            launch_script = inquirer.text("Which launch script:").execute()

            ros_options.append(ConfigOption("start", f"{package_name} {launch_script}"))

        sections.append(ConfigSection("ROS2", ros_options))

        return sections
