from __future__ import annotations

import platform

from pakk.modules.environments.base import EnvironmentBase


def get_current_environment_cls() -> type[EnvironmentBase]:
    # If we are on a linux system, use the linux environment
    if platform.system() == "Linux":
        from pakk.modules.environments.linux import LinuxEnvironment

        return LinuxEnvironment

    raise NotImplementedError(f"No environment not implemented for this platform ({platform.system()})")


def get_current_environment() -> EnvironmentBase:
    return get_current_environment_cls()()
