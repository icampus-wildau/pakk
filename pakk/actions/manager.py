from __future__ import annotations

import functools
import logging
import subprocess
import threading

from InquirerPy import inquirer

from pakk.args.base_args import BaseArgs
from pakk.config.process import Process
from pakk.helper.cli_util import split_name_version
from pakk.logger import Logger

# from pakk.modules.environments.dockerbase import DockerEnvironment
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.local import LocalConnector
from pakk.modules.types.base import TypeBase
from pakk.pakkage.core import PakkageConfig

logger = logging.getLogger(__name__)


class NotSupportedError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class PakkageNotFoundException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ErrorHandling:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except PakkageNotFoundException as e:
            logger.error(str(e))

            fix_msg = "To fix this, do one of the following:\n"
            fix_msg += f"  - run the command without arguments to get a selection of available, startable pakkages\n"
            fix_msg += f"  - define as argument an existing and startable pakkage (run 'ls' command to see startable pakkages)\n"

            Logger.get_console().print(fix_msg)
        except NotSupportedError as e:
            logger.error(str(e))


def _get_startable_pakkages(
    pakkage_names, select_message="Select pakkage to start:", **kwargs: str
) -> tuple[list[PakkageConfig], PakkageCollection]:
    get_all = kwargs.get("all", False)

    flag_verbose = kwargs.get("verbose", False)

    TypeBase.initialize()

    pakkages = PakkageCollection()
    local_discoverer = LocalConnector()
    pakkages.discover([local_discoverer], quiet=not flag_verbose)

    pakkage_names = [split_name_version(n)[0] for n in pakkage_names]

    startable_pakkages: dict[str, PakkageConfig] = dict()

    for p in pakkages.values():
        v = p.versions.installed
        if v is None:
            continue

        if not pakkage_names or (len(pakkage_names) > 0 and v.id in pakkage_names):
            if v.is_startable():
                startable_pakkages[v.id] = v

    if len(startable_pakkages) == 0:
        # if pakkage_names:
        #     logger.error(f"No startable pakkages found with name '{pakkage_names}'")
        # else:
        #     logger.error("No startable pakkages found")
        return [], pakkages

    pakkages_to_start: list[PakkageConfig] = []
    if not pakkage_names and not get_all:
        action = inquirer.fuzzy(  # type: ignore
            message=select_message,
            choices=list([p for p in startable_pakkages.keys()]),
            default="",
        ).execute()

        pakkages_to_start.append(startable_pakkages[action])
    else:
        if not get_all:
            for p in pakkage_names:
                pakkages_to_start.append(startable_pakkages[p])
        else:
            pakkages_to_start = list(startable_pakkages.values())

    return pakkages_to_start, pakkages


@ErrorHandling
def run(pakkage_names, **kwargs: str):
    pakkages_to_start, pakkages_discovered = _get_startable_pakkages(pakkage_names, "Select pakkage to run:", **kwargs)

    if len(pakkages_to_start) == 0:
        raise PakkageNotFoundException("No pakkages to run")
    if len(pakkages_to_start) > 1:
        raise NotSupportedError("Multiple pakkages to run is not supported yet")

    logger.info(f"Loading environment vars")
    Process.set_from_pakkages(pakkages_discovered)
    pakkages_to_start[0].run()


@ErrorHandling
def start(pakkage_names, **kwargs: str):

    pakkages_to_start, _ = _get_startable_pakkages(pakkage_names, "Select pakkage to start as service:", **kwargs)

    if len(pakkages_to_start) == 0:
        if len(pakkage_names) >= 1:
            raise PakkageNotFoundException(f"No startable pakkages found with name '{', '.join(list(pakkage_names))}'")
        raise PakkageNotFoundException("Found no pakkages to start")
    if len(pakkages_to_start) > 1:
        raise NotSupportedError("Multiple pakkages to start is not supported yet")

    pakkages_to_start[0].start()


