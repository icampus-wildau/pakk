from __future__ import annotations

import logging
import os
import shlex

import braceexpand

from pakk.args.base_args import BaseArgs
from pakk.config.process import Process
from pakk.modules.environments.base import EnvironmentBase
from pakk.modules.environments.linux import LinuxEnvironment
from pakk.modules.environments.parts.python import EnvPartPython
from pakk.modules.module import Module
from pakk.modules.types.base import TypeBase
from pakk.modules.types.base_instruction_parser import CombinableInstructionParser
from pakk.modules.types.base_instruction_parser import InstallInstructionParser
from pakk.modules.types.base_instruction_parser import InstructionParser
from pakk.modules.types.type_python import PythonTypeConfiguration
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.init_helper import InitConfigOption
from pakk.pakkage.init_helper import InitConfigSection
from pakk.pakkage.init_helper import InitHelperBase

logger = logging.getLogger(__name__)


class AptInstructionParser(CombinableInstructionParser):
    INSTRUCTION_NAME = "apt"
    DEFAULT_SUBINSTRUCTION = "install"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)

        self.apt_packages: list[str] = []

    def has_cmd(self):
        return len(self.apt_packages) > 0

    def get_cmd(self):
        expanded_packages = []
        for p in self.apt_packages:
            expanded_packages.extend(braceexpand.braceexpand(p))
        return f"sudo apt update && sudo apt install -y {' '.join(expanded_packages)}"

    def parse_install(self, instruction_content: str):
        self.apt_packages.extend(shlex.split(instruction_content))

    @staticmethod
    def get_combined_cmd(parser: list[AptInstructionParser]):
        if len(parser) == 0:
            return None

        apt_packages = []
        for i in parser:
            apt_packages.extend(i.apt_packages)

        combined_parser = AptInstructionParser(parser[0].env)
        combined_parser.apt_packages = apt_packages

        if combined_parser.has_cmd():
            return combined_parser.get_cmd()

        return None


class PipInstructionParser(InstructionParser):
    INSTRUCTION_NAME = "pip"
    DEFAULT_SUBINSTRUCTION = "install"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)
        self.requirement_file = None
        self.pip_packages: list[str] = []
        self.python_config = PythonTypeConfiguration.get_config()

    def has_cmd(self):
        return len(self.pip_packages) > 0 or self.requirement_file is not None

    def get_cmd(self):
        cmd = self.python_config.get_cmd_pip_install_package(
            requirements_file=self.requirement_file, packages=self.pip_packages
        )
        return cmd

    def parse_install(self, instruction_content: str):
        parts = shlex.split(instruction_content)
        if "-r" in parts:
            i = parts.index("-r")
            if len(parts) > i + 1:
                self.parse_requirements(parts[i + 1])

            parts = parts[:i] + parts[i + 2 :]
        elif "requirements.txt" in parts:
            i = parts.index("requirements.txt")
            self.parse_requirements(parts[i])

            parts = parts[:i] + parts[i + 1 :]

        self.pip_packages.extend(parts)

    def parse_requirements(self, instruction_content: str):
        path = self.env.get_path_in_environment(instruction_content)
        self.requirement_file = path

    def parse_packages(self, instruction_content: str):
        self.pip_packages.extend(shlex.split(instruction_content))


class ScriptInstructionParser(InstallInstructionParser):
    INSTRUCTION_NAME = "script"
    DEFAULT_SUBINSTRUCTION = "run"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)

        self.scripts: list[str] = []

    def has_cmd(self):
        return len(self.scripts) > 0

    def get_cmd(self):
        return f"{' && '.join(self.scripts)}"

    def parse_run(self, instruction_content: str):
        splits = shlex.split(instruction_content)
        i = 0
        while i < len(splits):
            s = splits[i]
            if s == "sudo":
                self.parse_run_sudo(splits[i + 1])
                i += 2
                continue
            # self.scripts.append(f'sudo -u {os.environ["USER"]} ' + self.env.get_path_in_environment(splits[i]))
            self.scripts.append("bash " + self.env.get_path_in_environment(splits[i]))
            i += 1

    def parse_run_sudo(self, instruction_content: str):
        self.scripts.extend(
            [f"sudo bash {self.env.get_path_in_environment(s)}" for s in shlex.split(instruction_content)]
        )


class LocalEnvVarParser(InstructionParser):
    INSTRUCTION_NAME = "env"
    DEFAULT_SUBINSTRUCTION = "set"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)

        self.env_vars: dict[str, str] = {}

    def has_cmd(self):
        return len(self.env_vars) > 0

    def get_cmd(self):
        return f"{' && '.join([f'export {k}={v}' for k, v in self.env_vars.items()])}"

    def parse_set(self, instruction_content: str):
        splits = shlex.split(instruction_content)
        if len(splits) % 2 != 0:
            raise ValueError(f"Invalid env instruction: '{instruction_content}'.")

        for i in range(0, len(splits), 2):
            key = splits[i]
            val = splits[i + 1]
            self.env_vars[key] = val

    def parse_undefined_subinstruction(self, instruction_content: str, subinstruction: str):
        if subinstruction.startswith("$"):
            self.parse_set(f"{subinstruction[1:]} {instruction_content}")
        else:
            super().parse_undefined_subinstruction(instruction_content, subinstruction)


