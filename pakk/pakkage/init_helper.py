from __future__ import annotations


class InitConfigOption:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value


class InitConfigSection:
    def __init__(self, name: str, options: list[InitConfigOption]):
        self.name = name
        self.options = options


class InitHelperBase:
    @staticmethod
    def help() -> list[InitConfigSection]:
        raise NotImplementedError()
