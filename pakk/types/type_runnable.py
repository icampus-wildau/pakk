from __future__ import annotations

from typing import TYPE_CHECKING

from pakk.environments.base import Environment
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
