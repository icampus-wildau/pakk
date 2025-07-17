from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pakk.environments.base import Environment
from pakk.pakkage.init_helper import InitConfigOption
from pakk.pakkage.init_helper import InitConfigSection
from pakk.pakkage.init_helper import InitHelperBase
from pakk.types.base import TypeBase
from pakk.types.base_instruction_parser import RunInstructionParser

if TYPE_CHECKING:
    from pakk.pakkage.core import PakkageConfig



class RunnableInstructionParser(RunInstructionParser):
    INSTRUCTION_NAME = ["start", "run"]
    # DEFAULT_SUBINSTRUCTION = "launch"

    def __init__(self, environment: Environment):
        super().__init__(environment)
        self.env = environment
        self.command: str | None = None

    def has_cmd(self):
        return self.command is not None

    def get_cmd(self):
        if not self.has_cmd():
            return ""
        
        cmd = self.command or ""
        cmd_words = cmd.split(" ")
        if len(cmd_words) == 1 and (cmd.endswith(".sh") or cmd.endswith(".bash")) and not cmd.startswith("./"):
            cmd = f"./{cmd}"
        
        cmds = [
            self.env.get_cmd_in_environment(cmd)
        ]
        return " && ".join(cmds)

    def parse_start(self, instruction_content: str):
        self.command = instruction_content.strip(' "')

    def parse_run(self, instruction_content: str):
        self.parse_start(instruction_content)


class TypeRunnable(TypeBase):
    PAKKAGE_TYPE: str | None = "Runnable"
    VISIBLE_TYPE = True
    CONFIGURABLE_TYPE = True
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = True
    
    INSTRUCTION_PARSER = [
        RunnableInstructionParser,
    ]

    def __init__(self, pakkage_version: PakkageConfig, env: Environment | None = None):
        super().__init__(pakkage_version, env or Environment())
        self.install_type.has_impact_on_children = False

    def install(self) -> None:
        """Nothing to do here."""
        pass

    def uninstall(self) -> None:
        pass


class InitHelper(InitHelperBase):
    @staticmethod
    def help() -> list[InitConfigSection]:
        return [InitConfigSection("Runnable", [])]
    
    @staticmethod
    def is_suitable_for_directory(directory_path: str) -> bool:
        """Check if this directory contains runnable files."""
        runnable_indicators = [
            "main",              # Main executable
            "run",               # Run script
            "start",             # Start script
            "app",               # App executable
            "server",            # Server executable
            "client",            # Client executable
            "daemon",            # Daemon executable
            "service",           # Service executable
        ]
        
        # Check for executable files without extension (binaries)
        if InitHelperBase._search_executable_files(directory_path, max_depth=2):
            return True
            
        # Check for files with runnable names
        for indicator in runnable_indicators:
            for ext in ['', '.sh', '.bash', '.exe']:
                indicator_path = os.path.join(directory_path, indicator + ext)
                if os.path.exists(indicator_path):
                    return True
                    
        return False
