from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from pakk.modules.module import Module


class EnvironmentBase(Module, ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def setup(self):
        """Set the environment up by installing all given dependencies and do other necessary setup steps."""
        raise NotImplementedError()

    def get_cmd_in_environment(self, cmd: str) -> str:
        """
        Get the command in the environment for the given command, e.g. if you need to pre- or append any further commands for your environment.
        By default, the command is returned unchanged.

        Parameters
        ----------
        cmd:
            The command to get the command in the environment for.
        """
        return cmd

    def get_interactive_cmd_in_environment(self, cmd: str) -> str:
        """
        Get the command to interactivly execute stuff in the environment for the given command.
        Overwrite this command, if you need to pre- or append any further commands for your environment.
        By default, the command is returned unchanged.

        Parameters
        ----------
        cmd:
            The command to get the command in the environment for.
        """
        return cmd

    def get_path_in_environment(self, path: str) -> str:
        """
        Get the path in the environment for the given local path.
        By default, the path is returned unchanged.

        Parameters
        ----------
        path:
            The path to get the path in the environment for.
        """
        return path


class GenericEnvironment(EnvironmentBase):
    def __init__(self):
        super().__init__()

    def setup(self):
        pass
