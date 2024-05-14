from __future__ import annotations

import nodesemver

from pakk.logger import Logger
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.dependency_tree.tree import DependencyTree
from pakk.modules.dependency_tree.tree_printer import TreePrinter
from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage


class Resolver(Module):
    def __init__(self, pakkages: PakkageCollection):
        super().__init__()
        self.resolver_pakkages = pakkages

    def resolve(self) -> dict[str, Pakkage]:
        """Resolve all the packages with the implemented resolver."""
        raise NotImplementedError()

    @staticmethod
    def fits_version(version: str, version_ranges: list[str]) -> bool:
        for ver_range_str in version_ranges:
            ver_range = nodesemver.Range(ver_range_str, loose=True)
            if not ver_range.test(version):
                return False
        return True


class ResolverException(Exception):
    def __init__(self, pakkage: Pakkage, parent_pakkages: list[Pakkage], pakkages: dict[str, Pakkage] | None = None):
        self.pakkage = pakkage
        self.parent_pakkages = parent_pakkages
        self.versions_available = list(pakkage.versions.available.keys())
        self.pakkages: dict[str, Pakkage] = pakkages or {}

        s = f"\nCould not resolve {pakkage.id}:\n"
        s += f"  Available versions: [{', '.join(self.versions_available)}]\n"
        for pp in parent_pakkages:
            if pp.versions.installed is not None:
                pp_type = f"(Installed version: {pp.versions.installed.version})"
            elif pp.versions.target is not None:
                pp_type = f"(Target version: {pp.versions.target.version})"
            else:
                pp_type = ""

            dep = pp.versions.target.dependencies[pakkage.id] if pp.versions.target is not None else "NONE"
            s += f"  -> Dependency of {pp.id} {pp_type}: {dep}\n"

        super().__init__(s)

    def print_msg(self):
        msg = ""

        current_deptree = DependencyTree(self.pakkages)
        current_deptree.init_pakkages()

        root_nodes: list[Pakkage] = []

        for pp in self.parent_pakkages:
            root_nodes.append(current_deptree.get_root_node(pp))

        printer = TreePrinter(self.pakkages, current_deptree)

        def str_method(pakkage: Pakkage, parent_pakkage: Pakkage | None = None):

            if pakkage.versions.target is None:
                return f"{pakkage.id}"

            s = f"{pakkage.id} @ {pakkage.versions.target.version}"

            if pakkage.versions.target.version not in pakkage.versions.available:
                s += f" ([bold red]version not available[/bold red])"

            if not parent_pakkage:
                return s

            if pakkage.id not in parent_pakkage.versions.target.dependencies:
                return s

            dependency_version = parent_pakkage.versions.target.dependencies[pakkage.id]
            target_version = pakkage.versions.target.version

            if not Resolver.fits_version(target_version, [dependency_version]):
                s += f": [bold red]conflicting requirement: {parent_pakkage.versions.target.dependencies[pakkage.id]}[/bold red] (from {parent_pakkage.id} @ {parent_pakkage.versions.target.version})"

            return s

        printer.str_method = str_method

        # for root in root_nodes:
        t = printer.get_tree(name=f"Dependencies of {str(self.pakkage)}", root_nodes=[self.pakkage.id])
        Logger.get_console().print(t)
        t = printer.get_tree(
            name=f"Pakkages having {self.pakkage.id} as dependency", root_nodes=[root.id for root in root_nodes]
        )
        Logger.get_console().print(t)
