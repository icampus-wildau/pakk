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

        # if is_required and not os.path.exists(path):
        #     raise FileNotFoundError(f"Configuration file {path} not found. Please configure it using `pakk configure {name}`.")

        # self.load(inquire_if_missing=False)
        
    @classmethod
    def get_path(cls):
        """Return the path to the configuration file."""
        if cls.NAME is None:
            raise ValueError(f"NAME of the Configuration must be set. Override the static variable NAME in your {cls.__name__} subclass.")
        return os.path.join(cls.get_configs_dir(), cls.NAME)
    
    @staticmethod
    def get_configs_dir() -> str:
        """Return the root directory of all config files"""
        return os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)

    @classmethod
    def exists(cls) -> bool:
        """Check if the configuration file exists."""
        return os.path.exists(cls.get_path())

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
            if cls._instance.exists():
                cls._instance.load()

        return cls._instance
        