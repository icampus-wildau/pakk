from __future__ import annotations

from faulthandler import is_enabled
import logging

from extended_configparser.configuration import ConfigEntryCollection, ConfigSection
from pakk.config.base import PakkConfigBase

logger = logging.getLogger(__name__)

class GitlabConfig(PakkConfigBase):
    NAME = "gitlab.cfg"

    def __init__(self, name: str):
        super().__init__(name)

        gitlab = ConfigSection("GitLab")
        self.enabled = gitlab.ConfirmationOption("enabled", True, "Enable the GitLab connector", inquire=True)
        
        section_connection = ConfigSection("GitLab.Connection")
        self.url = section_connection.Option("url", "", "URL of the GitLab instance", inquire=self.is_enabled)
        """URL of the GitLab instance"""

        self._api_version = section_connection.Option("api_version", "v4", "", inquire=False)
        self._ssl_verify = section_connection.Option("ssl_verify", "True", "", inquire=False)
        self._timeout = section_connection.Option("timeout", "10", "", inquire=False)

        section_projects = ConfigSection("GitLab.Projects")
        self.group_id = section_projects.Option("group_id", "", "Group ID of the GitLab group containing your pakk projects", inquire=self.is_enabled)
        self.include_archived = section_projects.ConfirmationOption("include_archived", False, "Include archived projects", inquire=self.is_enabled)

        section_connector = ConfigSection("GitLab.Connector")
        self.num_discover_workers = section_connector.Option("num_discover_workers", "4", "Number of workers for the discoverer", inquire=self.is_enabled, long_instruction="If num_workers is > 1, the discoverer will use multithreading")
        self.num_fetcher_workers = section_connector.Option("num_fetcher_workers", "4", "Number of workers for the fetcher", inquire=self.is_enabled, long_instruction="If num_workers is > 1, the fetcher will use multithreading")

        self.use_cache = section_connector.ConfirmationOption("use_cache", True, "Use caching for the GitLab connector", inquire=self.is_enabled)

    def is_enabled(self) -> bool:
        return self.enabled.value
