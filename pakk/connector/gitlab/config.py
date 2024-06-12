from __future__ import annotations

import logging

from extended_configparser.configuration import ConfigSection

from pakk.config.base import ConnectorConfiguration

logger = logging.getLogger(__name__)


class GitlabConfig(ConnectorConfiguration):
    NAME = "gitlab.cfg"

    def __init__(self):
        super().__init__()

        gitlab = ConfigSection("GitLab")
        self.enabled = gitlab.ConfirmationOption("enabled", True, "Enable the connector", inquire=True)

        section_connection = ConfigSection("GitLab.Connection")

        self._api_version = section_connection.Option("api_version", "4", "", inquire=False)
        self._ssl_verify = section_connection.Option("ssl_verify", "True", "", inquire=False)
        self._timeout = section_connection.Option("timeout", "10", "", inquire=False)

        section_projects = ConfigSection("GitLab.Projects")
        self.group_id = section_projects.Option(
            "group_id", "", "Group ID of the GitLab group containing your pakk projects", inquire=self.is_enabled
        )
        self.include_archived = section_projects.ConfirmationOption(
            "include_archived", False, "Include archived projects", inquire=self.is_enabled
        )

        section_connector = ConfigSection("GitLab.Connector")
        self.url = section_connection.Option("url", "", "URL of the GitLab instance", inquire=self.is_enabled)
        """URL of the GitLab instance"""
        self.private_token = section_connection.Option(
            "private_token", "", "Private token for the GitLab instance", inquire=self.is_enabled
        )
        self.num_discover_workers = section_connector.Option(
            "num_discover_workers",
            4,
            "Number of workers for the discoverer",
            inquire=self.is_enabled,
            value_getter=int,
            long_instruction="If num_workers is > 1, the discoverer will use multithreading",
        )
        self.num_fetcher_workers = section_connector.Option(
            "num_fetcher_workers",
            4,
            "Number of workers for the fetcher",
            inquire=self.is_enabled,
            value_getter=int,
            long_instruction="If num_workers is > 1, the fetcher will use multithreading",
        )

        self.cache_dir = section_connector.Option(
            "cache_dir",
            r"${Pakk.Subdirs:cache_dir}/gitlab",
            "Directory for the cache",
            is_dir=True,
            inquire=False,
        )

    def is_enabled(self) -> bool:
        return self.enabled.value and len(self.private_token.value.split()) > 0
