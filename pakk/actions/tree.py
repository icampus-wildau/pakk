from __future__ import annotations

import logging

from rich import print
from rich.tree import Tree

from pakk.args.install_args import InstallArgs
from pakk.helper.lockfile import PakkLock
from pakk.logger import Logger
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.local import LocalConnector
from pakk.modules.dependency_tree.tree import DependencyTree
from pakk.modules.dependency_tree.tree_printer import TreePrinter

logger = logging.getLogger(__name__)


def show_tree(**kwargs):
    lock = PakkLock("tree", create_lock=False)
    if not lock.access:
        logger.warn("Another pakk process is currently running, thus the tree could be wrong.")

    pakkages = PakkageCollection()
    pakkages.discover([LocalConnector()])

    deptree = DependencyTree(pakkages.pakkages)
    deptree.init_pakkages()

    printer = TreePrinter(pakkages.pakkages, deptree)
    tree = printer.get_tree(name="Installed pakkages", max_depth=int(kwargs.get("depth")))
    Logger.get_console().print(tree)


if __name__ == "__main__":
    show_tree(**{"depth": "0"})
