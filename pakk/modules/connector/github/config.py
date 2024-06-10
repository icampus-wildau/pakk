from __future__ import annotations

import logging

from extended_configparser.configuration import ConfigSection
from extended_configparser.parser import ExtendedConfigParser

from pakk.config.base import ConnectorConfiguration

logger = logging.getLogger(__name__)


class GithubConfig(ConnectorConfiguration):
    NAME = "github.cfg"

    def __init__(self):
        super().__init__()

        self.github_section = ConfigSection("GitHub")
        self.enabled = self.github_section.ConfirmationOption("enabled", True, "Enable the connector", inquire=True)

        self._timeout = self.github_section.Option("timeout", "10", "", inquire=False)

        # self.url = section_connection.Option("url", "", "URL of the GitHub instance", inquire=False)
        # """URL of the GitHub instance"""

        self.cache_dir = self.github_section.Option(
            "cache_dir",
            r"${Pakk.Subdirs:cache_dir}/github",
            "Directory for the cache files",
            inquire=False,
            is_dir=True,
        )
        self.cached_organizations = self.github_section.Option(
            "cached_organizations",
            ["icampus-wildau"],
            "Cache file for known organizations",
            inquire=False,
            value_getter=lambda x: ExtendedConfigParser.split_to_list(x),
            value_setter=lambda x: ExtendedConfigParser.list_to_str(x),
        )
        self.private_token = self.github_section.Option(
            "private_token",
            "",
            "Private token for the GitHub instance",
            value_getter=lambda x: None if (x == "" or x.lower() == "none") else x,
            inquire=self.is_enabled,
        )
        self.num_discover_workers = self.github_section.Option(
            "num_discover_workers",
            4,
            "Number of workers for the discoverer",
            inquire=self.is_enabled,
            value_getter=int,
            long_instruction="If num_workers is > 1, the discoverer will use multithreading",
        )
        self.num_fetcher_workers = self.github_section.Option(
            "num_fetcher_workers",
            4,
            "Number of workers for the fetcher",
            inquire=self.is_enabled,
            value_getter=int,
            long_instruction="If num_workers is > 1, the fetcher will use multithreading",
        )

    def is_enabled(self) -> bool:
        return self.enabled.value
