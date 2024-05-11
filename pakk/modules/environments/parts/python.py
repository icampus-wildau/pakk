from __future__ import annotations

from pakk.modules.module import Module


class EnvPartPython(Module):
    SECTION_NAME = "Env.Python"
    CONFIG_REQUIREMENTS = {SECTION_NAME: ["python_package_path"]}

    def __init__(self):
        super().__init__()
        self.config.require(EnvPartPython.CONFIG_REQUIREMENTS)

        self.path_python_packages = self.config.get_abs_path(
            "python_package_path", EnvPartPython.SECTION_NAME, none_if_val_is="None"
        )

    @staticmethod
    def get_cmd_pip_install_package(path: str, editable=True):
        return f"pip install {'-e' if editable else ''} {path}"
