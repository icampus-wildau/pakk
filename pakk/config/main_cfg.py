from __future__ import annotations

import logging

from extended_configparser.configuration import ConfigEntryCollection
from extended_configparser.configuration import ConfigSection

from pakk.config.base import PakkConfigBase

logger = logging.getLogger(__name__)


class MainConfigPaths(ConfigEntryCollection):
    """
    Helper class to bundle the paths for the main configuration for pakk.
    """

    def __init__(self):
        section = ConfigSection("Pakk.Dirs")
        self.pakk_dir_section = section
        self.data_root_dir = section.Option(
            "data_root_dir",
            r"${HOME}/pakk",
            "Root directory for all pakkage related data",
            long_instruction="The subdirectories defined in [Pakk.Subdirs] will be created in this directory, except you define them as absolute paths.",
            is_dir=True,
        )
        self.app_data_dir = section.Option(
            "app_data_dir",
            r"/opt/pakk",
            "Directory for application data from pakkages (stored at installation), like models, symlinks, etc.",
            is_dir=True,
        )
        self.log_dir = section.Option("log_dir", r"/var/pakk/logs", "Directory for log files", is_dir=True)
        self.services_dir = section.Option(
            "services_dir", r"/etc/pakk/services", "Directory for pakk service unit files", is_dir=True
        )

        subdir_section = ConfigSection("Pakk.Subdirs")
        self.cache_dir = subdir_section.Option(
            "cache_dir",
            r"${Pakk.Dirs:data_root_dir}/cache",
            "Main directory for cache files, e.g. for the discovering process.",
            is_dir=True,
        )
        """Main directory for cache files."""

        self.fetch_dir = subdir_section.Option(
            "fetch_dir",
            r"${Pakk.Dirs:data_root_dir}/fetch",
            "Main directory for fetched pakkages.",
            is_dir=True,
        )
        """Main directory for fetched pakkages."""

        self.pakkages_dir = subdir_section.Option(
            "pakkages_dir",
            r"${Pakk.Dirs:data_root_dir}/pakkages",
            "Main directory for the actual pakkages.",
            is_dir=True,
        )
        """Main directory for the actual pakkages."""

        self.environment_dir = subdir_section.Option(
            "environment_dir",
            r"${Pakk.Dirs:data_root_dir}/environment",
            "Main directory for pakk environments.",
            is_dir=True,
        )
        """Main directory for pakk environments."""

        self.all_pakkages_dir = subdir_section.Option(
            "all_pakkages_dir",
            r"${pakkages_dir}/all",
            "Subdirectory for all installed pakkages besides the subdirectories given by the pakkage types.",
            is_dir=True,
        )
        """Subdirectory for all installed pakkages besides the subdirectories given by the pakkage types."""


class AutoUpdateConfig(ConfigEntryCollection):
    """
    Helper class to bundle the autoupdate configuration for pakk.
    """

    def __init__(self):
        section = ConfigSection("Pakk.Autoupdate")
        self.enabled_for_pakk = section.ConfirmationOption(
            option="enabled_for_pakk",
            default=True,
            message="Enable autoupdate of pakk itself",
        )
        """Enable autoupdate of pakk itself"""

        self.enable_for_pakkages = section.ConfirmationOption(
            option="enable_for_pakkages",
            default=True,
            message="Enable autoupdate of installed pakkages",
        )
        """Enable autoupdate of installed pakkages"""

        self.project_url = section.Option(
            option="project_url",
            default="https://github.com/icampus-wildau/pakk",
            message="URL of the project to check for updates",
            inquire=False,
        )
        """URL of the project to check for updates"""

        self.update_channel = section.Option(
            option="update_channel",
            default="pip",
            message="Channel to check for updates. If 'pip' is selected, the pakkage will be updated via pip.",
            inquire=False,
        )


class MainConfig(PakkConfigBase):
    NAME = "main.cfg"

    def __init__(self, name: str):
        super().__init__(name)

        self.paths = MainConfigPaths()
        """All paths of the main configuration."""

        self.autoupdate = AutoUpdateConfig()
        """Autoupdate configuration for pakk."""

        self.pakk_cfg_files = ["pakk.cfg"]
        """
        List of pakkage cfg files.
        At the moment hardcoded to 'pakk.cfg'.
        """
