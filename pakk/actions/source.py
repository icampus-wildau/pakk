from __future__ import annotations

import builtins
import logging
import os
import re
import subprocess

from rich.table import Table

import pakk.config.pakk_config as config
from pakk.args.base_args import BaseArgs
from pakk.config.process import Process
from pakk.logger import Logger
from pakk.modules.discoverer.base import DiscoveredPakkagesMerger
from pakk.modules.discoverer.discoverer_gitlab import DiscovererGitlabCached
from pakk.modules.discoverer.discoverer_local import DiscovererLocal
from pakk.modules.types.base import TypeBase

logger = logging.getLogger(__name__)


def source(**kwargs: dict[str, str]):
    base_config = BaseArgs.set()
    flag_verbose = base_config.verbose

    TypeBase.initialize()

    local_discoverer = [DiscovererLocal()]
    discoverer = DiscoveredPakkagesMerger(local_discoverer, quiet=not flag_verbose)
    pakkages_discovered = discoverer.merge()

    Process.set_from_pakkages(pakkages_discovered)
    cmd = Process.get_cmd_env_var_setup(use_linebreak=True)
    print(cmd)
    # p = subprocess.run(cmd, shell=True)
    # os.system(cmd)

    return


if __name__ == "__main__":
    kwargs = {
        # "all": True,
        # "types": True,
        # # "extended": True,
    }

    source(**kwargs)
