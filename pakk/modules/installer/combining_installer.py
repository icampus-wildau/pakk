from __future__ import annotations

import logging
from typing import Callable

import networkx as nx

from pakk.args.install_args import InstallArgs
from pakk.config.main_cfg import MainConfig
from pakk.logger import Logger
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.dependency_tree.tree import DependencyTree
from pakk.modules.module import Module
from pakk.modules.types.base import TypeBase
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageConfig
from pakk.pakkage.core import PakkageInstallState

logger = logging.getLogger(__name__)


class InstallNode:
    """Node in the install graph."""

    def __init__(self, pakkage_config: PakkageConfig, depth: int = 0):
        """Initialize the install node for the given pakkage config."""
        self.depth = depth
        self.pakkage_config = pakkage_config
        """Pakkage config for this node."""

        self.types_to_install: list[TypeBase] = pakkage_config.pakk_types.copy()
        """Types that still need to be installed for this node."""

    @property
    def is_finished(self):
        return len(self.types_to_install) == 0

    def __str__(self):
        return f"InstallNode: {self.pakkage_config.id} ({self.types_to_install})"

    def __repr__(self):
        return str(self)


class InstallGraph:
    """Graph representing the dependency tree as nodes of pakkage configs to be installed."""

    def __init__(self, pakkages_to_install: list[Pakkage], deptree: DependencyTree):
        """Initialize the install graph for the given pakkages to install and resolved dependency tree.

        Parameters
        ----------
        pakkages_to_install : list[Pakkage]
            Pakkages to install.
        deptree : DependencyTree
            The resolved dependency tree.
        """

        self.deptree = deptree
        """Resolved dependency tree."""
        self.pakkages_to_install = pakkages_to_install
        """List of pakkages to install."""
        self.package_ids_to_install = set([p.id for p in pakkages_to_install])
        """Set of pakkage ids to install."""

        self.install_tree: nx.DiGraph = deptree.tree.copy()  # type: ignore
        """The directed graph representing the dependency tree only with nodes that needs to be installed."""
        self.install_tree_reverse: nx.DiGraph = deptree.tree_reverse.copy()  # type: ignore
        """The reversed directed graph representing the dependency tree only with nodes that needs to be installed."""

        # Remove all nodes that are not in the pakkages_to_install list
        nodes_to_remove = set()
        for node_id in self.install_tree.nodes:
            if node_id not in self.package_ids_to_install:
                nodes_to_remove.add(node_id)

        for node_id in nodes_to_remove:
            self.install_tree.remove_node(node_id)
            self.install_tree_reverse.remove_node(node_id)

        generations = nx.algorithms.dag.topological_generations(self.install_tree)
        self.sorted_generations: list[list[str]] = [sorted(generation) for generation in generations]
        """List of sorted generations of pakkages to install."""
        self.topological_sorted = [node for generation in self.sorted_generations for node in generation]
        """List of topologically sorted pakkages to install."""

        self.install_nodes: dict[str, InstallNode] = {}
        """Map of install nodes for each pakkage id."""

        for p in pakkages_to_install:
            v = p.versions.target
            if v is None:
                raise ValueError(f"Target version of {p.name} is None")

            # Find the generation of the node
            depth = 0
            for depth, generation in enumerate(self.sorted_generations):
                if p.id in generation:
                    break

            install_node = InstallNode(v, depth)
            self.install_nodes[p.id] = install_node

    @property
    def unfinished_nodes(self):
        """List of unfinished install nodes."""
        for node in self.topological_sorted:
            if not self.install_nodes[node].is_finished:
                yield self.install_nodes[node]

    def children_of_node(self, node: str | InstallNode):
        """Children of the given node."""
        if isinstance(node, InstallNode):
            node_id = node.pakkage_config.id
        else:
            node_id = node

        children = self.install_tree.successors(node_id)
        for child in children:
            if child not in self.package_ids_to_install:
                continue
            yield self.install_nodes[child]

    def parents_of_node(self, node: str | InstallNode):
        """Parents of the given node."""
        if isinstance(node, InstallNode):
            node_id = node.pakkage_config.id
        else:
            node_id = node

        parents = self.install_tree.predecessors(node_id)
        for parent in parents:
            if parent not in self.package_ids_to_install:
                continue
            yield self.install_nodes[parent]

    def unfinished_children_of_node(self, node: str | InstallNode):
        """Children of the given node that are not finished yet."""
        if isinstance(node, InstallNode):
            node_id = node.pakkage_config.id
        else:
            node_id = node

        children = self.children_of_node(node_id)
        for child in children:
            if not child.is_finished:
                yield child

    def __iter__(self):
        for node in self.topological_sorted:
            yield self.install_nodes[node]


