from __future__ import annotations

import configparser
import os
import re
import logging

from extended_configparser.configuration.entries import ConfigEntry
from pakk import ROOT_DIR, DEFAULT_CFG_DIR, DEFAULT_CFG_FILENAME, ENVS
from extended_configparser.configuration import ConfigEntryCollection, ConfigSection, Configuration
from pakk.helper import file_util
from pakk.logger import Logger

logger = logging.getLogger(__name__)

__config: "Config" = None


class PakkConfigBase(Configuration):
    def __init__(self, name: str):
        path = os.path.join(MainConfigPaths.get_configs_dir(), name)
        super().__init__(path)


class MainConfigPaths(ConfigEntryCollection):
    def __init__(self):
        section = ConfigSection("Pakk.Dirs")
        self.data_root_dir = section.ConfigOption(
            "data_root_dir",
            r"${HOME}/pakk/",
            "Root directory for all pakkage related data",
            long_instruction="The subdirectories defined in [Pakk.Subdirs] will be created in this directory, except you define them as absolute paths.",
        )
        self.app_data_dir = section.ConfigOption(
            "app_data_dir",
            r"/opt/pakk/",
            "Directory for application data from pakkages (stored at installation), like models, symlinks, etc.",
        )
        self.log_dir = section.ConfigOption("log_dir", r"/var/pakk/logs/", "Directory for log files")
        self.services_dir = section.ConfigOption(
            "services_dir", r"/etc/pakk/services/", "Directory for pakk service unit files"
        )

        subdir_section = ConfigSection("Pakk.Subdirs")
        self.cache_dir = subdir_section.ConfigOption(
            "cache_dir",
            r"${Pakk.Dirs:data_root_dir}/cache/",
            "Main directory for cache files, e.g. for the discovering process.",
        )
        self.fetch_dir = subdir_section.ConfigOption(
            "fetch_dir", r"${Pakk.Dirs:data_root_dir}/fetch/", "Main directory for fetched pakkages."
        )
        self.pakkages_dir = subdir_section.ConfigOption(
            "pakkages_dir", r"${Pakk.Dirs:data_root_dir}/pakkages/", "Main directory for the acktual pakkages."
        )
        self.enviroment_dir = subdir_section.ConfigOption(
            "enviroment_dir", r"${Pakk.Dirs:data_root_dir}/enviroment/", "Main directory for pakk enviroments."
        )
        self.all_pakkages_dir = subdir_section.ConfigOption(
            "all_pakkages_dir",
            r"${pakkages_dir}/all/",
            "Subdirectory for all installed pakkages besides the subdirectories given by the pakkage types.",
        )

    @staticmethod
    def get_configs_dir() -> str:
        return os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)

    @property
    def configs_dir(self) -> str:
        return self.get_config_dir()


class MainConfig(PakkConfigBase):
    def __init__(self):
        super().__init__("main.cfg")
        self.paths = MainConfigPaths()

        self.pakkage_config = ConfigEntry(
            "Pakk.Configs",
            "pakkage_config",
            default="pakk.cfg",
            message="Name of the file containing the pakkage configuration information in your pakkage repository",
            required=True,
            inquire=False,
        )


class Sections:
    MAIN = "Main"
    SUBDIRS = "Main.Subdirs"
    ENVIROMENT = "Main.Environment"
    PAKKAGE = "Main.Pakkage"
    GITLAB = "GitLab"
    GITLAB_CONNECTION = "GitLab.Connection"
    GITLAB_PROJECTS = "GitLab.Projects"
    DISCOVERER_GITLAB = "Discoverer.GitLab"
    FETCHER_GITLAB = "Fetcher.GitLab"


class MissingConfigSectionOptionException(Exception):
    """
    Exception that is raised when a required section or option is missing in the config file.
    """

    def __init__(self, section: str, option: str | None, source: str | type | None = None):
        style = "magenta"
        self.message = "[bold red]Pakk config error: [/bold red]"
        if section is not None and option is None:
            self.message += f"Missing required section [{style}]{section}"
        elif section is not None and option is not None:
            self.message += (
                f"Missing required option '[{style}]{option}[/{style}]' in section [{style}][{section}][/{style}]"
            )
        else:
            self.message += "Missing required section and option"

        if source is not None:
            if isinstance(source, type):
                source = source.__name__

            self.message += f" required by '[{style}]{source}[/{style}]'"

        clean_msg = Logger.get_plain_text(self.message)
        super().__init__(clean_msg)


