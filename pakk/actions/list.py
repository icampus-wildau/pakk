from __future__ import annotations
import builtins
import logging

import re
from pakk.helper.lockfile import PakkLock
from pakk.modules.connector.base import Connector, DiscoveredPakkages
from rich.table import Table
from pakk.logger import Logger
from pakk.modules.connector.local import LocalConnector

logger = logging.getLogger(__name__)


def list(**kwargs: str):
    flag_all = kwargs.get("all", False)
    flag_available = kwargs.get("available", False)
    flag_types = kwargs.get("types", False) or kwargs.get("extended", False)
    Logger.setup_logger(logging.INFO)

    lock = PakkLock("list", create_lock=False)
    if not lock.access:
        logger.warn("Another pakk process is currently running, thus the list could be wrong.")


    

    local_connector = [LocalConnector()]
    discoverer_list: list[Connector] = []

    if flag_all or flag_available:
        connectors = Pakk.get_connectors()
        from pakk.modules.discoverer.discoverer_gitlab import DiscovererGitlabCached
        # TODO Used discoverers should be configurable
        available_discoverers = [DiscovererGitlabCached()]
        
        discoverer_list = available_discoverers + local_connector
    else:
        discoverer_list = local_connector

    if flag_types:
        print("Initializing types...")
        from pakk.modules.types.base import TypeBase
        TypeBase.initialize()

    pakkages_discovered = DiscoveredPakkages.discover(discoverer_list)

    x = kwargs.get("extended", False)

    fields_visible = {
        "ID": True,
        "Name": x or kwargs.get("name", False),
        "Installed": True,
        "Available Versions": kwargs.get("available", False) or kwargs.get("all"),
        "Pakkage Type": x or kwargs.get("types", False),
        "Description": True, # x or kwargs.get("description", False),
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

    pakkages = builtins.list(pakkages_discovered.discovered_packages.values())
    pakkages.sort(key=lambda p: p.id)

    if regex is not None:
        regex = re.compile(regex)

    for p in pakkages:
        if regex is not None and not regex.match(p.id):
            continue

        iv = p.versions.installed
        av = p.versions.available
        if not flag_all:
            if iv is None:
                continue

        is_startable = iv.is_startable() if iv is not None else False
        iv_str = iv.version if iv is not None else "-"

        limit = int(kwargs.get("limit_available", 5))
        av_tag_list = builtins.list(av.keys())
        av_list = builtins.list(av.values())
        av_str = ", ".join(av_tag_list[0:limit]) + (", ..." if len(av_tag_list) > limit else "")

        if flag_types and (iv or len(av_list) > 0):
            v = iv or av_list[0]
            types = v.pakk_types
            is_startable = v.is_startable()
            type_names = [f"[underline]{t.PAKKAGE_TYPE}[/underline]" if t.is_runnable() else t.PAKKAGE_TYPE for t in types if t.PAKKAGE_TYPE is not None and t.VISIBLE_TYPE]
            # types = v.pakk_type_names
            types_str = ", ".join(type_names) if len(type_names) > 0 else "Library"
        else:
            types_str = "Unknown"

        kws = iv.keywords if iv is not None else builtins.list(av.values())[0].keywords if av is not None and len(
            av) > 0 else []

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
        # "types": True,
        # "extended": True,
    }

    list(**kwargs)
