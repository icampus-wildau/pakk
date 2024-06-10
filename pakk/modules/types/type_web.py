from __future__ import annotations

import logging
import os

from extended_configparser.configuration.entries.section import ConfigSection
from extended_configparser.parser import ExtendedConfigParser

from pakk.config.base import TypeConfiguration
from pakk.modules.environments.base import EnvironmentBase
from pakk.modules.environments.linux import LinuxEnvironment
from pakk.modules.types.base import TypeBase
from pakk.modules.types.base_instruction_parser import InstructionParser
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.init_helper import InitConfigOption
from pakk.pakkage.init_helper import InitConfigSection
from pakk.pakkage.init_helper import InitHelperBase
from pakk.setup.base import SetupBase

logger = logging.getLogger(__name__)


class WebTypeConfiguration(TypeConfiguration):
    def __init__(self):
        super().__init__()

        self.python_section = ConfigSection("Web")
        self.location_definition_directory = self.python_section.Option(
            "location_definition_directory",
            r"${Pakk.Subdirs:environment_dir}/nginx/locations",
            "Location where the nginx location files are stored",
            inquire=False,
            is_dir=True,
        )


class StaticRootParser(InstructionParser):
    INSTRUCTION_NAME = "static_root"
    DEFAULT_SUBINSTRUCTION = "set"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)

        self.static_root: str | None = None

    def get_default_for_build_dir(self, build_dir: str):
        return os.path.join(build_dir, "dist")

    def has_cmd(self):
        return self.static_root is not None

    def parse_set(self, instruction_content: str):
        self.static_root = instruction_content.strip(' "')


class PublicPathParser(InstructionParser):
    INSTRUCTION_NAME = "public_path"
    DEFAULT_SUBINSTRUCTION = "set"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)

        self.public_path: str | None = None

    def has_cmd(self):
        return self.public_path is not None

    def parse_set(self, instruction_content: str):
        self.public_path = instruction_content.strip(' "')


class BuildParser(InstructionParser):
    INSTRUCTION_NAME = ["build", "build_dir", "public_path_env_var", "public_path_build_option"]

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)

        self.build_system: str | None = None
        self.install_cmd: str | None = None
        self.build_cmd: str | None = None
        self.build_dir: str | None = None

        self.public_path_env_var: str | None = None
        self.public_path_build_option: str | None = None
        self.public_path: str | None = None

        self.build_options: dict[str, str] = {}
        self.build_envs: dict[str, str] = {}

    def has_cmd(self):
        return self.build_system is not None

    def get_cmd(self):

        if self.public_path is not None:
            if self.public_path_env_var is not None:
                self.build_envs[self.public_path_env_var] = self.public_path
            if self.public_path_build_option is not None:
                self.build_options[self.public_path_build_option] = self.public_path

        cmds = [
            f"cd {self.build_dir}" if self.build_dir is not None else None,
            self.get_cmd_env_vars(self.build_envs) if len(self.build_envs) > 0 else None,
            self.install_cmd,
            (
                (self.build_cmd + " " + " ".join([f"{k} {v}" for k, v in self.build_options.items()]))
                if self.build_cmd is not None
                else None
            ),
        ]
        return " && ".join([c for c in cmds if c is not None])

    def parse_build(self, instruction_content: str):
        self.build_system = instruction_content.strip(' "')
        if self.build_system == "yarn":
            self.install_cmd = "yarn"
            self.build_cmd = "yarn build"
        elif self.build_system == "npm":
            self.install_cmd = "npm install"
            self.build_cmd = "npm run build"
        else:
            raise ValueError(f"Unknown build system '{self.build_system}'.")

    def parse_build_dir(self, instruction_content: str):
        self.build_dir = instruction_content.strip(' "')

    def parse_public_path_env_var(self, instruction_content: str):
        self.public_path_env_var = instruction_content.strip(' "')

    def parse_public_path_build_option(self, instruction_content: str):
        self.public_path_build_option = instruction_content.strip(' "')


