from __future__ import annotations

from pakk.environments.base import Environment


class LinuxEnvironment(Environment):
    """Common Linux environment."""

    def __init__(self):
        super().__init__()

    def setup(self):
        pass
