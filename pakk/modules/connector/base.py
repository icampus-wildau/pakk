from __future__ import annotations
import configparser
import os

from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage

from InquirerPy import inquirer

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from InquirerPy.utils import InquirerPyValidate 

import logging
logger = logging.getLogger(__name__)


class Connector(Module):
    def __init__(self, pakkages: dict[str, Pakkage], config_requirements: dict[str, list[str]] | None = None):
        super().__init__(config_requirements)
        self.pakkages = pakkages

    def discover(self) -> dict[str, Pakkage]:
        """Discover all the packages with the implemented discoverer."""
        raise NotImplementedError()

    def fetch(self) -> dict[str, Pakkage]:
        """Fetch all the packages with the implemented fetcher."""
        raise NotImplementedError()



from functools import wraps


# class GitHubConfig(ConnectorConfiguration):
    
#     def __init__(self):
#         super().__init__("github.cfg")
#         self.config_path = ""
#         self.config_parser = configparser.ConfigParser()
#         self.config_parser.read(self.config_path)
#         self.api_token = ""
    
#     @config_option(
#         section="connection",
#         option="api_token",
#         message="",
#         long_description=None,
#         default="",
#     )
#     def configure_api_token(self, **kwargs):
        
#         self.config_parser.set()
        
        
    