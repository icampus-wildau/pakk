from __future__ import annotations

import logging

import nodesemver

from pakk.args.install_args import InstallArgs
from pakk.args.install_args import UpdateStrategy
from pakk.logger import Logger
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.dependency_tree.tree import DependencyTree
from pakk.modules.dependency_tree.tree_printer import TreePrinter
from pakk.modules.module import Module
from pakk.modules.resolver.base import Resolver
from pakk.modules.resolver.base import ResolverException
from pakk.pakkage.core import Pakkage

logger = logging.getLogger(__name__)


class ResolverFitting(Resolver):
    """Resolver that tries to select fitting version of unresolved dependency packages"""

    def __init__(self, pakkages: PakkageCollection):
        super().__init__(pakkages)

        self.pakkage_collection = pakkages
        self.deptree = DependencyTree(self.resolver_pakkages.pakkages)
        self.pakkages = self.resolver_pakkages.pakkages
        self.ids_to_be_installed = self.resolver_pakkages.ids_to_be_installed
        self.pakkage_to_be_installed = self.resolver_pakkages.pakkages[next(iter(self.ids_to_be_installed))]
        self.install_config = InstallArgs.get()

    #############################################################
    ### Properties
    #############################################################

    @property
    def _interesting_pakkages(self):
        return [p for p in self.pakkages.values() if p.versions.target is not None or p.versions.installed is not None]

    @property
    def tree_stats(self):
        return f"{self.deptree.tree.number_of_edges()} edges and {self.deptree.tree.number_of_nodes()} nodes"

    #############################################################
    ### Static methods
    #############################################################

    @staticmethod
    def get_fitting_versions(available_versions: list[str], required_versions: list[str]) -> list[str]:
        """Return the fitting versions from the given available versions that fulfill the given required versions.

        Parameters
        ----------
        available_versions : list[str]
            All available versions of the node
        required_versions : list[str]
            All required versions of the parent nodes

        Returns
        -------
        list[str]
            All versions that fit the required versions
        """
        fitting_versions = list(available_versions)
        for ver_range_str in required_versions:
            ver_range = nodesemver.Range(ver_range_str, loose=True)
            fitting_versions = [v for v in fitting_versions if ver_range.test(v)]
        return fitting_versions

    def filter_and_sort_versions(self, pakkage: Pakkage, versions: list[str]) -> list[str]:
        """Filter the given versions by the install config

        Parameters
        ----------
        pakkage : Pakkage
            The pakkage
        versions : list[str]
            The versions to be filtered

        Returns
        -------
        list[str]
            The filtered versions
        """

        pakkage_has_target = pakkage.versions.target is not None
        pakkage_has_fixed_target = pakkage_has_target and pakkage.versions.target_fixed
        installed_version = pakkage.versions.installed

        if pakkage_has_target and pakkage_has_fixed_target:
            versions = [pakkage.versions.target.version] if pakkage.versions.target.version in versions else []  # type: ignore
            return versions

        # Filter versions by install config
        if not self.install_config.allow_downgrade and installed_version:
            versions = [v for v in versions if nodesemver.gte(v, installed_version.version, loose=True)]

        # If eager --> sort fitting_version from newest to oldest
        # If only-if-needed --> sort fitting_version from newest to oldest but put the current version first
        update_strategy = self.install_config.upgrade_strategy  # UpdateStrategy.ONLY_IF_NEEDED
        versions = list(reversed(nodesemver.sort(versions, loose=True)))

        if update_strategy == UpdateStrategy.EAGER:
            pass
        elif update_strategy == UpdateStrategy.ONLY_IF_NEEDED:
            if installed_version is not None and installed_version.version in versions:
                versions.remove(installed_version.version)
                versions.insert(0, installed_version.version)

        return versions

    #############################################################
    ### Main methods
    #############################################################

    def resolve(self, quiet=False) -> PakkageCollection:
        """Resolve the given packages"""

        if not quiet:
            Module.print_rule(f"Resolving pakkages")

        self.deptree.init_pakkages(add_dependencies_for_non_installed=False)
        root = self.pakkage_to_be_installed
        try:
            self._resolve_node(root)
        except ResolverException as e:
            logger.error(f"Could not resolve {root}")
            raise e

        edges = list(self.deptree.tree.edges())
        r_edges = list(self.deptree.tree_reverse.edges())

        # Detect pakkages that are fixing installations and not direct successors
        # of the fixed installation pakkages
        fixed_pakkages = set()
        for pakkage in self.pakkages.values():
            if pakkage.versions.target is not None and pakkage.versions.target_fixed:
                fixed_pakkages.add(pakkage.id)

        for pakkage_id in self.pakkages:
            if pakkage_id in fixed_pakkages:
                self.pakkages[pakkage_id].versions.is_repairing_install = False
            else:
                self.pakkages[pakkage_id].versions.is_repairing_install = self.install_config.repair

        for pakkage_id in fixed_pakkages:
            for successor in self.deptree.tree.successors(pakkage_id):
                self.pakkages[successor].versions.is_repairing_install = False

        # TODO: Fix this when multiple pakkages are installed
        if not quiet:
            root_node = self.deptree.get_root_node(root)
            printer = TreePrinter(self.pakkages, self.deptree)
            # printer = TreePrinter(self.pakkages, self.deptree, root_node=root.id, name="Resolved pakkages")
            tree = printer.get_tree(root_nodes=root_node.id, name="Resolved pakkages")
            Logger.get_console().print(tree)

        topological_sorting = self.deptree.get_topologic_sorting()
        sorted_pakkages = {k: self.pakkages[k] for k in topological_sorting}
        for id in self.pakkages:
            if id not in sorted_pakkages:
                sorted_pakkages[id] = self.pakkages[id]

        self.pakkages = sorted_pakkages
        self.resolver_pakkages.pakkages = sorted_pakkages
        return self.resolver_pakkages
        # return self.pakkages

    def _resolve_node(self, pakkage: Pakkage):
        # print(f"\nResolving {pakkage.id}")
        logger.debug(f"\nResolving {pakkage}")

        parent_nodes = list(self.deptree.tree_reverse.neighbors(pakkage.id))
        parent_pakkages = [self.pakkages[pn] for pn in parent_nodes]

        available_versions = list(pakkage.versions.available.keys())

        parents_with_fixed_versions: list[Pakkage] = [
            self.pakkages[pn] for pn in parent_nodes if self.pakkages[pn].versions.target_fixed
        ]
        parents_without_fixed_versions: list[Pakkage] = [
            self.pakkages[pn] for pn in parent_nodes if not self.pakkages[pn].versions.target_fixed
        ]

        dependency_versions_of_fixed_parents = [
            p.versions.target.dependencies[pakkage.id]
            for p in parents_with_fixed_versions
            if p.versions.target is not None
        ]

        # Check which versions fits all fixed parents
        fitting_versions = self.get_fitting_versions(available_versions, dependency_versions_of_fixed_parents)

        # If pakkage is already installed, filter out versions that do not fit the install config
        fitting_versions = self.filter_and_sort_versions(pakkage, fitting_versions)

        if len(fitting_versions) == 0:
            raise ResolverException(pakkage, parent_pakkages, self.pakkages)

        for fitting_version in fitting_versions:
            old_target_version = pakkage.versions.target
            new_target_version = pakkage.versions.available[fitting_version]

            # If the target is already the same as the new fitting version, but we don't have resolved the version yet, we need to go on.
            # Otherwise, we can stop here
            if old_target_version == new_target_version and pakkage.versions.resolved:
                break

            # Select version
            pakkage.versions.target = pakkage.versions.available[fitting_version]

            # TODO Problem: we cannot store just not working versions without knowing which different versions are currently present in the graph
            # pakkage.versions.target_versions_tried.add(fitting_version)

            # Set to fixed
            target_was_fixed = pakkage.versions.target_fixed
            pakkage.versions.target_fixed = True

            # Add dependencies in graph
            added_deps = self.deptree.add_dependencies(pakkage, pakkage.versions.target)

            edges = list(self.deptree.tree.edges())
            r_edges = list(self.deptree.tree_reverse.edges())

            try:
                # Resolve all parents
                for parent in parents_without_fixed_versions:
                    self._resolve_node(parent)

                for child_id in added_deps:
                    self._resolve_node(self.pakkages[child_id])

            except ResolverException as e:
                # If the version does not fit, try the next one
                # Remove dependencies from graph
                self.deptree.remove_dependencies(pakkage)
                continue
            finally:
                pakkage.versions.target_fixed = target_was_fixed

            pakkage.versions.resolved = True
            # If the version fits, return
            return

        if not pakkage.versions.resolved:
            raise ResolverException(pakkage, parent_pakkages, self.pakkages)
