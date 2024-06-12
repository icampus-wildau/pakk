from __future__ import annotations

import platform

from pakk.environments.base import Environment


def get_current_environment_cls() -> type[Environment]:
    # If we are on a linux system, use the linux environment
    if platform.system() == "Linux":
        from pakk.environments.linux import LinuxEnvironment

        return LinuxEnvironment

    raise NotImplementedError(f"No environment not implemented for this platform ({platform.system()})")


def get_current_environment() -> Environment:
    return get_current_environment_cls()()