class GitInstructionParser(InstructionParser):
    INSTRUCTION_NAME = "git"
    DEFAULT_SUBINSTRUCTION = "clone"

    def __init__(self, environment: EnvironmentBase):
        super().__init__(environment)
        self.git_urls: list[str] = []

    def has_cmd(self):
        return len(self.git_urls) > 0

    def get_cmd(self) -> str:
        return " && ".join(f"git clone {url}" for url in self.git_urls)

    def parse_clone(self, instruction_content: str):
        parts = shlex.split(instruction_content)
        parts = [p.strip() for p in parts]
        self.git_urls.extend(parts)

    def parse_submodule(self, instruction_content: str):
        raise NotImplementedError()


class TypeSetup(TypeBase):
    """
    General setup instructions.
    """

    PAKKAGE_TYPE = "Setup"
    VISIBLE_TYPE = False
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = True

    INSTRUCTION_PARSER = [
        LocalEnvVarParser,
        AptInstructionParser,
        PipInstructionParser,
        GitInstructionParser,
        ScriptInstructionParser,
    ]

    def __init__(self, pakkage_version: PakkageConfig, env: EnvironmentBase):
        super().__init__(pakkage_version, env)

        self.install_type.is_independent = True

    def parse_undefined_instruction(self, instruction_name: str, instruction_content: str):
        self.get_instruction_parser_by_cls(LocalEnvVarParser).parse_instruction(
            instruction_content, instruction_name, instruction_name
        )

    def install(self) -> None:
        """Install by executing the setup instruction."""
        logger.info(f"Execute setup instructions for '{self.pakkage_version.id}'...")

        base_cfg = BaseArgs.get()
        v = self.pakkage_version

        if isinstance(self.env, LinuxEnvironment):

            env_vars = self.get_instruction_parser_by_cls(LocalEnvVarParser).env_vars
            Process.update_temp_env_vars(v, env_vars)

            setup_env = os.environ.copy()
            setup_env.update(env_vars)

            for setup_instruction_parser in self.instruction_parser_install:
                if isinstance(setup_instruction_parser, LocalEnvVarParser):
                    continue
                if setup_instruction_parser.has_cmd():

                    self.set_status(
                        v.name, f"Executing setup instruction '{setup_instruction_parser.INSTRUCTION_NAME}'..."
                    )
                    cmd = setup_instruction_parser.get_cmd()
                    self.run_commands(cmd, cwd=self.pakkage_version.local_path, env=setup_env, print_output=True)

    @staticmethod
    def install_multiple(types: list[TypeSetup]):
        """Install multiple setup types in parallel."""
        logger.info(f"Execute setup instructions for {[t.pakkage_version.id for t in types]}...")
        base_cfg = BaseArgs.get()

        for t in types:
            if not isinstance(t.env, LinuxEnvironment):
                raise ValueError(f"Environment '{t.env}' is not a LinuxEnvironment and not supported yet.")

        for t in types:
            env_vars = t.get_instruction_parser_by_cls(LocalEnvVarParser).env_vars
            if len(env_vars) > 0:
                logger.info(f"Set temporal environment variables for '{t.pakkage_version.id}'...")
                Process.update_temp_env_vars(t.pakkage_version, env_vars)

        for instruction_parser in TypeSetup.INSTRUCTION_PARSER:
            if instruction_parser == LocalEnvVarParser:
                continue

            if issubclass(instruction_parser, CombinableInstructionParser):
                types_with_instruction = [
                    t for t in types if t.get_instruction_parser_by_cls(instruction_parser).has_cmd()
                ]
                parser = [t.get_instruction_parser_by_cls(instruction_parser) for t in types_with_instruction]

                cmd = instruction_parser.get_combined_cmd(parser)

                if cmd is None:
                    continue

                logger.info(
                    f"Executing '{instruction_parser.INSTRUCTION_NAME}' instruction for {[t.pakkage_version.id for t in types_with_instruction]}..."
                )
                Module.run_commands(cmd, print_output=True)
            else:
                for t in types:
                    parser = t.get_instruction_parser_by_cls(instruction_parser)
                    if parser.has_cmd():
                        logger.info(
                            f"Executing '{instruction_parser.INSTRUCTION_NAME}' instruction for '{t.pakkage_version.id}'..."
                        )
                        envs = os.environ.copy()
                        temp_env_vars = Process.get_temp_env_vars(t.pakkage_version)
                        envs.update(temp_env_vars)

                        cmd = parser.get_cmd()
                        Module.run_commands(cmd, cwd=t.pakkage_version.local_path, print_output=True, env=envs)

    def uninstall(self) -> None:
        pass


class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[InitConfigSection]:
        return [
            InitConfigSection(
                "Setup",
                [
                    InitConfigOption("# apt", "space separated list of apt packages to install"),
                    InitConfigOption(
                        "# pip", '"-r requirements.txt" and/or space separated list of pip packages to install'
                    ),
                    InitConfigOption("# git", "space separated list of git urls to clone"),
                    InitConfigOption("# script", "Script to execute for setup"),
                ],
            )
        ]
