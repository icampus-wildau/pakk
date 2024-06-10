from __future__ import annotations

import builtins
import logging
import re

from rich.table import Table

from pakk.helper.lockfile import PakkLock
from pakk.logger import Logger
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.local import LocalConnector

logger = logging.getLogger(__name__)


def status(**kwargs: str):
    # flag_all = kwargs.get("all", False)
    # flag_available = kwargs.get("available", False)
    # flag_types = kwargs.get("types", False) or kwargs.get("extended", False)
    flag_types = True

    lock = PakkLock("status", create_lock=False)
    if not lock.access:
        logger.warn("Another pakk process is currently running, thus the list could be wrong.")

    if flag_types:
        from pakk.modules.types.base import TypeBase

        TypeBase.initialize()

    pakkages = PakkageCollection()
    pakkages.discover([LocalConnector()])

    x = kwargs.get("extended", False)

    fields_visible = {
        "ID": True,
        # "Name": x or kwargs.get("name", False),
        "Autostart": True,
        "Status": True,
        "Version": True,
        # "Available Versions": kwargs.get("available", False) or kwargs.get("all"),
        "Type": x or flag_types,
        # "Description": x or kwargs.get("description", False),
        # "Keywords": x or kwargs.get("keywords", False),
    }

    regex = kwargs.get("regex_filter", None)

    title = "Pakkage Status"
    if regex is not None:
        title += f" (matching '{regex}')"

    table = Table(title=title, show_lines=bool(kwargs.get("lines", False)))
    for key, visible in fields_visible.items():
        if visible:
            table.add_column(key, justify="left")

    pakkages = builtins.list(pakkages.values())
    pakkages.sort(key=lambda p: p.id)

    if regex is not None:
        regex = re.compile(regex)

    for p in pakkages:
        if regex is not None and not regex.match(p.id):
            continue

        iv = p.versions.installed
        if iv is None:
            continue

        if not iv.is_startable():
            continue

        is_startable = iv.is_startable() if iv is not None else False
        iv_str = iv.version if iv is not None else "-"

        if flag_types:
            types = iv.pakk_types
            is_startable = iv.is_startable()
            type_names = [
                f"[underline]{t.PAKKAGE_TYPE}[/underline]" if t.is_runnable() else t.PAKKAGE_TYPE
                for t in types
                if t.PAKKAGE_TYPE is not None and t.VISIBLE_TYPE
            ]
            types_str = ", ".join(type_names) if len(type_names) > 0 else "Unknown"
        else:
            types_str = "Unknown"

        id = p.id
        if is_startable:
            id = f"[underline]{id}[/underline]"

        enabled_str = (
            "[white on green]Enabled[/white on green]" if iv.is_enabled() else "[white on red]Disabled[/white on red]"
        )
        status_str = (
            "[white on green]Running[/white on green]" if iv.is_active() else "[white on red]Stopped[/white on red]"
        )

        data = [
            id,
            enabled_str,
            status_str,
            iv_str,
            types_str,
        ]
        data_for_row = []
        for i, field in enumerate(fields_visible.keys()):
            if fields_visible[field]:
                data_for_row.append(data[i])

        table.add_row(*data_for_row)

    Logger.get_console().print(table)
    # Logger.get_console().print(f"Executable pakkages are underlined.")


if __name__ == "__main__":
    kwargs = {
        # "all": True,
        # "types": True,
        # "extended": True,
    }

    status(**kwargs)
