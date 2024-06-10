from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING
from typing import Generic
from typing import Type
from typing import TypeVar

from pakk.config.base import TypeConfiguration
from pakk.config.main_cfg import MainConfig
from pakk.config.process import Process
from pakk.modules.environments.base import GenericEnvironment
from pakk.modules.module import Module
from pakk.modules.types.base_instruction_parser import InstallInstructionParser
from pakk.modules.types.base_instruction_parser import InstructionParser
from pakk.modules.types.base_instruction_parser import RunInstructionParser

if TYPE_CHECKING:
    from pakk.modules.environments.base import EnvironmentBase
    from pakk.pakkage.core import PakkageConfig


# TODO: Setup support for:
# - [x] pip
# - [x] apt
# - [ ] download
# - [ ] npm
# - [ ] yarn
# - [ ] git

# TODO: Allow setup instructions without given type:
# - [x] pip
# - [x] apt

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="InstructionParser", covariant=True)
InstructionParserType = TypeVar("InstructionParserType", bound=InstructionParser)

TB = TypeVar("TB", bound="TypeBase")


class InstallationFailedException(Exception):
    """Exception raised when the installation of a pakkage failed."""

    def __init__(self, message: str):
        super().__init__(message)


class TypeBase(Module, Generic[TB]):
    PAKKAGE_TYPE: str | None = None
    """
    The name of this pakkage type.
    This name is also used as prefix for pakk section names to determine if this type supports the pakkage.

    The name is also shown as in the types section of pakkages.
    """

    VISIBLE_TYPE = True
    """If True, this type is shown in the types section of pakkages list."""

    CONFIGURABLE_TYPE = True
    """If True, this type can be configured in the pakk.cfg file."""

    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = True
    """If True, multiple installations of the same pakkage are allowed."""

    _imported_type_classes: list[type[TypeBase]] | None = None
    """List of all imported type classes."""

    SECTION_NAME = "Types"

    INSTRUCTION_PARSER: list[type[InstructionParser]] = []
    """
    List of instruction parsers for this type.
    The order is important.
    The classes in this list are used to create the instruction parser objects automatically.
    """

    CONFIG_CLS: type[TypeConfiguration] = None
    """
    The configuration class for this type.
    Set this to a subclass of TypeConfiguration to enable configuration for this type when using `pakk configure`.
    """

    def __init__(self, pakkage_version: PakkageConfig, environment: EnvironmentBase):
        super().__init__()

        if self.PAKKAGE_TYPE is None:
            raise ValueError(f"PAKKAGE_TYPE must be set for {self.__class__.__name__}.")

        self.pakkage_version = pakkage_version
        """The pakkage version this type belongs to."""
        self.env = environment  # or GenericEnvironment()
        """The environment used to install this pakkage type."""

        self.install_type = InstallType()
        """Controls the installation behavior of this pakkage type."""

        self.instruction_parser: dict[str, InstructionParser] = {}
        """Dictionary of instruction parsers for this type. Key is the instruction name."""

        for p in self.INSTRUCTION_PARSER:
            if p.INSTRUCTION_NAME is None:
                continue

            parser = p(self.env)
            if isinstance(p.INSTRUCTION_NAME, list):
                for instruction_name in p.INSTRUCTION_NAME:
                    self.instruction_parser[instruction_name] = parser
            elif isinstance(p.INSTRUCTION_NAME, str):
                self.instruction_parser[p.INSTRUCTION_NAME] = parser
            else:
                raise ValueError(
                    f"Invalid instruction name '{p.INSTRUCTION_NAME}' in instruction parser '{p.__name__}'."
                )

        self._instruction_parser_by_cls: dict[type[InstructionParser], InstructionParser] = {
            p.__class__: p for p in self.instruction_parser.values()
        }

        self.instruction_parser_install = [
            p for p in self.instruction_parser.values() if isinstance(p, InstallInstructionParser)
        ]
        """List of instruction parsers that are used for installation."""
        self.instruction_parser_run = [
            p for p in self.instruction_parser.values() if isinstance(p, RunInstructionParser)
        ]
        """List of instruction parsers that are used for running commands."""

        self.config_sections = TypeConfigSection.get_sections(self.pakkage_version, self.PAKKAGE_TYPE)
        """List of parsed config sections for this pakkage type."""
        self.parse_config_sections(self.config_sections)

    def __str__(self):
        return f"{self.PAKKAGE_TYPE} {self.pakkage_version.id}"

    def __repr__(self):
        return str(self)

    def get_instruction_parser_by_cls(self, instruction_cls: Type[InstructionParserType]) -> InstructionParserType:
        """Get the instruction parser for the given instruction class."""
        return self._instruction_parser_by_cls[instruction_cls]

    def parse_undefined_instruction(self, instruction_name: str, instruction_content: str):
        """Parse an unknown instruction. By default, this raises a ValueError, but can be overwritten by subclasses."""
        raise ValueError(f"Unknown instruction '{instruction_name}' in pakk.cfg of {self.pakkage_version.id}.")

    def parse_config_sections(self, config_sections: list[TypeConfigSection]):
        """Parse a list of type config sections for this pakkage type with the defined instruction parsers."""
        for section in config_sections:
            if section.type_name == self.PAKKAGE_TYPE:
                # If the explicit instruction name is omitted, like in "[Setup]"
                # iterate through the instructions and take the key as instruction name
                if section.instruction is None:
                    for instruction_name, instruction_content in section.section_content.items():
                        if instruction_name in self.instruction_parser:
                            logger.debug(
                                f"Parsing instruction '{instruction_name}' for type '{self.PAKKAGE_TYPE}': {instruction_content}."
                            )
                            self.instruction_parser[instruction_name].parse_instruction(
                                instruction_content, instruction_name
                            )
                        else:
                            self.parse_undefined_instruction(instruction_name, instruction_content)
                # If the explicit instruction name is given, like in "[Setup:pip]"
                # iterate through the instructions and take the key as subinstruction
                else:
                    if section.instruction in self.instruction_parser:
                        for sub_instruction, instruction_content in section.section_content.items():
                            self.instruction_parser[section.instruction].parse_instruction(
                                instruction_content, instruction_name, sub_instruction
                            )
                    else:
                        logger.warning(
                            f"TODO: Unknown instruction '{section.instruction}' in pakk.cfg of {self.pakkage_version.id}."
                        )
                        # TODO: is this parameter correct?
                        self.parse_undefined_instruction(section.instruction, section.section_content)

    @staticmethod
    def get_type_classes() -> list[type[TypeBase]]:
        """Return the list of all imported type classes."""
        if TypeBase._imported_type_classes is None:
            TypeBase.initialize()

        if TypeBase._imported_type_classes is None:
            raise ValueError("TypeBase._imported_type_classes is None.")

        return TypeBase._imported_type_classes

    @staticmethod
    def initialize():
        """Imports all types defined in the pakk config."""
        from pakk.helper.loader import PakkLoader

        # Import the defined setup and installation modules
        TypeBase._imported_type_classes = PakkLoader.get_type_classes()

        from pakk.modules.types.type_generic import TypeGeneric

        if TypeGeneric not in TypeBase._imported_type_classes:
            TypeBase._imported_type_classes.append(TypeGeneric)

    @classmethod
    def symlink_pakkage_in_pakkages_dir(cls, pakkage_version: PakkageConfig) -> None:
        """Link the pakkage in the modules directory."""
        path = pakkage_version.local_path
        if path is None:
            raise ValueError("Pakkage version has no local path.")

        if cls.PAKKAGE_TYPE is None:
            raise ValueError(f"PAKKAGE_TYPE must be set for {cls.__name__}.")

        pakkages_dir = MainConfig.get_config().paths.pakkages_dir.value
        if pakkages_dir is None:
            raise ValueError("pakkages_dir is not set in the pakk config.")

        dest_dir = os.path.join(pakkages_dir, cls.PAKKAGE_TYPE)
        dest_path = os.path.join(dest_dir, pakkage_version.basename)

        Module.symlink_pakkage_to(pakkage_version, dest_path)

    @classmethod
    def unlink_pakkage_in_pakkages_dir(cls, pakkage_version: PakkageConfig) -> None:
        """Unlink the pakkage in the module  directory for uninstalling."""
        pakkages_dir = MainConfig.get_config().paths.pakkages_dir.value
        if cls.PAKKAGE_TYPE is None:
            raise ValueError(f"PAKKAGE_TYPE must be set for {cls.__name__}.")
        if pakkages_dir is None:
            raise ValueError("pakkages_dir is not set in the pakk config.")

        dest_dir = os.path.join(pakkages_dir, cls.PAKKAGE_TYPE)
        dest_path = os.path.join(dest_dir, pakkage_version.basename)

        Module.unlink_pakkage_from(dest_path)

    @classmethod
    def allows_multiple_simultaneous_installations(cls) -> bool:
        """Return if the installer allows multiple simultaneous installations."""
        return cls.ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS

    @classmethod
    def supports(cls, pakkage_version: PakkageConfig) -> bool:
        """
        Return if the type supports the given pakkage version.
        This default implementation checks if the pakkage config the type as prefix in the section names.
        """
        # section_names = pakkage_version.cfg.sections()
        section_names = pakkage_version.cfg_sections
        type_names = [re.split(TypeConfigSection.TYPE_DELIMITER, section)[0] for section in section_names]

        if cls.PAKKAGE_TYPE in type_names:
            return True

        return False

    @classmethod
    def supports_environment(cls, environment: EnvironmentBase) -> bool:
        """Return if the type supports the given environment."""
        # raise NotImplementedError()
        return True

    @classmethod
    def supports_section(cls, section_name: str) -> bool:
        """Return if the type supports the given section name."""
        type_name = re.split(TypeConfigSection.TYPE_DELIMITER, section_name)[0]
        return cls.PAKKAGE_TYPE == section_name

    def is_runnable(self) -> bool:
        """Return if the pakkage can be started with this type."""
        for instruction in self.instruction_parser_run:
            if instruction.has_cmd():
                return True

        return False

    def run(self) -> None:
        """Run the pakkage with this type."""
        if not self.is_runnable():
            raise ValueError("Pakkage is not runnable.")

        run_instructions: list[RunInstructionParser] = []
        for instruction in self.instruction_parser_run:
            if instruction.has_cmd():
                run_instructions.append(instruction)

        # if len(run_instructions) > 1:
        #     raise ValueError("Pakkage has multiple run instructions.")

        fetched_instructions = set()
        cmds = []
        for instruction in run_instructions:
            if instruction not in fetched_instructions:
                fetched_instructions.add(instruction)
                if instruction.has_cmd():
                    cmds.append(instruction.get_cmd())

        cmd = " && ".join(cmds)
        envs = Process.get_env_vars()
        logger.info(f"Running pakkage with command '{cmd}'")

        # Expand the environment variables
        os_envs = os.environ.copy()
        pakk_envs = Process.get_env_vars()
        envs = {**os_envs, **pakk_envs}

        self.run_commands(cmd, print_output=True, execute_in_bash=True, env=envs)

    def install(self) -> None:
        """Install the package version with this type."""
        raise NotImplementedError()

    @staticmethod
    def supervised_installation(types: list[TB], raise_exception: bool = False):
        """
        Execute multiple installations simultaneously and handle exceptions.
        If the installation fails, this type is considered as failed.
        """
        try:
            TypeBase.install_multiple(types)
        except InstallationFailedException as e:
            logger.error(f"Installation failed: {e}")

            for type_ in types:
                type_.pakkage_version.state.failed_types.append(type_.__class__.__name__)

            if raise_exception:
                raise e
            # type_.uninstall()
            # raise InstallationFailedException(f"Installation of {type_} failed: {e}")

    @staticmethod
    def install_multiple(types: list[TB]):
        """
        Execute multiple installations simultaneously.
        Should be overwritten if the installer supports optimized simultaneous installations.
        """
        for type_ in types:
            type_.install()

    def uninstall(self) -> None:
        """Uninstall the package with the implemented installer."""
        raise NotImplementedError()