@ErrorHandling
def stop(pakkage_names, **kwargs: str):

    pakkages_to_start, _ = _get_startable_pakkages(pakkage_names, "Select pakkage to stop:", **kwargs)

    if len(pakkages_to_start) == 0:
        if len(pakkage_names) >= 1:
            raise PakkageNotFoundException(f"No stoppable pakkages found with name '{', '.join(list(pakkage_names))}'")
        raise PakkageNotFoundException("Found no pakkages to stop")
    if len(pakkages_to_start) > 1:
        raise NotSupportedError("Multiple pakkages to stop is not supported yet")

    pakkages_to_start[0].stop()


@ErrorHandling
def enable(pakkage_names, **kwargs: str):

    pakkages_to_start, _ = _get_startable_pakkages(pakkage_names, "Select pakkage to enable for autostart:", **kwargs)

    if len(pakkages_to_start) == 0:
        if len(pakkage_names) >= 1:
            raise PakkageNotFoundException(f"No pakkages to enable found with name '{', '.join(list(pakkage_names))}'")
        raise PakkageNotFoundException("Found no pakkages to enable")
    if len(pakkages_to_start) > 1:
        raise NotSupportedError("Multiple pakkages to enable is not supported yet")

    pakkages_to_start[0].enable()


@ErrorHandling
def disable(pakkage_names, **kwargs: str):

    pakkages_to_start, _ = _get_startable_pakkages(pakkage_names, "Select pakkage to disable from autostart:", **kwargs)

    if len(pakkages_to_start) == 0:
        if len(pakkage_names) >= 1:
            raise PakkageNotFoundException(f"No pakkages to disable found with name '{', '.join(list(pakkage_names))}'")
        raise PakkageNotFoundException("Found no pakkages to start")
    if len(pakkages_to_start) > 1:
        raise NotSupportedError("Multiple pakkages to disable is not supported yet")

    pakkages_to_start[0].disable()


@ErrorHandling
def restart(pakkage_names, **kwargs: str | bool):
    all_running = kwargs.get("running", False)
    all_enabled = kwargs.get("enabled", False)

    if all_running or all_enabled:
        kwargs["all"] = True
        pakkage_names = []

    pakkages_to_start, _ = _get_startable_pakkages(pakkage_names, "Select pakkage to restart:", **kwargs)  # type: ignore

    if len(pakkages_to_start) == 0:
        if len(pakkage_names) >= 1:
            raise PakkageNotFoundException(f"No pakkages to restart found with name '{', '.join(list(pakkage_names))}'")
        raise PakkageNotFoundException("Found no pakkages to restart")
    # if len(pakkages_to_start) > 1:
    #     raise NotSupportedError("Multiple pakkages to restart is not supported yet")

    threads: list[tuple[PakkageConfig, threading.Thread]] = []

    if all_running:
        pakkages_to_start = [p for p in pakkages_to_start if p.is_active()]
    elif all_enabled:
        pakkages_to_start = [p for p in pakkages_to_start if p.is_enabled()]

    for p in pakkages_to_start:
        t = threading.Thread(target=p.restart)
        t.start()
        threads.append((p, t))

    for p, t in threads:
        t.join()


@ErrorHandling
def follow_log(pakkage_names, **kwargs: str | bool):
    all_running = kwargs.get("running", False)
    all_enabled = kwargs.get("enabled", False)

    if all_running or all_enabled:
        kwargs["all"] = True
        pakkage_names = []

    pakkages_to_start, _ = _get_startable_pakkages(
        pakkage_names, "Select pakkage to follow the log messages:", **kwargs  # type: ignore
    )

    if len(pakkages_to_start) == 0:
        if len(pakkage_names) >= 1:
            raise PakkageNotFoundException(
                f"No pakkages to follow log found with name '{', '.join(list(pakkage_names))}'"
            )
        raise PakkageNotFoundException("Found no pakkages to follow log")
    if len(pakkages_to_start) > 1:
        raise NotSupportedError("Multiple pakkages to follow log is not supported yet")

    pakkages_to_start[0].follow_log()


if __name__ == "__main__":
    # kwargs = {
    #     # "all": True,
    #     "types": True,
    #     # "extended": True,
    # }
    kwargs = {"running": True}

    restart([], **kwargs)
