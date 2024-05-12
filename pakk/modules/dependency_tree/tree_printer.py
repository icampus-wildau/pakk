from __future__ import annotations

import logging
from typing import Optional

from rich.tree import Tree

from pakk.modules.dependency_tree.tree import DependencyTree
from pakk.pakkage.core import Pakkage

logger = logging.getLogger(__name__)


class TreePrinter:
    def __init__(
        self,
        pakkages: dict[str, Pakkage],
        dep_tree: DependencyTree,
    ):
        self.dep_tree = dep_tree
        self.pakkages = pakkages
        self.str_method = lambda pakkage, parent_pakkage: str(pakkage)
        self.format_method = self._get_style

    def get_tree(
        self,
        name: str = "Pakkage tree",
        root_nodes: Optional[str | list[str]] = None,
        max_depth: Optional[int] = None,
    ) -> Tree:
        topologic_generations = self.dep_tree.get_topological_generations()

        rich_tree = Tree(name)

        if root_nodes:
            if isinstance(root_nodes, str):
                root_nodes = [root_nodes]

            for root_node in root_nodes:
                root_package = self.pakkages[root_node]
                t_root_node = rich_tree.add(self._get_style(root_package) + self.str_method(root_package, None))
                self._add_children(t_root_node, root_node, 1)
        else:
            toplevel_nodes = []
            if max_depth == 0:
                toplevel_nodes = topologic_generations[0]
            else:
                for gen in topologic_generations:
                    toplevel_nodes.extend(gen)

            for package_id in toplevel_nodes:
                package = self.pakkages[package_id]
                first_level_node = rich_tree.add(self._get_style(package) + self.str_method(package, None))
                self._add_children(first_level_node, package_id, 1, max_depth=max_depth)

        return rich_tree
        # Logger.get_console().print(rich_tree)

    def _get_style(self, package: Pakkage):
        if package.versions.target_fixed:
            return "[bold green]"
        elif package.versions.is_update_candidate():
            if package.versions.installed is None:
                return "[green]"
            else:
                return "[blue]"

        return ""

    def _add_children(self, node: Tree, package_id: str, depth: int, max_depth: Optional[int] = None):
        if max_depth and depth >= max_depth:
            if len(list(self.dep_tree.tree.successors(package_id))) > 0:
                node.add("[gray]...")
            return

        parent_pakkage = self.pakkages[package_id]

        for child_id in self.dep_tree.tree.successors(package_id):
            child_package = self.pakkages[child_id]
            new_node = node.add(self._get_style(child_package) + self.str_method(child_package, parent_pakkage))
            self._add_children(new_node, child_id, depth + 1)