class TypeConfigSection:
    TYPE_DELIMITER = r"[.:]"

    def __init__(self, pakkage_version: PakkageConfig, cfg_section_name: str):
        self.cfg_section_name = cfg_section_name
        splits = re.split(TypeConfigSection.TYPE_DELIMITER, cfg_section_name)

        self.type_name = splits[0] if len(splits) > 0 else None
        """The pakkage type of a pakk config section. In [Type:instruction_type.instruction] it would be 'Type'."""
        self.instruction = splits[1] if len(splits) > 1 else None
        """The instruction for the given pakkage type. In [Type:instruction_type.instruction] it would be 'instruction_type'."""

        self.instruction_suffix = splits[2] if len(splits) > 2 else None
        """The instruction for the given instruction type. In [Type:instruction_type.instruction] it would be 'instruction'."""

        self.section_content = pakkage_version.cfg[cfg_section_name]

    @staticmethod
    def get_sections(
        pakkage_version: PakkageConfig, type_name: str, instruction_name: str | None = None
    ) -> list[TypeConfigSection]:
        """Get the sections for the given type and instruction name."""
        sections = []
        section_names = pakkage_version.cfg.sections()
        for section_name in section_names:
            cfg_section = TypeConfigSection(pakkage_version, section_name)
            if cfg_section.type_name == type_name and (
                instruction_name is None or cfg_section.instruction == instruction_name
            ):
                sections.append(cfg_section)
        return sections


