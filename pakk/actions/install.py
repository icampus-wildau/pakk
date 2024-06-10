from __future__ import annotations

import logging

import jellyfish
import nodesemver

from pakk.args.install_args import InstallArgs
from pakk.config.process import Process
from pakk.helper.cli_util import split_name_version
from pakk.helper.loader import PakkLoader
from pakk.helper.lockfile import PakkLock
from pakk.logger import Logger
from pakk.modules.connector.base import PakkageCollection

# from pakk.modules.fetcher.fetcher_gitlab import FetcherGitlab
from pakk.modules.installer.combining_installer import InstallerCombining
from pakk.modules.module import Module
from pakk.modules.resolver.base import ResolverException
from pakk.modules.resolver.resolver_fitting import ResolverFitting
from pakk.modules.types.base import TypeBase
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageInstallState

logger = logging.getLogger(__name__)


class PakkageNotFoundException(Exception):

    # Adapted from https://stackoverflow.com/questions/54172831/hamming-distance-between-two-strings-in-python
    @staticmethod
    def get_most_similar(name: str, available_names: list[str], n=3):
        # jaro_winkler = [(jellyfish.jaro_winkler_similarity(name, x), x) for x in available_names]
        # sorted_jaro_winkler_tuples = sorted(jaro_wikler, key=lambda x: x[0])
        sorted_jaro_winkler = sorted(
            available_names, key=lambda x: (jellyfish.jaro_winkler_similarity(name, x), x), reverse=True
        )
        return sorted_jaro_winkler[:n]

    def __init__(self, package_name: str, available_packages: list[str]):
        s = f"\nPakkage {package_name} not found... Did you mean one of these?\n"
        s += f"  {', '.join(PakkageNotFoundException.get_most_similar(package_name, available_packages))}"

        super().__init__(s)


class AmbivalentIdsException(Exception):
    def __init__(self, package_name: str, available_packages: list[str]):
        s = f"\nAmbivalent package name {package_name}... Did you mean one of these?\n"
        s += f"  {', '.join(available_packages)}"

        super().__init__(s)


class VersionNotFoundException(Exception):
    def __init__(self, package: Pakkage, version: str):
        s = f"\nVersion {version} for {package.id} not found...\n"
        s += f"  Available versions: {list(package.versions.available.keys())}"
        super().__init__(s)


