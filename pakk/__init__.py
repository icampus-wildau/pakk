import enum
import os
import shutil
from typing import Dict


ROOT_DIR = os.path.realpath(os.path.dirname(__file__))
DEFAULT_CFG_DIR = os.path.join(ROOT_DIR, "..", 'config')
DEFAULT_CFG_FILENAME = os.path.join(DEFAULT_CFG_DIR, 'pakk.cfg')
DEFAULT_USR_CFG_FILENAME = os.path.join(DEFAULT_CFG_DIR, 'user_pakk.cfg')
PAKK_CMD_PATH = shutil.which("pakk")

class ENVS:
    CONFIG_DIR = "PAKK_CONFIG_DIR"
    CONFIG_NAME = "PAKK_CONFIG_NAME"
    USER_CONFIG_NAME = "PAKK_USER_CONFIG_NAME"
