from __future__ import annotations

import os
import logging
from typing import Type, TypeVar

from pakk import DEFAULT_CFG_DIR, ENVS
from extended_configparser.configuration import Configuration

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="PakkConfigBase")

class PakkConfigBase(Configuration):
    """
    Base class for pakk configuration files.
    Provides singleton access to the config via the get_config() method
    """
    NAME: None | str = None
    _instance: None | PakkConfigBase = None
    
    def __init__(self, name: str):
        path = os.path.join(self.get_configs_dir(), name)
        super().__init__(path)

        self.load(inquire_if_missing=True)
        
    
    @staticmethod
    def get_configs_dir() -> str:
        """Return the root directory of all config files"""
        return os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)

    @property
    def configs_dir(self) -> str:
        """The root directory of all config files"""
        return self.get_configs_dir()
    
    @classmethod
    def get_config(cls: Type[T]) -> T:
        """
        Get the instance of this configuration.
        """
        if cls._instance is None:
            if cls.NAME is None:
                raise ValueError(f"NAME of the Configuration must be set. Override the static variable NAME in your {cls.__name__} subclass.")
            
            cls._instance = cls(name=cls.NAME)
            cls._instance.load()

        return cls._instance
        