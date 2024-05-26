from __future__ import annotations

import logging
import subprocess

from InquirerPy import inquirer
from mdplus.util.parser.ros2_parser import Package
from mdplus.util.parser.ros2_parser import PackageType
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

import pakk.config.pakk_config as pakk_config
from pakk.args.base_args import BaseArgs
from pakk.logger import Logger
from pakk.modules.discoverer.base import DiscoveredPakkagesMerger
from pakk.modules.discoverer.discoverer_local import DiscovererLocal
from pakk.modules.environments.parts.ros2 import EnvPartROS2
from pakk.modules.module import Module
from pakk.modules.types.base import TypeBase
from pakk.modules.types.type_ros2 import TypeRos2
from pakk.pakkage.core import PakkageConfig

logger = logging.getLogger(__name__)


class Ros2RunPackage:
    def __init__(self, pakkage: PakkageConfig, ros_package: Package):
        self.pakkage = pakkage
        self.ros_package = ros_package

    def __str__(self):
        return f"{self.ros_package.name} (from {str(self.pakkage)})"

    def __repr__(self):
        return str(self)


class Ros2RunCompleter(Completer):
    def __init__(self, packages: dict[str, Ros2RunPackage]):
        self.packages = packages

    def get_completions(self, document: Document, complete_event: CompleteEvent):

        word = document.get_word_before_cursor()
        package = None

        splits = document.current_line.split()
        if word == "" and document.cursor_position > 0:
            splits.append("")
        if len(splits) > 1:
            package_name = splits[0]
            package = self.packages.get(package_name, None)

        if package is None:
            for p in self.packages.values():
                name = p.ros_package.name
                if name.startswith(word):
                    yield Completion(
                        text=name,
                        start_position=-len(word),
                    )
        else:
            for n in package.ros_package.nodes:
                name = n.name
                if name.startswith(word):
                    yield Completion(
                        text=name,
                        start_position=-len(word),
                    )


def ros2(run_args: str | list[str], **kwargs: dict[str, str]):
    base_args = BaseArgs.get()
    flag_verbose = kwargs.get("verbose", False)
    TypeBase.initialize()

    if isinstance(run_args, str):
        run_args = run_args.split(" ")

    if len(run_args) == 0:
        run_type = "ros2"
    else:
        run_type = run_args[0]

    # TODO
    if len(run_args) > 1:
        pass

    local_discoverer = DiscovererLocal()
    discoverer = DiscoveredPakkagesMerger([local_discoverer])
    discoverer.quiet = not flag_verbose
    pakkages_discovered = discoverer.merge()

    cfg = pakk_config.get()
    ros_path = cfg.get_abs_path("ws_dir", "Env.ROS2")

    found_ros_packages: dict[str, Ros2RunPackage] = {}

    for pakkage in pakkages_discovered.values():
        installed = pakkage.versions.installed
        if installed is None:
            continue

        types = installed.pakk_types
        if any(isinstance(t, TypeRos2) for t in types):
            path = installed.local_path
            ros_packages = Package.getPackages(path)

            found_ros_packages.update(
                {p.name: Ros2RunPackage(installed, p) for p in ros_packages if p.package_type == PackageType.PYTHON}
            )

    result = inquirer.text(message="ros2 run", completer=Ros2RunCompleter(found_ros_packages), qmark=">").execute()

    # print(result)
    package_name, node_name = result.split(" ")

    pakkage = found_ros_packages[package_name].pakkage
    ros_package = found_ros_packages[package_name].ros_package
    pakk_types = pakkage.pakk_types
    # ros_type = next(t for t in pakk_types if isinstance(t, TypeRos2))
    ros_type = next(t for t in pakkage.pakk_types if isinstance(t, TypeRos2))
    env: EnvPartROS2 = ros_type.env

    # env.build_image(rebuild_if_exists=flag_rebuild)
    # cmd = env.get_interactive_docker_command(f"ros2 run {result}")
    cmd = env.get_interactive_cmd_in_environment(f"{env.get_cmd_setup_ws()} && ros2 run {result}")

    cmd = "$(pakk source) && " + cmd

    print(cmd)
    logger.debug(cmd)
    logger.info(f"Starting: {result}")

    cmd_result = Module.run_commands_with_returncode(cmd, print_output=True, execute_in_bash=True)
    # p = subprocess.run(cmd, shell=True)
    # os.system(cmd)

    logger.info(f"Finished with code {cmd_result[0]}")
    return


if __name__ == "__main__":
    # kwargs = {
    #     # "all": True,
    #     "types": True,
    #     # "extended": True,
    # }
    kwargs = {}

    ros2("ros2", **kwargs)
