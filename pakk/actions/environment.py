from __future__ import annotations

import logging
import subprocess

from InquirerPy import inquirer

from pakk.args.base_args import BaseArgs
from pakk.logger import Logger
from pakk.modules.discoverer.base import DiscoveredPakkagesMerger
from pakk.modules.discoverer.discoverer_local import DiscovererLocal

# from pakk.modules.environments.dockerbase import DockerEnvironment
from pakk.modules.types.base import TypeBase
from pakk.pakkage.core import PakkageConfig

logger = logging.getLogger(__name__)


def environment(**kwargs: dict[str, str]):
    base_config = BaseConfig.set(**kwargs)

    flag_verbose = kwargs.get("verbose", False)
    flag_rebuild = kwargs.get("rebuild", False)

    TypeBase.initialize()

    local_discoverer = DiscovererLocal()
    discoverer = DiscoveredPakkagesMerger([local_discoverer])
    discoverer.quiet = not flag_verbose
    pakkages_discovered = discoverer.merge()

    envs: dict[str, DockerEnvironment] = dict()

    for p in pakkages_discovered.values():
        v = p.versions.installed
        if v is None:
            continue

        types = v.pakk_types
        for t in types:
            if hasattr(t, "env"):
                env: DockerEnvironment = t.env
                envs[env.image_name] = env

    # print(env_names)

    env_names = [env.image_name for env in envs.values()]

    action = inquirer.fuzzy(
        message="Select ROS environment to start:",
        choices=list(env_names),
        default="",
    ).execute()

    envs[action].build_image(rebuild_if_exists=flag_rebuild)
    cmd = envs[action].get_interactive_docker_command()
    logger.info(f"Start environment: {action}")
    logger.debug("Running command:")
    logger.debug(cmd)
    p = subprocess.run(cmd, shell=True)


if __name__ == "__main__":
    # kwargs = {
    #     # "all": True,
    #     "types": True,
    #     # "extended": True,
    # }
    kwargs = {}

    environment(**kwargs)
