from __future__ import annotations

import logging
import os
import re
import shlex

from pakk.config.process import Process
from pakk.helper import file_util
from pakk.modules.environments.base import EnvironmentBase
from pakk.modules.environments.linux import LinuxEnvironment
from pakk.modules.types.base import TypeBase
from pakk.modules.types.base_instruction_parser import InstallInstructionParser
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.init_helper import InitConfigOption
from pakk.pakkage.init_helper import InitConfigSection
from pakk.pakkage.init_helper import InitHelperBase

logger = logging.getLogger(__name__)


class LinkInstructionParser(InstallInstructionParser):
    INSTRUCTION_NAME = "link"
    DEFAULT_SUBINSTRUCTION = "link"

    class Link:
        def __init__(self, target: str, link_name: str):
            self.target = target
            self.link_name = link_name

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)
        self.links: list[LinkInstructionParser.Link] = []

    def has_cmd(self):
        return len(self.links) > 0

    def get_cmd(self):
        link_cmds = []
        for link in self.links:
            link_cmds.append(f"ln -sf {link.target} {link.link_name}")

        return " && ".join(link_cmds)

    def parse_link(self, instruction_content: str):
        parts = shlex.split(instruction_content)
        if len(parts) % 2 != 0:
            raise ValueError(f"Invalid link instruction: '{instruction_content}'.")

        for i in range(0, len(parts), 2):
            target = parts[i]
            link_name = parts[i + 1]
            self.links.append(LinkInstructionParser.Link(target, link_name))

    def parse_undefined_subinstruction(self, subinstruction: str, instruction_content: str):
        content_parts = shlex.split(instruction_content)
        subinstruction_parts = shlex.split(subinstruction)

        if len(content_parts) == 1 and len(subinstruction_parts) == 1:
            self.parse_link(f"{subinstruction} {instruction_content}")


class EnvVarInstructionParser(InstallInstructionParser):
    INSTRUCTION_NAME = "env"
    DEFAULT_SUBINSTRUCTION = "set"

    class EnvVar:
        def __init__(self, key: str, val: str):
            self.key = key
            self.val = val

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)
        self.env_vars: list[EnvVarInstructionParser.EnvVar] = []

    def has_cmd(self):
        return len(self.env_vars) > 0

    def get_cmd(self):
        env_cmds = []
        for env_var in self.env_vars:
            env_cmds.append(f"export {env_var.key}={env_var.val}")

        return " && ".join(env_cmds)

    def parse_set(self, instruction_content: str):
        parts = shlex.split(instruction_content)
        if len(parts) % 2 != 0:
            raise ValueError(f"Invalid env instruction: '{instruction_content}'.")

        for i in range(0, len(parts), 2):
            key = parts[i]
            val = parts[i + 1]
            self.env_vars.append(EnvVarInstructionParser.EnvVar(key, val))

    def parse_undefined_subinstruction(self, instruction_content: str, subinstruction: str):
        content_parts = shlex.split(instruction_content)
        subinstruction_parts = shlex.split(subinstruction)

        if len(content_parts) == 1 and len(subinstruction_parts) == 1:
            self.parse_set(f"{subinstruction} {instruction_content}")
        else:
            raise ValueError(f"Invalid env instruction: '{instruction_content}'.")


