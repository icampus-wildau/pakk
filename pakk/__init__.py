from __future__ import annotations

import enum
import os
import shutil
from typing import Dict

ROOT_DIR = os.path.realpath(os.path.dirname(__file__))
HOME_DIR = os.environ["HOME"]
DEFAULT_CFG_DIR = os.path.join(HOME_DIR, ".config", "pakk")
# DEFAULT_CFG_DIR = os.path.join(ROOT_DIR, "..", "config")
PAKK_CMD_PATH = shutil.which("pakk")


class ENVS:
    CONFIG_DIR = "PAKK_CONFIG_DIR"
    CONFIG_NAME = "PAKK_CONFIG_NAME"
    USER_CONFIG_NAME = "PAKK_USER_CONFIG_NAME"
