from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pakk.modules.connector.base import PakkageCollection
    from pakk.pakkage.core import PakkageConfig


class Process:
    instance = None

    def __init__(self):
        self.env_vars = dict()
        self.temp_env_vars = dict()
        self.temp_env_vars_map: dict[PakkageConfig, dict[str, str]] = dict()

    @classmethod
    def set_from_pakkages(cls, pakkages: PakkageCollection) -> None:
        process = Process.get()

        for p in pakkages.values():
            v = p.versions.installed
            if v is None:
                continue

            process.env_vars.update(v.env_vars)

    @staticmethod
    def get_temp_env_vars(pakkage_config: PakkageConfig) -> dict[str, str]:
        process = Process.get()
        return process.temp_env_vars_map.get(pakkage_config, dict())

    @staticmethod
    def update_temp_env_vars(pakkage_config: PakkageConfig, env_vars: dict[str, str]) -> None:
        process = Process.get()
        # process.temp_env_vars.update(env_vars)
        if pakkage_config not in process.temp_env_vars_map:
            process.temp_env_vars_map[pakkage_config] = dict()
        process.temp_env_vars_map[pakkage_config].update(env_vars)

    @staticmethod
    def clear_temp_env_vars() -> None:
        process = Process.get()
        process.temp_env_vars.clear()

    @classmethod
    def update_env_vars(cls, env_vars: dict[str, str]) -> None:
        process = Process.get()
        process.env_vars.update(env_vars)

    @classmethod
    def get(cls) -> Process:
        if cls.instance is None:
            cls.instance = cls()
        return cls.instance

    @classmethod
    def get_env_vars(cls) -> dict[str, str]:
        process = Process.get()
        return process.env_vars

    @classmethod
    def get_cmd_env_var_setup(cls, use_linebreak=False) -> str:
        process = Process.get()
        cmd = []
        for k, v in process.env_vars.items():
            cmd.append(f"export {k}={v}")
        if use_linebreak:
            return "\n".join(cmd)
        return " && ".join(cmd)