class InstallerCombining(Module):
    """
    Installer that combines all defined setup and install classes to install the pakkages.
    """

    def __init__(self, pakkages: PakkageCollection, dependency_tree: DependencyTree):
        """
        Initialize the installer.
        The dependency tree is used to determine the order in which the pakkages are installed.

        Parameters
        ----------
        pakkages: PakkageCollection
            The pakkages collection containing pakkages with target versions to be installed.
        dependency_tree: DependencyTree
            The dependency tree of the pakkages from the Resolver Step.
        """
        super().__init__()

        self.pakkage_collection = pakkages
        self.pakkages = pakkages.pakkages
        self.deptree = dependency_tree

        self.config = MainConfig.get_config()
        self.fetched_dir: str = self.config.paths.fetch_dir.value
        self.all_pakkges_dir: str = self.config.paths.all_pakkages_dir.value

        self.status_callback: Callable[[str], None] | None = None
        self.tasks = None

        self.install_args = InstallArgs.get()

        self.pakkages_to_uninstall: list[Pakkage] = []
        self.pakkages_to_install: list[Pakkage] = []

        self._init_package_assignments()

    def _init_package_assignments(self):
        # Check if pakkages needs to be installed, updated or uninstalled
        pakkages_to_install = []
        pakkages_to_uninstall = []

        for pakkage in self.pakkages.values():
            if pakkage.versions.is_update_candidate():
                pakkages_to_install.append(pakkage)

                if pakkage.versions.target is None:
                    raise ValueError(f"Target version of {pakkage.name} is None")

                if pakkage.versions.installed is None:
                    logger.info(f"Will install {pakkage.id} ({pakkage.versions.target.version})")
                else:
                    if pakkage.versions.reinstall:
                        logger.info(f"Will reinstall {pakkage.id} ({pakkage.versions.installed.version})")
                    else:
                        logger.info(
                            f"Will update {pakkage.name} ({pakkage.versions.installed.version} -> {pakkage.versions.target.version})"
                        )
                    pakkages_to_uninstall.append(pakkage)
            elif pakkage.versions.target is not None:
                if pakkage.versions.reinstall and pakkage.versions.installed is not None:
                    logger.info(f"Will reinstall {pakkage.name} ({pakkage.versions.installed.version})")
                    pakkages_to_uninstall.append(pakkage)
                    pakkages_to_install.append(pakkage)
                else:
                    if pakkage.versions.installed is None:
                        raise ValueError(f"Installed version of {pakkage.name} is None")
                    logger.debug(
                        f"Skipping {pakkage.name} as it is already up to date ({pakkage.versions.installed.version})"
                    )

        self.pakkages_to_uninstall: list[Pakkage] = pakkages_to_uninstall
        self.pakkages_to_install: list[Pakkage] = pakkages_to_install

    def uninstall(self):
        if len(self.pakkages_to_uninstall) > 0:
            Module.print_rule(f"Uninstalling pakkages")
            logger.info(f"Uninstalling {len(self.pakkages_to_uninstall)} packages...")

            for pakkage in self.pakkages_to_uninstall:
                if pakkage.versions.installed is None:
                    raise ValueError(f"Installed version of {pakkage.name} is None")
                v: PakkageConfig = pakkage.versions.installed
                logger.info(f"Uninstalling {v.name} ({v.version})")
                for pakk_type in v.pakk_types:
                    pakk_type.uninstall()

                v.state.install_state = PakkageInstallState.UNINSTALLED
                v.save_state()

                # Move to fetched dir
                if not self.install_args.refetch:
                    new_dir = self.fetched_dir
                    v.move_to(new_dir)
                else:
                    v.delete_directory()

                pakkage.versions.installed = None

    def install(self) -> dict[str, Pakkage]:
        """Install all the packages with the configured setup and installation modules."""

        if len(self.pakkages_to_install) > 0:
            Module.print_rule(f"Installing pakkages")
            logger.info(f"Installing {len(self.pakkages_to_install)} packages...")

            def callback(pakkage_name, info):
                logger.info(f"[cyan]{pakkage_name}[/cyan]: {info}")

            # Move to installed dir and reset failed types
            for pakkage in self.pakkages_to_install:
                v = pakkage.versions.target
                if v is None:
                    raise ValueError(f"Target version of {pakkage.name} is None")

                new_dir = self.all_pakkges_dir
                logger.debug(f"Moving {v.name} to {new_dir}")
                v.move_to(new_dir)

                # Reset failed types
                v.state.failed_types.clear()

            install_graph = InstallGraph(self.pakkages_to_install, self.deptree)

            independent_types: dict[type[TypeBase], list[TypeBase]] = {}
            # Iter all nodes and select types that can be installed independently from dependencies
            for node in install_graph.unfinished_nodes:
                while len(node.types_to_install) > 0:
                    t = node.types_to_install[0]
                    if t.install_type.is_independent:
                        if t.__class__ not in independent_types:
                            independent_types[t.__class__] = []
                        independent_types[t.__class__].append(t)
                        node.types_to_install.remove(t)
                    else:
                        break

            # Execute these installations first
            for type_, type_list in independent_types.items():
                type_.supervised_installation(type_list)

            # After that: while there are still unfinished nodes:
            while len(unfinished_nodes := list(install_graph.unfinished_nodes)) > 0:
                # Select all leaf nodes
                leaf_nodes = [
                    n for n in unfinished_nodes if len(list(install_graph.unfinished_children_of_node(n))) == 0
                ]
                # Get the top bubble of each leaf node
                top_types = [(node, node.types_to_install[0]) for node in leaf_nodes]
                # Sort the top_type installations by priority
                top_types.sort(key=lambda t: t[1].install_type.install_priority, reverse=True)

                # If the top bubble types differ, select the top bubble with the highest install priority
                selected_leaf_nodes: list[InstallNode] = []
                top_type_type = None
                for node, t in top_types:
                    if top_type_type is None:
                        top_type_type = t.__class__
                    if t.__class__ == top_type_type:
                        selected_leaf_nodes.append(node)

                # Install the top types
                if len(selected_leaf_nodes) > 0:
                    leaf_node = selected_leaf_nodes[0]
                    top_type = leaf_node.types_to_install[0]

                    top_types_to_install: list[TypeBase] = []

                    # If selected installation does not allow combination with other installations of the same type on the children:
                    if not top_type.install_type.is_combinable_with_children:
                        # Select and remove the top types from the leaf nodes
                        for node in selected_leaf_nodes:
                            top_types_to_install.append(node.types_to_install.pop(0))

                        for t in top_types_to_install:
                            t.status_callback = callback
                        top_type.supervised_installation(top_types_to_install)
                    # If selected installation allows combination with other installations of the same type on the children:
                    else:
                        i = 0
                        selected_nodes = selected_leaf_nodes.copy()

                        # For each of the selected nodes:
                        #   If the installation type is the last in the node (ignoring TypeGeneric) then:
                        #     -> select all nodes having installations of the same type as next coming installation
                        #        from all child nodes and add them to selected nodes
                        while i < len(selected_nodes):
                            node = selected_nodes[i]
                            if len(node.types_to_install) == 0:
                                continue
                            if node.types_to_install[0].__class__ == top_type.__class__:
                                top_types_to_install.append(node.types_to_install.pop(0))

                            # if len(node.types_to_install) == 1 and node.types_to_install[0].__class__ == TypeGeneric or len(node.types_to_install) == 0:

                            if len(node.types_to_install) == 0 or all(
                                [not t.install_type.has_impact_on_children for t in node.types_to_install]
                            ):
                                parents = list(install_graph.parents_of_node(node))
                                for parent in parents:
                                    if (
                                        len(parent.types_to_install) > 0
                                        and parent.types_to_install[0].__class__ == top_type.__class__
                                    ):
                                        # TODO: It should work without checking if the parent node is already in the list, but maybe add this check later
                                        selected_nodes.append(parent)

                            i += 1

                        for t in top_types_to_install:
                            t.status_callback = callback
                        top_type.supervised_installation(top_types_to_install)

            # Finish the installation by saving the install state
            for pakkage in self.pakkages_to_install:
                if pakkage.versions.target is None:
                    logger.error("This should not happen")
                    continue

                version = pakkage.versions.target
                if len(version.state.failed_types) > 0:
                    logger.error(f"Installation of {version.id} failed.")
                    version.state.install_state = PakkageInstallState.FAILED
                    version.save_state()
                    continue

                pakkage.versions.installed = version
                version.save_state()

                # Set group of the pakkage directory to pakk
                version.set_group("pakk")
                # v.set_group("pakk")

                if version.is_startable() and version.is_enabled():
                    version.enable()

                logger.info(f"Finished installation of {pakkage.name}.")

            Logger.get_console().print("")

        elif len(self.pakkages_to_install) == 0:
            logger.info(f"Everything up to date, no packages to install :)")

        return self.pakkages
