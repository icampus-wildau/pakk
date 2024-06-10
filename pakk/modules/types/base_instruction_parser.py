from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pakk.modules.environments.base import EnvironmentBase


class InstructionParser:
    """
    [<PakkageType>:<InstructionType>]
    <subinstruction> = <instruction_content>

    Example:
    ```
    [Setup:pip]
    dependencies = -r requirements.txt
    ```

    PakkaGeType = Setup
    InstructionType = pip
    SubInstruction = dependencies
    InstructionContent = -r requirements.txt

    """

    INSTRUCTION_NAME: str | list[str] | None = None
    DEFAULT_SUBINSTRUCTION: str | None = None

    def __init__(self, environment: EnvironmentBase):
        self.env = environment

    def has_cmd(self):
        raise NotImplementedError()

    def get_cmd(self):
        raise NotImplementedError()

    def parse_undefined_subinstruction(self, instruction_content: str, subinstruction: str):
        raise ValueError(f"Unknown subinstruction '{subinstruction}' for instruction '{self.INSTRUCTION_NAME}'.")

    def parse_instruction(
        self, instruction_content: str, instruction: str | None = None, subinstruction: str | None = None
    ):
        if subinstruction is None:
            if self.DEFAULT_SUBINSTRUCTION is None:
                if isinstance(self.INSTRUCTION_NAME, list):
                    return self.parse_instruction(
                        instruction_content, instruction=instruction, subinstruction=instruction
                    )
                raise ValueError(
                    f"No subinstruction given and no default subinstruction set for instruction '{self.INSTRUCTION_NAME}'."
                )
            return self.parse_instruction(instruction_content, subinstruction=self.DEFAULT_SUBINSTRUCTION)

        if hasattr(self, f"parse_{subinstruction}"):
            return getattr(self, f"parse_{subinstruction}")(instruction_content)
        else:
            return self.parse_undefined_subinstruction(instruction_content, subinstruction)

    @staticmethod
    def get_cmd_env_vars(env_vars: dict[str, str]):
        return " && ".join([f"export {k}={v}" for k, v in env_vars.items()])


class InstallInstructionParser(InstructionParser):
    pass


class CombinableInstructionParser(InstructionParser):
    @staticmethod
    def get_combined_cmd(parser: list[CombinableInstructionParser]):
        return " && ".join([p.get_cmd() for p in parser])


class RunInstructionParser(InstructionParser):
    pass
