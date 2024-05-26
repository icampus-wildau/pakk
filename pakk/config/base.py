from __future__ import annotations

import logging
import os
from typing import Type
from typing import TypeVar

from extended_configparser.configuration import Configuration

from pakk import DEFAULT_CFG_DIR
from pakk import ENVS

logger = logging.getLogger(__name__)

C = TypeVar("C", bound="PakkConfigBase")
T = TypeVar("T", bound="TypeConfiguration")


class PakkConfigBase(Configuration):
    """
    Base class for pakk configuration files.
    Provides singleton access to the config via the get_config() method
    """

    NAME: None | str = None
    """Name of the configuration file. Base for the path to the configuration file."""

    CFG_BASE: list[str] = []
    """Names of other configuration files that are used as basis for this configuration."""

    _instance: None | PakkConfigBase = None

    def __init__(self, name: str):
        path = os.path.abspath(os.path.join(self.get_configs_dir(), name))
        base_paths = [os.path.join(self.get_configs_dir(), cfg) for cfg in self.CFG_BASE]
        super().__init__(path, base_paths=base_paths, auto_save=True)

        # if is_required and not os.path.exists(path):
        #     raise FileNotFoundError(f"Configuration file {path} not found. Please configure it using `pakk configure {name}`.")

        # self.load(inquire_if_missing=False)

    @classmethod
    def get_path(cls):
        """Return the path to the configuration file."""
        if cls.NAME is None:
            raise ValueError(
                f"NAME of the Configuration must be set. Override the static variable NAME in your {cls.__name__} subclass."
            )
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
    def __load_config__(cls: Type[C], **args) -> C:
        """
        Load the instance of this configuration with the given arguments.
        """
        if cls._instance is None:
            if cls.NAME is None:
                raise ValueError(
                    f"NAME of the Configuration must be set. Override the static variable NAME in your {cls.__name__} subclass."
                )

            cls._instance = cls(**args)
            if not cls._instance.exists():
                logger.warning(
                    f"Configuration file {cls._instance.config_path} for configuration {cls.__name__} not found."
                )

            cls._instance.load(quiet=True)
            if cls._instance.auto_save:
                if not cls._instance.exists():
                    logger.info(f"Creating configuration file {cls._instance.config_path}")
                cls._instance.write()

        return cls._instance

    @classmethod
    def get_config(cls: Type[C]) -> C:
        """
        Get the instance of this configuration.
        """

        return cls.__load_config__(name=cls.NAME)


class ConnectorConfiguration(PakkConfigBase):
    CFG_BASE = ["main.cfg"]

    def __init__(self):
        if self.NAME is None:
            logger.warning(
                f"NAME of the Configuration must be set. Override the static variable NAME in your {self.__class__.__name__} subclass."
            )
        super().__init__(self.NAME or "connector.cfg")

    def is_enabled(self) -> bool:
        raise NotImplementedError(f"is_enabled() must be implemented in the subclass of {self.__class__.__name__}")

    @classmethod
    def get_config(cls: Type[C]) -> C:
        """
        Get the instance of this configuration.
        """

        return cls.__load_config__()


class TypeConfiguration(PakkConfigBase):
    """
    Base class for pakkage type configurations
    """

    NAME = "types.cfg"
    CFG_BASE = ["main.cfg"]

    def __init__(self):
        super().__init__(TypeConfiguration.NAME or "types.cfg")

    @classmethod
    def get_config(cls: Type[T]) -> T:
        """
        Get the instance of this configuration.
        """

        return cls.__load_config__()
