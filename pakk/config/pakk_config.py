# from __future__ import annotations

# import configparser
# import os
# import re
# import logging

from __future__ import annotations

# from pakk import ROOT_DIR, DEFAULT_CFG_DIR, DEFAULT_CFG_FILENAME, ENVS
# from pakk.helper import file_util
# from pakk.logger import Logger
# logger = logging.getLogger(__name__)

# __config: "Config" = None


# class Sections:
#     MAIN = "Main"
#     SUBDIRS = "Main.Subdirs"
#     ENVIROMENT = "Main.Environment"
#     PAKKAGE = "Main.Pakkage"
#     GITLAB = "GitLab"
#     GITLAB_CONNECTION = "GitLab.Connection"
#     GITLAB_PROJECTS = "GitLab.Projects"
#     DISCOVERER_GITLAB = "Discoverer.GitLab"
#     FETCHER_GITLAB = "Fetcher.GitLab"


# class MissingConfigSectionOptionException(Exception):
#     """
#     Exception that is raised when a required section or option is missing in the config file.
#     """

#     def __init__(self, section: str, option: str | None, source: str | type | None = None):
#         style = "magenta"
#         self.message = "[bold red]Pakk config error: [/bold red]"
#         if section is not None and option is None:
#             self.message += f"Missing required section [{style}]{section}"
#         elif section is not None and option is not None:
#             self.message += f"Missing required option '[{style}]{option}[/{style}]' in section [{style}][{section}][/{style}]"
#         else:
#             self.message += "Missing required section and option"

#         if source is not None:
#             if isinstance(source, type):
#                 source = source.__name__

#             self.message += f" required by '[{style}]{source}[/{style}]'"

#         clean_msg = Logger.get_plain_text(self.message)
#         super().__init__(clean_msg)


# class EnvInterpolation(configparser.ExtendedInterpolation):
#     ENV_PATTERN = re.compile(r"\$\[([^\}]+)\]")
#     _KEYCRE = re.compile(r"\$\{([^}]+)\}")

#     def __init__(self, allow_uninterpolated_values=False):
#         self.allow_uninterpolated_values = allow_uninterpolated_values

#     def _interpolate_some(self, parser, option, accum, rest, section, map,
#                           depth):
#         rawval = parser.get(section, option, raw=True, fallback=rest)
#         if depth > configparser.MAX_INTERPOLATION_DEPTH:
#             raise configparser.InterpolationDepthError(option, section, rawval)
#         while rest:
#             p = rest.find("$")
#             if p < 0:
#                 accum.append(rest)
#                 return
#             if p > 0:
#                 accum.append(rest[:p])
#                 rest = rest[p:]
#             # p is no longer used
#             c = rest[1:2]
#             if c == "$":
#                 accum.append("$")
#                 rest = rest[2:]
#             elif c == "{":
#                 m = self._KEYCRE.match(rest)
#                 if m is None:
#                     raise configparser.InterpolationSyntaxError(option, section,
#                                                                 "bad interpolation variable reference %r" % rest)
#                 path = m.group(1).split(':')
#                 rest = rest[m.end():]
#                 sect = section
#                 opt = option
#                 try:
#                     if len(path) == 1:
#                         # Substitute env vars
#                         if path[0] in os.environ:
#                             v = os.environ[path[0]]
#                         else:
#                             opt = parser.optionxform(path[0])
#                             v = map[opt]
#                     elif len(path) == 2:
#                         sect = path[0]
#                         opt = parser.optionxform(path[1])
#                         if self.allow_uninterpolated_values:
#                             if not parser.has_option(sect, opt):
#                                 accum.append("$" + c + ":".join(path))
#                                 continue
#                         v = parser.get(sect, opt, raw=True)
#                     else:
#                         raise configparser.InterpolationSyntaxError(
#                             option, section,
#                             "More than one ':' found: %r" % (rest,))
#                 except (KeyError, configparser.NoSectionError, configparser.NoOptionError):
#                     raise configparser.InterpolationMissingOptionError(
#                         option, section, rawval, ":".join(path)) from None
#                 if "$" in v:
#                     self._interpolate_some(parser, opt, accum, v, sect,
#                                            dict(parser.items(sect, raw=True)),
#                                            depth + 1)
#                 else:
#                     accum.append(v)
#             else:

#                 if self.allow_uninterpolated_values:
#                     accum.append("$" + c)
#                     rest = rest[2:]
#                 else:
#                     raise configparser.InterpolationSyntaxError(
#                         option, section,
#                         "'$' must be followed by '$' or '{', "
#                         "found: %r" % (rest,))

# # Class that inherits from dict and encapsulates the dict of a configparser
# class Config(configparser.ConfigParser):
#     def __init__(self):
#         # super().__init__(interpolation=EnvInterpolation())
#         super().__init__(defaults=os.environ, interpolation=configparser.ExtendedInterpolation())

