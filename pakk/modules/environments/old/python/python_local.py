from __future__ import annotations

from pakk.modules.environments.base import Environment


class PythonEnvironment(Environment):
    SECTION_NAME = "Env.Python"

    CONFIG_REQUIREMENTS = {
        SECTION_NAME: [
            "python_package_path",
        ]
    }

    def __init__(self):
        super().__init__()

        self.path_python_packages = self.config.get_abs_path(
            "python_package_path", PythonEnvironment.SECTION_NAME, create_dir=True, none_if_val_is="NONE"
        )

    def setup(self):
        """Set the environment up by installing all given dependencies and do other necessary setup steps."""
        cmd = self.get_cmd_pip_install_dependencies()
        self.run_commands_with_output(cmd)

    def install_package(self, path: str, editable=True):
        cmd = self.get_cmd_pip_install_package(path, editable)
        self.run_commands_with_output(cmd)

    def get_cmd_pip_install_dependencies(self):
        """Get the command to install all python dependencies."""
        cmd = super().get_cmd_pip_install_dependencies()
        if cmd is None:
            return cmd
        if self.path_python_packages is not None:
            cmd += " -t {self.path_python_packages}"
        return cmd

    def get_cmd_pip_install_package(self, path: str, editable=True):
        return f"pip install {'-e' if editable else ''} {self.get_path_in_environment(path)}"
