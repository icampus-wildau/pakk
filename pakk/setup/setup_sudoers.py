from __future__ import annotations

import logging
import os
import tempfile

from extended_configparser.parser import ExtendedConfigParser

from pakk.modules.environments.base import EnvironmentBase
from pakk.setup.base import SetupBase

logger = logging.getLogger(__name__)


class PakkSudoersSetup(SetupBase):
    NAME = "sudoers"
    VERSION = "1.0.0"
    PRIORITY = 55

    def __init__(self, parser: ExtendedConfigParser, environment: EnvironmentBase):
        super().__init__(parser, environment)

    def run_setup(self) -> bool:
        # Create sudoers file for pakk group
        # TODO: script execution is security risk, allow that only for checked system pakkages
        paths = [
            "# Created by pakk setup\n",
            # "# Allow pakk group to execute setup scripts in pakkages",
            # f"{data_root_dir}/*/*/*",  # TODO: bspw. für Lilv benötigt, das muss aber besser gehen
            # f"{data_root_dir}/*/*/*/*",
            "/usr/bin/bash",
            "# Allow pakk group to execute apt commands for setups",
            f"/usr/bin/apt",
            f"/usr/bin/apt-get",
            "# Allow pakk group to control systemctl and link service files into the systemd directory",
            f"/usr/bin/systemctl",
            f"/usr/bin/ln",
            "# Allow pakk group to control nginx",
            f"/usr/sbin/nginx",
        ]

        sudoers_file_content = ""
        for p in paths:
            s = p if p.startswith("#") else f"%{self.group_name} ALL=(root) NOPASSWD: {p}"
            s += "\n"
            sudoers_file_content += s

        # Copy sudoers file to /etc/sudoers.d/pakk and change mod to 440
        sudoers_file_path = "/etc/sudoers.d/sudo_pakk"
        logger.info(f"Creating sudoers file at '{sudoers_file_path}'")
        logger.info(f"Content of sudoers file:\n[lightgrey]{sudoers_file_content}[lightgrey]")

        temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        temp_file.write(sudoers_file_content)
        temp_file.flush()
        temp_file.close()
        temp_file_path = temp_file.name

        logger.info(f"Copying '{temp_file_path}' to '{sudoers_file_path}'")
        self.system(f"sudo cp {temp_file_path} {sudoers_file_path}")

        logger.info(f"Changing mod of '{sudoers_file_path}' to 440")
        self.system(f"sudo chmod 440 {sudoers_file_path}")

        # Remove temp file
        self.system(f"rm {temp_file_path}")

        return True
