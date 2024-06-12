from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING

import networkx as nx
from graphviz import Digraph

if TYPE_CHECKING:
    from pakk.pakkage.core import Pakkage
    from pakk.pakkage.core import PakkageConfig

logger = logging.getLogger(__name__)


class DependencyTree:
    def __init__(self, pakkages: dict[str, Pakkage]):
        self.pakkages = pakkages

        # self.unresolved_pakkages: dict[str, Pakkage] = dict()
        self.unresolved_pakkages: list[str] = list()
        self.nodes_with_new_parents: set[str] = set()

        self.tree: nx.DiGraph = None  # type: ignore
        self.tree_reverse: nx.DiGraph = None  # type: ignore

        self._init_nodes()

    def _init_nodes(self):
        """Initialize the nodes of the graph from the pakkages"""
        g = nx.DiGraph()
        g_reverse = nx.DiGraph()

        for pakkage in self.pakkages.values():
            g.add_node(pakkage.id, pakkage=pakkage)
            g_reverse.add_node(pakkage.id, pakkage=pakkage)

        self.tree = g
        self.tree_reverse = g_reverse

    def get_parent_nodes(self, pakkage: Pakkage) -> list[Pakkage]:
        """Get the parent node of a pakkage"""
        parents = list(self.tree_reverse.neighbors(pakkage.id))
        if len(parents) == 0:
            return []

        return [self.pakkages[p] for p in parents]

    def get_root_node(self, pakkage: Pakkage, visited: dict[str, int] | None = None, step=0):
        """Get the highest parent node of a pakkage"""
        visited = visited or dict()

        current_parents = list(self.tree_reverse.successors(pakkage.id))
        new_parents = [p for p in current_parents if p not in visited]

        for p in new_parents:
            visited[p] = step
            self.get_root_node(self.pakkages[p], visited, step + 1)

        if step == 0:
            if len(visited) == 0:
                return pakkage

            sorted_visited = sorted(visited.items(), key=lambda x: x[1], reverse=True)
            highest_pakkage = self.pakkages[sorted_visited[0][0]]
            return highest_pakkage

        return pakkage

    def init_pakkages(self, add_dependencies_for_non_installed=True):
        logger.debug("Initializing pakkages")
        for p_id, pakkage in self.pakkages.items():
            if pakkage.versions.installed is not None and pakkage.versions.target is None:
                pakkage.versions.target = pakkage.versions.installed
                self.add_dependencies(pakkage, pakkage.versions.installed)
            elif pakkage.versions.target is not None and add_dependencies_for_non_installed:
                self.add_dependencies(pakkage, pakkage.versions.target)

        topologic_sorting = self.get_topologic_sorting()
        # self.unresolved_pakkages = {p_id: self.pakkages[p_id] for p_id in topologic_sorting}
        self.unresolved_pakkages = [p_id for p_id in topologic_sorting]

    def remove_dependencies(self, pakkage: Pakkage) -> set[str]:
        """Remove all dependencies of a pakkage from the tree"""
        neighbors_to_remove = []
        for n in self.tree.neighbors(pakkage.id):
            neighbors_to_remove.append(n)

        for n in neighbors_to_remove:
            self.tree.remove_edge(pakkage.id, n)
            self.tree_reverse.remove_edge(n, pakkage.id)

        return set(neighbors_to_remove)

    def add_dependencies(self, pakkage: Pakkage, version: PakkageConfig):  # -> dict[str, Pakkage]:
        """Add dependencies of a pakkage to the tree"""

        removed_deps = self.remove_dependencies(pakkage)
        added_deps = set()

        for dependency in version.dependencies:
            logger.debug(f"[{pakkage.id}]: Adding dependency {dependency}")

            if dependency not in self.pakkages:
                raise Exception(f"Dependency {dependency} not found in pakkage map")

            self.tree.add_edge(pakkage.id, dependency)
            self.tree_reverse.add_edge(dependency, pakkage.id)
            self.pakkages[dependency].versions.resolved = False

            added_deps.add(dependency)

        # Remove ids, that are already in the tree
        # added_deps.difference_update(self.unresolved_pakkages.keys())
        new_deps = set(added_deps)
        new_deps.difference_update(self.unresolved_pakkages)

        for dep in new_deps:
            self.nodes_with_new_parents.add(dep)
            # self.unresolved_pakkages.append[dep] = self.pakkages[dep]
            self.unresolved_pakkages.append(dep)

        logger.debug(f"G has now {self.tree.number_of_edges()} edges and {self.tree.number_of_nodes()} nodes")

        return added_deps

    def get_topologic_sorting(self, compact=True) -> list[str]:
        """
        Get a topologic sorting of the dependency tree starting with the root nodes, ending with the leafs.
        If compact is True, only the nodes are included that
        are installed or will be installed are included or are dependencies of such nodes.

        Parameters
        ----------
        compact: bool
            If True, return only the nodes that are currently relevant for resolving.

        Returns
        -------
        list[str]: List of node ids

        """
        topologic_sorting = list(reversed(list(nx.algorithms.dag.topological_sort(self.tree))))

        if compact:
            remove_ids = set()
            for node_id in topologic_sorting:
                n_out = len(list(self.tree.neighbors(node_id)))
                n_in = len(list(self.tree_reverse.neighbors(node_id)))
                installed = self.pakkages[node_id].versions.installed is not None
                target = self.pakkages[node_id].versions.target is not None

                if n_out == 0 and n_in == 0 and not installed and not target:
                    remove_ids.add(node_id)

            for node_id in remove_ids:
                topologic_sorting.remove(node_id)

        return topologic_sorting

    def get_topological_generations(self, compact=True, reversed=False) -> list[list[str]]:
        """Get the topological generations of the dependency tree.

        Parameters
        ----------
        compact : bool, optional
            If True, only the nodes are included that are installed or will be installed are included or are dependencies of such nodes, by default True
        reversed : bool, optional
            If True, the generations are returned in reversed order, by default False

        Returns
        -------
        list[list[str]]
            List of generations, where each generation is a list of node ids
        """

        generations = nx.algorithms.dag.topological_generations(self.tree)
        sorted_generations: list[list[str]] = [sorted(generation) for generation in generations]

        if compact:
            remove_ids = set()
            for generation in sorted_generations:
                for node_id in generation:
                    n_out = len(list(self.tree.neighbors(node_id)))
                    n_in = len(list(self.tree_reverse.neighbors(node_id)))
                    installed = self.pakkages[node_id].versions.installed is not None
                    target = self.pakkages[node_id].versions.target is not None

                    if n_out == 0 and n_in == 0 and not installed and not target:
                        remove_ids.add(node_id)

            for generation in sorted_generations:
                for node_id in remove_ids:
                    if node_id in generation:
                        generation.remove(node_id)

        if reversed:
            sorted_generations = list(builtins.reversed(sorted_generations))

        return sorted_generations

    def get_next_unresolved_pakkage(self, remove=True) -> Pakkage | None:
        if len(self.unresolved_pakkages) == 0:
            return None

        p = self.unresolved_pakkages[0]
        if remove:
            self.unresolved_pakkages = self.unresolved_pakkages[1:]

        return self.pakkages[p]

        # p = next(iter(self.unresolved_pakkages.values()))
        # if remove:
        #     del self.unresolved_pakkages[p.id]
        #
        # return p

    def print_graph(self):
        # Create a new graph object
        g = Digraph()

        # Add nodes to the graph
        for node_id, data in self.tree.nodes(data=True):
            neighbors = self.tree.neighbors(node_id)
            n_neighbors = len(list(neighbors))
            n_in_neighbors = len(list(self.tree_reverse.neighbors(node_id)))
            if n_neighbors > 0 or n_in_neighbors > 0:
                v = self.pakkages[node_id].versions.target or self.pakkages[node_id].versions.installed
                g.node(str(node_id), label=v.version if v else node_id)

        # Add edges to the graph
        for edge in self.tree.edges:
            g.edge(str(edge[0]), str(edge[1]))

        # Print the graph on the terminal
        print(g.source)