# Class that inherits from dict and encapsulates the dict of a configparser
class Config(configparser.ConfigParser):
    def __init__(self):
        # super().__init__(interpolation=EnvInterpolation())
        super().__init__(defaults=os.environ, interpolation=configparser.ExtendedInterpolation())

    def require(
        self, section: str | dict[str, list[str]], options: str | list[str] = None, source: str | type | None = None
    ):
        if isinstance(section, dict):
            for section, sec_options in section.items():
                self.require(section, sec_options, source)
            return

        if not isinstance(section, str):
            raise Exception("Section must be a dict or string")

        if not self.has_section(section):
            raise MissingConfigSectionOptionException(section, None, source)

        if isinstance(options, str):
            options = [options]

        for option in options:
            if not self.has_option(section, option):
                raise MissingConfigSectionOptionException(section, option, source)

    def get_list(self, section: str, option: str, delimiter=",") -> list[str]:
        return Config.split_to_list(self.get(section, option), delimiter)

    @staticmethod
    def split_to_list(list_str: str, delimiter=",") -> list[str]:
        if list_str is None or list_str == "":
            return []
        return [i.strip() for i in list_str.split(delimiter)]

    @property
    def pakk_configuration_files(self) -> list[str]:
        return self.get_list(Sections.PAKKAGE, "pakkage_files")

    def get_abs_path(
        self,
        option: str,
        section: str = Sections.SUBDIRS,
        create_dir=False,
        none_if_val_is: str | None = None,
        fallback=None,
    ) -> str | None:
        root = self.get(Sections.MAIN, "data_root_dir", fallback=fallback)
        if root is None:
            return None

        if not os.path.isabs(root):
            root = os.path.join(ROOT_DIR, root)

        path = self.get(section, option)
        if none_if_val_is is not None and path == none_if_val_is:
            return None

        if not os.path.isabs(path):
            path = os.path.join(root, path)

        n_path = os.path.normpath(path)
        a_path = os.path.abspath(n_path)

        if create_dir:
            if not os.path.exists(a_path):
                os.makedirs(a_path, exist_ok=True)

        return a_path

    @staticmethod
    def fix_name_for_env_var(name: str) -> str:
        return name.replace("-", "_").replace(".", "_").replace(":", "_").upper()

    @property
    def env_vars(self):
        vars = {}

        sections = [
            Sections.MAIN,
            Sections.SUBDIRS,
        ]

        for s in sections:
            for k, v in self[s].items():
                env_name = "PAKK_" + Config.fix_name_for_env_var(k)
                vars[env_name] = self.get_abs_path(k, s)

        return vars


def get_path(option: str, section: str = Sections.SUBDIRS) -> str | None:
    return get().get_abs_path(option, section)


def get_base_cfg_path() -> str:
    config_dir = os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)
    name = os.environ.get(ENVS.USER_CONFIG_NAME, DEFAULT_CFG_FILENAME)
    path = os.path.join(config_dir, name)
    path = os.path.abspath(path)
    return path


def get_cfg_paths() -> list[str]:
    """Return a list of all files ending with 'pakk.cfg' in the config directory"""
    config_dir = os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)
    return [os.path.join(config_dir, f) for f in os.listdir(config_dir) if f.endswith("pakk.cfg")]


# Load the config file from the given path if it exists with a configparser
def reload() -> Config:
    base_cfg_path = get_base_cfg_path()
    paths = get_cfg_paths()

    # Put base cfg at first place
    if base_cfg_path in paths:
        paths.remove(base_cfg_path)
    paths.insert(0, base_cfg_path)

    global __config
    __config = Config()

    for path in paths:
        if os.path.exists(path):
            __config.read(path)

            if __config.has_section(Sections.MAIN):
                for subdir_key in __config[Sections.MAIN].keys():
                    # Check, if the directory exists
                    dir_path: str = __config.get_abs_path(subdir_key, section=Sections.MAIN, none_if_val_is="None")  # type: ignore
                    if not os.path.exists(dir_path):
                        try:
                            logger.debug(f"Creating directory from [MAIN] at {dir_path}")
                            os.makedirs(dir_path)
                        except PermissionError as e:
                            file_util.create_dir_by_cmd(dir_path, sudo=True)

            if __config.has_section(Sections.SUBDIRS):
                for subdir_key in __config[Sections.SUBDIRS].keys():
                    # Check, if the directory exists
                    dir_path: str = __config.get_abs_path(subdir_key, none_if_val_is="None")  # type: ignore
                    if not os.path.exists(dir_path):
                        logger.debug(f"Creating directory from [SUBDIRS] at {dir_path}")
                        os.makedirs(dir_path)

    # d = __config.__dict__
    return __config


def get() -> Config:
    global __config
    if __config is None:
        __config = reload()
    return __config
