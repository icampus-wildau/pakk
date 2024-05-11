from __future__ import annotations

import configparser
import os

# from pakk.config.base import ConfigEntry, Configuration, CommentConfigParser
from pakk.config.main_cfg import MainConfig

# config_parser = configparser.ConfigParser()
# config_parser.add_section("Test")
# config_parser.set("Test", "Foo", "Bla")
# with open("test.cfg", "w") as f:
#     config_parser.write(f)

cfg = MainConfig()
cfg.inquire()
cfg.write()

for entry in cfg.entries:
    print(entry)


# print("My interpolator")
# p = configparser.ConfigParser(interpolation=EnvInterpolation())
# p.read("test.cfg")

# # Print all config values
# for section in p.sections():
#     for option in p.options(section):
#         print(f"{section}:{option} = {p.get(section, option)}")


# print("Other interpolator")
# p = configparser.ConfigParser(interpolation=OtherEnvInterpolation())
# p.read("test.cfg")

# # Print all config values
# for section in p.sections():
#     for option in p.options(section):
#         print(f"{section}:{option} = {p.get(section, option)}")
