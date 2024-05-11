from __future__ import annotations

import os

from pakk.modules.module import Module


class EnvPartNginx(Module):
    SECTION_NAME = "Env.Nginx"
    CONFIG_REQUIREMENTS = {SECTION_NAME: ["locations"]}

    def __init__(self):
        super().__init__()
        self.config.require(EnvPartNginx.CONFIG_REQUIREMENTS)

        self.path_locations = self.config.get_abs_path("locations", EnvPartNginx.SECTION_NAME)
