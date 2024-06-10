from __future__ import annotations

import os

from pakk.modules.module import Module


class EnvPartROS2(Module):
    SECTION_NAME = "Env.ROS2"
    CONFIG_REQUIREMENTS = {SECTION_NAME: ["ws_dir"]}

    def __init__(self):
        super().__init__()
        self.config.require(EnvPartROS2.CONFIG_REQUIREMENTS)

        self.path_ros_ws = self.config.get_abs_path("ws_dir", EnvPartROS2.SECTION_NAME)
        self.path_ros_ws_src = os.path.join(self.path_ros_ws, "src")

    def get_cmd_setup_ws(self):
        return f". {os.path.join(self.path_ros_ws, 'install', 'setup.bash')}"

    @staticmethod
    def get_cmd_colcon_list_packages(search_path: str, search_recursive: bool = True):
        """Get the colcon command to list all packages in the given path."""
        path_cmd = "--paths" if not search_recursive else "--base-paths"
        # return f'colcon list --names-only --paths {search_path}'
        return f"colcon list --names-only {path_cmd} {search_path}"

    @staticmethod
    def get_cmd_colcon_build(package_names: list[str], symlink_install: bool = False):
        """Get the colcon command to build the given packages."""
        return (
            f'colcon build {"--symlink-install " if symlink_install else ""}--packages-select {" ".join(package_names)}'
        )