def install(pakkage_names: list[str] | str, **kwargs: str | bool):

    install_args = InstallArgs.get()
    lock = PakkLock("install")
    if not lock.access:
        logger.error("Wait for the other pakk process to finish to continue.")
        return

    ### Normalize input
    if isinstance(pakkage_names, str):
        pakkage_names = [pakkage_names]

    if len(pakkage_names) == 2:
        try:
            _ = nodesemver.Range(pakkage_names[1], loose=True)
            pakkage_names = [pakkage_names[0] + "@" + pakkage_names[1]]
        except ValueError:
            pass

    Module.print_rule(f"Start installation of: {pakkage_names}")

    ### Setup
    # Import necessary modules
    TypeBase.initialize()

    pakkages = PakkageCollection()
    connectors = PakkLoader.get_connector_instances()
    pakkages.discover(connectors, pakkage_names)

    # TODO: Handle undiscovered pakkages

    for n in pakkage_names:
        name, version = split_name_version(n)

        p = pakkages[name]
        if p is None:
            if name not in pakkages.id_abbreviations:
                raise PakkageNotFoundException(name, list(pakkages.keys()))
            elif len(pakkages.id_abbreviations[name]) > 1:
                raise AmbivalentIdsException(name, pakkages.id_abbreviations[name])

            p = pakkages[pakkages.id_abbreviations[name][0]]

            if p is None:
                raise PakkageNotFoundException(name, list(pakkages.keys()))

        pakkages.ids_to_be_installed.add(p.id)
        # installing_pakkage_ids.append(p.id)

        p.versions.target_explicitly_given = version is not None

        # If version is not given, find the correct version
        if version is None:
            if install_args.upgrade:
                version = list(p.versions.available.keys())[0]
                p.versions.target = p.versions.available.get(version, None)
            elif install_args.force_reinstall and p.versions.installed is not None:
                p.versions.target = p.versions.installed
                p.versions.reinstall = True
            elif (
                p.versions.installed is not None
                and p.versions.installed.state.install_state == PakkageInstallState.FAILED
            ):
                p.versions.target = p.versions.installed
                p.versions.reinstall = True
            elif p.versions.installed is None:
                available = list(p.versions.available.keys())
                if len(available) > 0:
                    version = available[0]
                    p.versions.target = p.versions.available.get(version, None)
                elif p.versions.target is not None:
                    p.versions.available[p.versions.target.version] = p.versions.target
            else:
                logger.info(f"{p.id} is already installed at {p.versions.installed}.")
                available_versions = list(p.versions.available.keys())
                # print(available_versions)
                compare_result = nodesemver.compare(p.versions.installed.version, available_versions[0], loose=True)
                if compare_result == 0:
                    logger.info(f"  No newer version available.")
                elif compare_result == -1:
                    logger.info(f"  [bold blue]Newer version available: {available_versions[0]}[/bold blue]")

                # if p.versions.installed < p.versions.available.keys()[-1]
        else:
            p.versions.target = p.versions.available.get(version, None)
            if install_args.force_reinstall:
                p.versions.reinstall = True

        p.versions.target_fixed = True
        if version is not None and p.versions.target is None:
            raise VersionNotFoundException(p, version)

    if len(pakkages.ids_to_be_installed) == 0:
        logger.info("Nothing to install.")
        return

    # print(pakkages.ids_to_be_installed)

    resolver = ResolverFitting(pakkages)
    try:
        if not install_args.no_deps:
            resolver.resolve()
    except ResolverException as e:
        x = e.print_msg()
        return

    # Filter repairing installations
    if not install_args.repair:
        for pakkage in pakkages.pakkages.values():
            if pakkage.versions.target is not None and pakkage.versions.is_repairing_install:
                pakkage.versions.target = None

    # TODO
    # Abfrage, ob Pakete geupdated werden sollen

    installer = InstallerCombining(pakkages, resolver.deptree)
    if install_args.dry_run:
        return

    installer.uninstall()

    pakkages.fetch(connectors=connectors)

    # fetcher = FetcherGitlab(pakkages_resolved)
    # fetcher.fetch()

    Process.set_from_pakkages(pakkages)
    pakkages_installed = installer.install()

    return pakkages_installed


if __name__ == "__main__":
    # pakkages_resolved = install("ros2-basic-user-actions", "0.1.1")
    # install("rose-base-dependencies", pakkages=pakkages_resolved)
    # install(["ros2-basic-user-actions@0.1.5", "ros2-rosass-rose"])

    # TODO: Wenn niedrigere Version angegeben wird als bereits installiert, wird die alte Version nicht als "Update-Candidate" erkannt

    # install("ros2-basic-user-actions")
    # install("rose-base-dependencies")

    # install("robacc")
    # install("ros2-motors@1.0.0")
    # install("ros2-motors@1.0.1")
    # install("ros2-motors@1.0.2")
    # install("ros2-motors@1.0.3")
    # install("ros2-motors")

    kwargs = {
        # "all": True,
        "force_reinstall": True,
        # "refetch": True,
        # "extended": True,
        # "upgrade": True,
        # "upgrade_strategy": "eager",
    }
    # install("flint-models", **kwargs)
    # install("ros2-respeaker", **kwargs)
    # install("scribosermo-model-de", **kwargs)

    # install(["ros2-displays", "ros2-respeaker"], **kwargs)
    # install("ros2-rosbridge-suite", **kwargs)
    # install("ros2-system-info", **kwargs)
    install("ros-i2c", **kwargs)
    # install("ros2-displays", **kwargs)
    # install("ros2-resource-manager", **kwargs)
    # install("ros2-rosass-rose", **kwargs)
    # install("ros2-motors", **kwargs)
    # install("ros2-hardware-interfaces", **kwargs)
    # install("vosk-model-de-small", **kwargs)
