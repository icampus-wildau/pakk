from __future__ import annotations

from pakk.environments.base import EnvironmentBase

# from pakk.environments.parts.nginx import EnvPartNginx
# from pakk.environments.parts.python import EnvPartPython
# from pakk.environments.parts.ros2 import EnvPartROS2


class LinuxEnvironment(
    EnvironmentBase,
    # EnvPartPython,
    # EnvPartROS2,
    # EnvPartNginx
):
    """Common Linux environment."""

    def __init__(self):
        super().__init__()

    def setup(self):
        pass