class TypeWeb(TypeBase):
    """
    Type for web apps, static and reverse proxy.
    """

    PAKKAGE_TYPE: str = "Web"
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = False

    SECTION_NAME = "Type.Web"

    # CONFIG_REQUIREMENTS = TypeBase.CONFIG_REQUIREMENTS | {
    #     SECTION_NAME: ["dockerized"]
    # }

    INSTRUCTION_PARSER = [
        StaticRootParser,
        PublicPathParser,
        BuildParser,
    ]

    def __init__(self, pakkage_version: PakkageConfig, env: EnvironmentBase):
        super().__init__(pakkage_version, env)

        self.config = WebTypeConfiguration().get_config()

        self.install_type.is_combinable_with_children = False

        self.dir_locations = self.config.location_definition_directory.value
        self.pakkage_locations_path = os.path.join(self.dir_locations, f"{pakkage_version.basename}.conf")

        v = self.pakkage_version
        self.build_parser = self.get_instruction_parser_by_cls(BuildParser)
        self.public_path = self.get_instruction_parser_by_cls(PublicPathParser).public_path or v.id
        # Remove trailing slash
        if self.public_path.endswith("/"):
            self.public_path = self.public_path[:-1]

        self.build_parser.public_path = self.public_path

        # TODO: Handle if no build_dir is set
        self.dist_dir_parser = self.get_instruction_parser_by_cls(StaticRootParser)
        self.dist_dir = self.dist_dir_parser.static_root or self.dist_dir_parser.get_default_for_build_dir(
            self.build_parser.build_dir
        )

        if v.local_path is None:
            raise ValueError("Local path is not set.")

        self.abs_dist_dir = os.path.join(v.local_path, self.dist_dir)

    def get_location_entry(self, root: str, prefix: str, index: str = "index.html"):

        if prefix.endswith("/"):
            prefix = prefix[:-1]

        s = f"""
location {prefix} {{
    alias {root};
    index {index};
    try_files $uri $uri/ =404;
}}
"""

        return s

    def install(self) -> None:
        """Install a Web pakkage."""
        logger.info(f"Installing Web pakkage '{self.pakkage_version.id}'...")

        v = self.pakkage_version
        self.env: LinuxEnvironment

        # build_dir = self.get_instruction_parser_by_cls(BuildDirParser).build_dir
        # install_cmd = self.get_instruction_parser_by_cls(BuildParser).install_cmd
        # build_cmd = self.get_instruction_parser_by_cls(BuildParser).build_cmd
        # logger.info(f"Build command: {build_cmd}")

        logger.info(f"Static root: {self.dist_dir}")
        logger.info(f"Public path: {self.public_path}")

        if self.build_parser.has_cmd():
            # public_path_string = f'\\"{self.public_path}\\"'
            public_path_string = f"{self.public_path}"
            env_var_cmd = self.build_parser.get_cmd_env_vars(
                {
                    "BASE": public_path_string,
                    "BASE_URL": public_path_string,
                    "PUBLIC_URL": public_path_string,
                    "PUBLIC_PATH": public_path_string,
                }
            )

            cmd = env_var_cmd + " && " + self.build_parser.get_cmd()
            logger.info(f"Installing and building web app: '{cmd}'")
            self.run_commands([cmd], cwd=v.local_path, print_output=True)

        # Link into pakkages_dir
        self.symlink_pakkage_in_pakkages_dir(v)

        logger.info(f"Setup nginx location @ '{self.abs_dist_dir}")

        # Check if there are old nginx location files, that were not removed successfully
        # If so, remove them
        for f in os.listdir(self.dir_locations):
            if f.startswith(f"{v.id}@") and f.endswith(".conf"):
                logger.info(f"Removing old nginx location file @ '{os.path.join(self.dir_locations, f)}'")
                os.remove(os.path.join(self.dir_locations, f))

        location_entry = self.get_location_entry(self.abs_dist_dir, self.public_path)
        with open(self.pakkage_locations_path, "w") as f:
            f.write(location_entry)

        self.reload_nginx()

        # Link into Nginx locations root
        # self.set_status(v.name, f"Linking {dist_dir} into Nginx locations root...")
        # path_locations = self.env.path_locations
        # pakkage_locations_path = os.path.join(path_locations, v.basename)
        # self.symlink_pakkage_to(v, pakkage_locations_path)

        # raise NotImplementedError()

    def reload_nginx(self):
        # Test if nginx config is ok
        cmd = "sudo nginx -t"
        if self.run_commands_with_returncode([cmd], cwd=self.pakkage_version.local_path, print_output=True)[0] != 0:
            raise Exception("Nginx config is not ok.")

        # Reload nginx config
        cmd = "sudo nginx -s reload"
        if self.run_commands_with_returncode([cmd], cwd=self.pakkage_version.local_path, print_output=True)[0] != 0:
            raise Exception("Nginx config could not be reloaded.")

    def uninstall(self) -> None:
        TypeWeb.unlink_pakkage_in_pakkages_dir(self.pakkage_version)

        # Remove nginx location file from self.pakkage_locations_path
        if os.path.exists(self.pakkage_locations_path):
            logger.info(f"Removing nginx location file @ '{self.pakkage_locations_path}'")
            os.remove(self.pakkage_locations_path)

        self.reload_nginx()

    # @staticmethod
    # def install_multiple(types: list[TypeRos2]):
    #     """
    #     Install multiple ROS pakkages simultaneously.

    #     Parameters
    #     ----------
    #     types:
    #         The ROS pakkages to install.
    #     """
    #     if len(types) == 0:
    #         return
    #     logger.info(f"Installing ROS2 pakkages for {[t.pakkage_version.id for t in types]}...")

    #     ros_p_names = []

    #     # Link into pakkages_dir
    #     for t in types:
    #         t.set_status(t.pakkage_version.name, f"Linking {t.pakkage_version.basename} into ROS2 modules dir...")
    #         t.symlink_pakkage_in_pakkages_dir(t.pakkage_version)

    #         # Link into ROS workspace
    #         # Don't use v.basename here. ROS supports atm only one version simultaneously, thus it should always be the same name
    #         t.set_status(t.pakkage_version.name, f"Linking {t.pakkage_version.basename} into ROS workspace...")
    #         ros_src_pakkage_path = os.path.join(t.env.path_ros_ws_src, t.pakkage_version.id)
    #         t.symlink_pakkage_to(t.pakkage_version, ros_src_pakkage_path)

    #         # Get ROS packages present in the pakkage
    #         t.set_status(t.pakkage_version.name, f"Retrieving ROS package names in {t.pakkage_version.basename}...")
    #         ros_p_names.extend(t.get_ros_package_names())

    #     # Build the ROS packages
    #     logger.info(f"Building ROS packages for {[t.pakkage_version.id for t in types]}...")
    #     types[0].build_ros_packages(ros_p_names)

    # def uninstall(self) -> None:
    #     TypeRos2.unlink_pakkage_in_pakkages_dir(self.pakkage_version)
    #     ros_src_pakkage_path = os.path.join(self.env.path_ros_ws_src, self.pakkage_version.id)
    #     TypeRos2.unlink_pakkage_from(ros_src_pakkage_path)


