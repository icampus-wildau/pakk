from __future__ import annotations

import nodesemver

from pakk.modules.dependency_tree.tree import DependencyTree
from pakk.modules.module import Module
from pakk.modules.resolver.base import Resolver
from pakk.modules.resolver.base import ResolverException
from pakk.pakkage.core import Pakkage


class ResolverNewest(Resolver):
    """Resolver that always selects the newest version of unresolved dependency packages"""

    def __init__(self, pakkages: dict[str, Pakkage], config_requirements: dict[str, list[str]] = None):
        super().__init__(pakkages, config_requirements)

        self.deptree = DependencyTree(pakkages)

    def resolve(self) -> dict[str, Pakkage]:
        """Resolve the given packages"""

        Module.print_rule(f"Resolving pakkages")

        self.deptree.init_pakkages()

        while (next_pakkage := self.deptree.get_next_unresolved_pakkage()) is not None:
            self.resolve_node(next_pakkage)
            # if not next_pakkage.versions.is_installed() or next_pakkage.versions.is_update_candidate():

        self.deptree.print_graph()

        topological_sorting = self.deptree.get_topologic_sorting()
        sorted_pakkages = {k: self.pakkages[k] for k in topological_sorting}
        for id in self.pakkages:
            if id not in sorted_pakkages:
                sorted_pakkages[id] = self.pakkages[id]

        self.pakkages = sorted_pakkages
        return self.pakkages

    def resolve_node(self, pakkage: Pakkage):
        print(f"\nResolving {pakkage.id}")

        parent_nodes = list(self.deptree.tree_reverse.neighbors(pakkage.id))
        versions_available = list(pakkage.versions.available.keys())

        # If there is no target version, the node is a not yet resolved dep of a resolved
        no_target = pakkage.versions.target is None
        # If there is a target version, but it is not fixed, the node has multiple parents and needs to be resolved multiple times
        no_fixed_target = pakkage.versions.target is not None and not pakkage.versions.target_fixed
        # If the node is not installed, it needs to be resolved
        is_update_candidate = pakkage.versions.is_update_candidate()
        # If the node got new parents, it needs to be newly resolved
        has_new_parents = pakkage.id in self.deptree.nodes_with_new_parents

        if no_target or no_fixed_target or is_update_candidate or has_new_parents:
            for pn in parent_nodes:
                p_pakkage = self.pakkages[pn]
                dep = p_pakkage.versions.target.dependencies[pakkage.id]
                ver_range = nodesemver.Range(dep, loose=True)
                versions_available = [v for v in versions_available if ver_range.test(v)]

            if len(versions_available) == 0:
                raise ResolverException(pakkage, [self.pakkages[pn] for pn in parent_nodes])

            if pakkage.versions.target_fixed:
                if pakkage.versions.target.version not in versions_available:
                    raise ResolverException(pakkage, [self.pakkages[pn] for pn in parent_nodes])
            else:
                version = nodesemver.max_satisfying(versions_available, "*")
                pakkage.versions.target = pakkage.versions.available[version]

            self.deptree.add_dependencies(pakkage, pakkage.versions.target)

        if pakkage.id in self.deptree.nodes_with_new_parents:
            self.deptree.nodes_with_new_parents.remove(pakkage.id)
