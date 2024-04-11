class ConfigOption():
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

class ConfigSection():
    def __init__(self, name: str, options: list[ConfigOption]):
        self.name = name
        self.options = options

class InitHelperBase():
    @staticmethod
    def help() -> list[ConfigSection]:
        raise NotImplementedError()