class InstallType:
    def __init__(self):
        self.is_independent = False
        """If True, the installation can be started even if the dependency installations not have finished yet."""

        self.is_combinable_with_children = False
        """If True, the installation can be combined with other install instructions of the same type of the child (parent nodes when looking from the dep tree view) nodes,
        even if they are not independent from dependency nodes and thus should be executed one after the other."""

        """
        Examples:
        ROS: Not IndependentFromDependencies + CombinableWithChildren
        --> ROS nodes should be build only after dependency nodes are finished (e.g. to setup Asset Symlinks etc.)
        --> ROS installation can be combined with other ROS installation (that are independent leaf nodes) (this combining installation is handled by overriding `install_multiple` method in the ROS type)
        --> If a node has only the ROS installation left, it can be combined with other ROS installations in the dependency hierarchie, thus these types are installed before the current dependency node is finished

        Setup: IndependentFromDependencies
        --> Can be installed independently from dependencies, thus can be always installed first from all nodes

        Asset: Not IndependentFromDependencies + Not CombinableWithChildren
        --> Asset nodes should be build only after dependency nodes are finished (e.g. to setup other Asset Symlinks etc.)
        --> Asset installation can not be combined with other Asset installations
        """

        self.has_impact_on_children = True
        """
        If True, the installation of this type has an impact on the installation of the child (parent nodes when looking from the dep tree view) nodes.
        If False, the installation of child nodes can already start before the installation of this type is finished.
        """

        self.is_finished = False

    @property
    def install_priority(self):
        """
        Priority of the install type.
        - independent (highest priority)
        - non-combinable (high priority)
        - combinable (low priority)
        - combinable across hierarchy (lowest priority)
        """

        if self.is_independent:
            return 2
        elif not self.is_combinable_with_children:
            return 1
        else:
            return 0

    def __lt__(self, other: InstallType):
        """
        Compares the install priority of two InstallType objects.
        """
        return self.install_priority < other.install_priority

    def __eq__(self, other: object):
        """
        Compares the install priority of two InstallType objects.
        """
        if not isinstance(other, InstallType):
            return False

        return self.install_priority == other.install_priority
