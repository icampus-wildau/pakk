from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from typing import TYPE_CHECKING
from typing import Callable

from pakk.config.main_cfg import MainConfig
from pakk.helper.file_util import create_dir_symlink
from pakk.helper.file_util import unlink_dir_symlink
from pakk.logger import Logger

if TYPE_CHECKING:
    from pakk.pakkage.core import PakkageConfig

logger = logging.getLogger(__name__)


class Module:
    def __init__(self):
        """
        Instantiate a module.
        """
        self.status_callback: Callable[[str, str], None] = Module._default_status_callback

        self.all_pakkges_dir_path = MainConfig.get_config().paths.all_pakkages_dir.value
        """The path to the directory where all modules are stored."""

    @staticmethod
    def _default_status_callback(pakkage_name: str, info: str):
        pass

    def set_status(self, pakkage_name: str, status: str):
        self.status_callback(pakkage_name, self.get_status_message(status))

    def get_status_message(self, msg: str):
        return rf"\[{self.__class__.__name__}] {msg}"

    @classmethod
    def print_rule(cls, message: str):
        Logger.get_console().rule(f"[bold blue]{message}")

    @classmethod
    def print_empty_lines(cls, n: int = 1):
        Logger.get_console().print(n * "\n")

    @staticmethod
    def run_commands_with_returncode(
        command: str | list[str],
        cwd: str | None = None,
        print_output=False,
        execute_in_bash=False,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        """
        Run a command.
        If command is a list, the elements are concatenated with "&&".

        Parameters
        ----------
        command: str | list[str]
            The command(s) to run.
        cwd: str
            The working directory. If None, the current working directory is used.
        print_output: bool
            If True, the output is printed to the console. Otherwise, it is returned.
        execute_in_bash: bool
            If True, the command is executed in a bash shell.

        Returns
        -------
        tuple(int, str, str): The returncode, stdout and stderr of the command.

        """

        # TODO: Timeout handling

        if cwd is None:
            cwd = os.getcwd()

        if isinstance(command, list):
            command = " && ".join(command)

        if execute_in_bash:
            command = f"bash -c '{command}'"

        result = subprocess.run(command, shell=True, capture_output=(not print_output), text=True, cwd=cwd, env=env)
        return (result.returncode, result.stdout, result.stderr)

    @staticmethod
    def run_commands(
        command: str | list[str],
        cwd: str | None = None,
        print_output=False,
        execute_in_bash=False,
        env: dict[str, str] | None = None,
    ) -> str:
        """
        See run_commands_with_returncode.
        """
        returncode, stdout, stderr = Module.run_commands_with_returncode(
            command, cwd, print_output, execute_in_bash, env
        )
        return stdout

    @staticmethod
    def run_commands_with_output(
        command: str | list[str],
        cwd: str | None = None,
        catch_dynamic_output=False,
        callback: Callable[[str], None] | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        if command is None:
            return ""

        if cwd is None:
            cwd = os.getcwd()

        output_callback = callback

        if output_callback is None:

            def cb(x):
                Logger.get_console().print(x)

            output_callback = cb

        if isinstance(command, list):
            command = " && ".join(command)

        cmd = f'script -c "{command}" /dev/stdout'
        if not catch_dynamic_output or platform.system() == "Windows":
            cmd = command

        complete_output = ""

        # TODO: Catch stderr separately
        with subprocess.Popen(
            cmd,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            env=env,
        ) as p:
            # Capture the output of the subprocess to print the info in the pbar
            if p.stdout is None:
                return ""
            for line in p.stdout:
                complete_output += line
                # remove any whitespace including newlines
                line = line.strip().replace("\r", "").replace("\n", "").strip()

                ansi_escape = re.compile(r"(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])")
                result = ansi_escape.sub("", line)

                with_backslash_escaped = result.replace("\\", "\\\\")

                if with_backslash_escaped != "":
                    output_callback(with_backslash_escaped)

        return complete_output

    @staticmethod
    def symlink_pakkage_to(pakkage_version: PakkageConfig, dest_path: str):
        path = pakkage_version.local_path
        if path is None:
            raise ValueError(f"Path of pakkage {pakkage_version.name} is None.")
        create_dir_symlink(path, dest_path)

        return dest_path

    @staticmethod
    def unlink_pakkage_from(dest_path: str):
        unlink_dir_symlink(dest_path)

    @staticmethod
    def create_dirs(path: str):
        os.makedirs(path, exist_ok=True)