#     def require(self, section: str | dict[str, list[str]], options: str | list[str] = None, source: str | type | None = None):
#         if isinstance(section, dict):
#             for section, sec_options in section.items():
#                 self.require(section, sec_options, source)
#             return

#         if not isinstance(section, str):
#             raise Exception("Section must be a dict or string")

#         if not self.has_section(section):
#             raise MissingConfigSectionOptionException(section, None, source)

#         if isinstance(options, str):
#             options = [options]

#         for option in options:
#             if not self.has_option(section, option):
#                 raise MissingConfigSectionOptionException(section, option, source)

#     def get_list(self, section: str, option: str, delimiter=",") -> list[str]:
#         return Config.split_to_list(self.get(section, option), delimiter)

#     @staticmethod
#     def split_to_list(list_str: str, delimiter=",") -> list[str]:
#         if list_str is None or list_str == "":
#             return []
#         return [i.strip() for i in list_str.split(delimiter)]

#     @property
#     def pakk_configuration_files(self) -> list[str]:
#         return self.get_list(Sections.PAKKAGE, "pakkage_files")

#     def get_abs_path(self, option: str, section: str = Sections.SUBDIRS, create_dir=False, none_if_val_is: str | None = None, fallback=None) -> str | None:
#         root = self.get(Sections.MAIN, "data_root_dir", fallback=fallback)
#         if root is None:
#             return None

#         if not os.path.isabs(root):
#             root = os.path.join(ROOT_DIR, root)

#         path = self.get(section, option)
#         if none_if_val_is is not None and path == none_if_val_is:
#             return None

#         if not os.path.isabs(path):
#             path = os.path.join(root, path)

#         n_path = os.path.normpath(path)
#         a_path = os.path.abspath(n_path)

#         if create_dir:
#             if not os.path.exists(a_path):
#                 os.makedirs(a_path, exist_ok=True)

#         return a_path

#     @staticmethod
#     def fix_name_for_env_var(name: str) -> str:
#         return name.replace("-", "_").replace(".", "_").replace(":", "_").upper()

#     @property
#     def env_vars(self):
#         vars = {}

#         sections = [
#             Sections.MAIN,
#             Sections.SUBDIRS,
#         ]

#         for s in sections:
#             for k, v in self[s].items():
#                 env_name = "PAKK_" + Config.fix_name_for_env_var(k)
#                 vars[env_name] = self.get_abs_path(k, s)

#         return vars


# def get_path(option: str, section: str = Sections.SUBDIRS) -> str | None:
#     return get().get_abs_path(option, section)


# def get_base_cfg_path() -> str:
#     config_dir = os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)
#     name = os.environ.get(ENVS.USER_CONFIG_NAME, DEFAULT_CFG_FILENAME)
#     path = os.path.join(config_dir, name)
#     path = os.path.abspath(path)
#     return path

# def get_cfg_paths() -> list[str]:
#     """Return a list of all files ending with 'pakk.cfg' in the config directory"""
#     config_dir = os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)
#     return [os.path.join(config_dir, f) for f in os.listdir(config_dir) if f.endswith("pakk.cfg")]

# # Load the config file from the given path if it exists with a configparser
# def reload() -> Config:
#     base_cfg_path = get_base_cfg_path()
#     paths = get_cfg_paths()

#     # Put base cfg at first place
#     if base_cfg_path in paths:
#         paths.remove(base_cfg_path)
#     paths.insert(0, base_cfg_path)

#     global __config
#     __config = Config()

#     for path in paths:
#         if os.path.exists(path):
#             __config.read(path)

#             if __config.has_section(Sections.MAIN):
#                 for subdir_key in __config[Sections.MAIN].keys():
#                     # Check, if the directory exists
#                     dir_path: str = __config.get_abs_path(subdir_key, section=Sections.MAIN, none_if_val_is="None") # type: ignore
#                     if not os.path.exists(dir_path):
#                         try:
#                             logger.debug(f"Creating directory from [MAIN] at {dir_path}")
#                             os.makedirs(dir_path)
#                         except PermissionError as e:
#                             file_util.create_dir_by_cmd(dir_path, sudo=True)

#             if __config.has_section(Sections.SUBDIRS):
#                 for subdir_key in __config[Sections.SUBDIRS].keys():
#                     # Check, if the directory exists
#                     dir_path: str = __config.get_abs_path(subdir_key, none_if_val_is="None") # type: ignore
#                     if not os.path.exists(dir_path):
#                         logger.debug(f"Creating directory from [SUBDIRS] at {dir_path}")
#                         os.makedirs(dir_path)

#     # d = __config.__dict__
#     return __config


# def get() -> Config:
#     global __config
#     if __config is None:
#         __config = reload()
#     return __config