class NginxSetup(SetupBase):
    NAME = "nginx"
    VERSION = "0.0.0"

    def __init__(self, parser: ExtendedConfigParser, environment: EnvironmentBase):
        super().__init__(parser, environment)

    def run_setup(self) -> bool:
        return False

        # Adapt nginx to work with user_name user
        logger.info(f"Adapting nginx' www-data to work with {self.user_name} user")
        self.system(f"sudo gpasswd -a www-data {self.user_name}")

        # Adapt nginx config
        logger.info("Adapting nginx config")
        nginx_config_path = "/etc/nginx/sites-enabled/default"
        locations_dir = config.get_abs_path("locations", "Env.Nginx")

        # Search for the following pattern
        # ### PAKK LOCATIONS ###
        # include {locations_dir/*};
        # ### END PAKK LOCATIONS ###

        start_pattern = "### PAKK LOCATIONS ###"
        end_pattern = "### END PAKK LOCATIONS ###"
        content = f"include {locations_dir}/*;"
        all_content = rf"{start_pattern}\n{content}\n{end_pattern}"
        # Escape every $.*/[\]^+?(){}| so that sed does not interpret them as regex
        escape_dict = {
            "$": r"\$",
            ".": r"\.",
            "*": r"\*",
            "/": r"\/",
            "[": r"\[",
            "]": r"\]",
            "^": r"\^",
            "+": r"\+",
            "?": r"\?",
            "(": r"\(",
            ")": r"\)",
            "{": r"\{",
            "}": r"\}",
            "|": r"\|",
        }
        escaped_content = all_content.translate(str.maketrans(escape_dict))

        grep_command = f"sudo grep -q '{start_pattern}' {nginx_config_path}"

        # If the pattern already exists, replace the content
        if os.system(grep_command) == 0:
            logger.info(f"Replacing existing nginx content")
            sed_command = rf"sudo sed -i '/{start_pattern}/,/{end_pattern}/c\\{escaped_content}' {nginx_config_path}"
            os.system(sed_command)
        # Otherwise append the content after the server_name
        else:
            sed_command = rf"sudo sed -i '/server_name _;/a\\{escaped_content}' {nginx_config_path}"
            logger.info(f"Appending nginx sites content: {sed_command}")
            os.system(sed_command)


class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[InitConfigSection]:
        from InquirerPy import inquirer

        sections: list[InitConfigSection] = []
        ros_options: list[InitConfigOption] = []

        launchable = inquirer.confirm("Is the ROS2 pakkage startable?", default=False).execute()

        if launchable:
            package_name = inquirer.text("Name of the launchable ROS2 pakkage:").execute()
            launch_script = inquirer.text("Which launch script:").execute()

            ros_options.append(InitConfigOption("start", f"{package_name} {launch_script}"))

        sections.append(InitConfigSection("ROS2", ros_options))

        return sections