class TypeAsset(TypeBase):
    """
    Install and setup for asset pakkages.
    """

    PAKKAGE_TYPE: str = "Asset"
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = True

    INSTRUCTION_PARSER = [
        LinkInstructionParser,
        EnvVarInstructionParser,
    ]

    def __init__(self, pakkage_version: PakkageConfig, env: EnvironmentBase):
        super().__init__(pakkage_version, env)

    def parse_undefined_instruction(self, instruction_name: str, instruction_content: str):
        """
        If env vars are defined like:
        [Asset]
        env_key = env_val

        ... then the instruction is unknown, thus we parse it as an env var.
        """
        self.get_instruction_parser_by_cls(EnvVarInstructionParser).parse_instruction(
            f"{instruction_name} {instruction_content}"
        )

    def get_environment_vars(self) -> dict[str, str]:
        env_vars = {}
        v = self.pakkage_version
        if v.local_path is None:
            raise ValueError(f"Local path for pakkage '{v.id}' is not set.")

        parser = self.get_instruction_parser_by_cls(EnvVarInstructionParser)
        for env_var in parser.env_vars:
            val = env_var.val
            key = env_var.key

            if val.startswith("./"):
                val = os.path.join(v.local_path, val)

            temp_env = Process.get_temp_env_vars(self.pakkage_version)
            # Iter over temp envs and search for occurences of them in the value and replace them if found
            for temp_key, temp_val in temp_env.items():
                # Regex to find occurences of the temp env var
                pattern = re.compile(rf"\${{{temp_key}}}|\${temp_key}")
                # Replace all occurences of the temp env var with its value
                val = pattern.sub(temp_val, val)

            names = [key, f"{key}_{v.version}"]
            for name in names:
                n = self.fix_name_for_env_var(name)
                env_vars[n] = val

        return env_vars

    @staticmethod
    def fix_name_for_env_var(name: str) -> str:
        return name.replace("-", "_").replace(".", "_").replace(":", "_").upper()

    def get_symlinks(self) -> list[LinkInstructionParser.Link]:
        parser = self.get_instruction_parser_by_cls(LinkInstructionParser)
        return parser.links

    def setup_symlinks(self, symlinks: list[LinkInstructionParser.Link]):
        if self.pakkage_version.local_path is None:
            raise ValueError(f"Local path for pakkage '{self.pakkage_version.id}' is not set.")

        cmd = Process.get_cmd_env_var_setup()
        for symlink in symlinks:
            if "$" in symlink.target:
                result = self.run_commands(
                    cmd + " && echo " + symlink.target, env=Process.get_temp_env_vars(self.pakkage_version)
                ).strip()
                symlink.target = result
            if "$" in symlink.link_name:
                result = self.run_commands(
                    cmd + " && echo " + symlink.link_name, env=Process.get_temp_env_vars(self.pakkage_version)
                ).strip()
                symlink.link_name = result

            src = (
                symlink.target
                if os.path.isabs(symlink.target)
                else os.path.abspath(os.path.join(self.pakkage_version.local_path, symlink.target))
            )
            dst = (
                symlink.link_name
                if os.path.isabs(symlink.link_name)
                else os.path.abspath(os.path.join(self.pakkage_version.local_path, symlink.link_name))
            )

            if os.path.exists(src):
                if os.path.exists(dst):
                    if os.path.islink(dst):
                        os.remove(dst)
                    else:
                        raise ValueError(
                            f"Cannot create symlink '{dst}' because a file or directory already exists at that location."
                        )
                if os.path.isfile(src):
                    file_util.create_file_symlink(src, dst)
                else:
                    file_util.create_dir_symlink(src, dst)

            else:
                # TODO: better error handling, leading to unsuccessful installation
                raise ValueError(f"Cannot create symlink '{dst}' because the source file '{src}' does not exist.")

    def install(self) -> None:
        """Install a ROS pakkage."""
        logger.info(f"Installing Asset pakkage '{self.pakkage_version.id}'...")

        v = self.pakkage_version

        # Link into pakkages_dir
        self.set_status(v.name, f"Linking {v.basename} into modules directory...")
        self.symlink_pakkage_in_pakkages_dir(v)

        # Setup pakk.env file to store asset instructions as environment variables
        self.set_status(v.name, f"Setting up environment variables for the Asset in {v.basename}...")
        env_vars = self.get_environment_vars()
        self.pakkage_version.save_env_vars(env_vars)

        # Apply env vars and setup links
        Process.update_env_vars(env_vars)
        symlinks = self.get_symlinks()
        self.setup_symlinks(symlinks)

    def uninstall(self) -> None:
        TypeAsset.unlink_pakkage_in_pakkages_dir(self.pakkage_version)


class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[InitConfigSection]:
        return [
            InitConfigSection(
                "Asset",
                [
                    InitConfigOption("# ENV_VAR_KEY", "Environment variable value. (Add as many as you want)"),
                    InitConfigOption(
                        "# link", "link_source link_target (Add as many of these source/target pairs as you want)"
                    ),
                ],
            )
        ]
