from __future__ import annotations

import builtins
import logging
import re

from rich.table import Table

from pakk.helper.loader import PakkLoader
from pakk.helper.lockfile import PakkLock
from pakk.logger import Logger
from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.local import LocalConnector
from pakk.pakkage.core import PakkageInstallState

logger = logging.getLogger(__name__)


def list(**kwargs):
    flag_all = kwargs.get("all", False)
    flag_available = kwargs.get("available", False)
    flag_types = kwargs.get("types", False) or kwargs.get("extended", False)
    verbose = kwargs.get("verbose", False)
    has_locations = len(kwargs.get("location", [])) > 0

    lock = PakkLock("list", create_lock=False)
    if not lock.access:
        logger.warn("Another pakk process is currently running, thus the list could be wrong.")

    pakkages = PakkageCollection()

    local_connector: builtins.list[Connector] = [LocalConnector()]
    discoverer_list: builtins.list[Connector] = []

    if flag_all or flag_available:
        connectors = PakkLoader.get_connector_instances()
        discoverer_list = connectors
    else:
        discoverer_list = local_connector

    if flag_types:
        print("Initializing types...")
        from pakk.modules.types.base import TypeBase

        TypeBase.initialize()

    pakkages_discovered = pakkages.discover(discoverer_list)

    # To avoid problems in the type initialization... Maybe there is a better way
    for pakkage in pakkages_discovered.values():
        for version in pakkage.versions.available.values():
            version.local_path = version.local_path or ""

    x = kwargs.get("extended", False)

    fields_visible = {
        "ID": True,
        "Name": x or kwargs.get("name", False),
        "Installed": True,
        "Available Versions": has_locations or kwargs.get("available", False) or kwargs.get("all"),
        "Pakkage Type": x or kwargs.get("types", False),
        "Description": True,  # x or kwargs.get("description", False),
        "Keywords": x or kwargs.get("keywords", False),
    }

    regex = kwargs.get("regex_filter", None)

    title = "Pakkages"
    if regex is not None:
        title += f" (matching '{regex}')"

    table = Table(title=title, show_lines=bool(kwargs.get("lines", False)))
    for key, visible in fields_visible.items():
        if visible:
            table.add_column(key, justify="left")

    pakkages = builtins.list(pakkages_discovered.values())
    pakkages.sort(key=lambda p: p.id)

    if regex is not None:
        regex = re.compile(regex)

    for p in pakkages:
        if regex is not None and not regex.search(p.id):
            continue

        iv = p.versions.installed
        av = p.versions.available
        at = p.versions.target
        is_failed = False
        if iv is not None:
            if iv.state.install_state == PakkageInstallState.FAILED:
                is_failed = True

        if not is_failed:
            if not flag_all:
                if iv is None and not has_locations:
                    continue

        is_startable = iv.is_startable() if iv is not None else False
        iv_str = "[red]FAILED[/red]" if is_failed else (iv.version if iv is not None else "-")

        limit = int(kwargs.get("limit_available", 5))
        av_tag_list = builtins.list(av.keys())
        av_list = builtins.list(av.values())
        av_str = ", ".join(av_tag_list[0:limit]) + (", ..." if len(av_tag_list) > limit else "")

        if flag_types and (iv or len(av_list) > 0):
            v = iv or av_list[0]
            types = v.pakk_types
            is_startable = v.is_startable()
            type_names = [
                f"[underline]{t.PAKKAGE_TYPE}[/underline]" if t.is_runnable() else t.PAKKAGE_TYPE
                for t in types
                if t.PAKKAGE_TYPE is not None and t.VISIBLE_TYPE
            ]
            # types = v.pakk_type_names
            types_str = ", ".join(type_names) if len(type_names) > 0 else "Library"
        else:
            types_str = "Unknown"

        kws = (
            iv.keywords
            if iv is not None
            else builtins.list(av.values())[0].keywords if av is not None and len(av) > 0 else []
        )

        kws = ", ".join(kws)

        id = p.id
        if is_startable:
            id = f"[underline]{id}[/underline]"

        data = [id, p.name, iv_str, av_str, types_str, p.description, kws]
        data_for_row = []
        for i, field in enumerate(fields_visible.keys()):
            if fields_visible[field]:
                data_for_row.append(data[i])

        table.add_row(*data_for_row)

    Logger.get_console().print(table)
    Logger.get_console().print(f"Executable pakkages are underlined.")


if __name__ == "__main__":
    kwargs = {
        "all": True,
        "verbose": True,
    }

    list(**kwargs)
