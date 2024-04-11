from __future__ import annotations
import configparser

from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage

from InquirerPy import inquirer

from typing import TYPE_CHECKING

if TYPE_CHECKING
    from InquirerPy.utils import InquirerPyValidate 


class ConfigEntry():
    def __init__(
        self,
        section: str,
        option: str,
        default: str,
        message: str,
        use_existing_as_default = True,
        instruction: str = None,
        long_instruction: str = None,
        qmark = "?",
        amark = ">",
        validate: InquirerPyValidate | None = None,
    ):
        self.section = section
        self.option = option
        self.default = default
        self.message = message
        self.instruction = instruction
        self.long_instruction = long_instruction
        self.value: str | None = default
        self.use_existing_as_default = use_existing_as_default
        self.amark = amark
        self.qmark = qmark
        self.validate = validate


    def inquire(self):
        self.value = inquirer.text(
            message=self.message,
            default=(self.value if self.use_existing_as_default else self.default),
            instruction=self.instruction,
            long_instruction=self.long_instruction,
            amark=self.amark,
            qmark=self.qmark ,
            validate=self.validate,
            
        ).execute()


class Configuration():
    def __init__(self):
        self.name = ""
        self.entries: list[ConfigEntry] = []

        self.config_path = ""
        self._config_parser = configparser.ConfigParser()

    def read(self):
        self._config_parser.read(self.config_path)
        
        for entry in self.entries:
            entry.value = self._config_parser.get(entry.section, entry.option, fallback=entry.default)
    
    def write(self):
        for entry in self.entries:
            self.set_entry(entry)
            
        with open(self.config_path, "w") as f:
            self._config_parser.write(f)
    
    def set_entry(self, entry: ConfigEntry):
        if not self._config_parser.has_section(section=entry.section):
            self._config_parser.add_section(section=entry.section)
            
        self._config_parser.set(entry.section, entry.option, entry.value)
        


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


class GitHubConfig(ConnectorConfiguration):
    
    def __init__(self):
        super().__init__("github.cfg")
        self.config_path = ""
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(self.config_path)
        self.api_token = ""
    
    @config_option(
        section="connection",
        option="api_token",
        message="",
        long_description=None,
        default="",
    )
    def configure_api_token(self, **kwargs):
        
        self.config_parser.set()
        
        
    