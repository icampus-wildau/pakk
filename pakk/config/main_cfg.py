from __future__ import annotations

import logging

from extended_configparser.configuration import ConfigEntryCollection, ConfigSection
from pakk.config.base import PakkConfigBase

logger = logging.getLogger(__name__)


class MainConfigPaths(ConfigEntryCollection):
    """
    Helper class to bundle the paths for the main configuration for pakk.
    """
    
    def __init__(self):
        section = ConfigSection("Pakk.Dirs")
        self.data_root_dir = section.Option(
            "data_root_dir",
            r"${HOME}/pakk/",
            "Root directory for all pakkage related data",
            long_instruction="The subdirectories defined in [Pakk.Subdirs] will be created in this directory, except you define them as absolute paths.",
        )
        self.app_data_dir = section.Option(
            "app_data_dir",
            r"/opt/pakk/",
            "Directory for application data from pakkages (stored at installation), like models, symlinks, etc.",
        )
        self.log_dir = section.Option("log_dir", r"/var/pakk/logs/", "Directory for log files")
        self.services_dir = section.Option(
            "services_dir", r"/etc/pakk/services/", "Directory for pakk service unit files"
        )

        subdir_section = ConfigSection("Pakk.Subdirs")
        self.cache_dir = subdir_section.Option(
            "cache_dir",
            r"${Pakk.Dirs:data_root_dir}/cache/",
            "Main directory for cache files, e.g. for the discovering process.",
        )
        """Main directory for cache files."""
        
        self.fetch_dir = subdir_section.Option(
            "fetch_dir", r"${Pakk.Dirs:data_root_dir}/fetch/", "Main directory for fetched pakkages."
        )
        """Main directory for fetched pakkages."""
        
        self.pakkages_dir = subdir_section.Option(
            "pakkages_dir", r"${Pakk.Dirs:data_root_dir}/pakkages/", "Main directory for the acktual pakkages."
        )
        """Main directory for the actual pakkages."""
        
        self.enviroment_dir = subdir_section.Option(
            "enviroment_dir", r"${Pakk.Dirs:data_root_dir}/enviroment/", "Main directory for pakk enviroments."
        )
        """Main directory for pakk enviroments."""
        
        self.all_pakkages_dir = subdir_section.Option(
            "all_pakkages_dir",
            r"${pakkages_dir}/all/",
            "Subdirectory for all installed pakkages besides the subdirectories given by the pakkage types.",
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
            default="main",
            message="Channel to check for updates",
            inquire=False,
        )
        

class ConnectorsConfig(ConfigEntryCollection):
    def __init__(self):

        section = ConfigSection("Pakk.Connectors")

        self.enabled = section.SelectOption


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