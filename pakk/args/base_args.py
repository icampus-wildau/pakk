from __future__ import annotations

from typing import TypeVar

BaseArgsType = TypeVar("BaseArgsType", bound="BaseArgs")


class BaseArgs:
    # __config: BaseArgs | None = None
    configs: dict[str, BaseArgs] = {}

    def __init__(self, **kwargs: str | list[str] | bool):
        self.verbose: bool = bool(kwargs.get("verbose", False))
        self.rebuild_base_images: bool = bool(kwargs.get("rebuild_base_images", False))

    @classmethod
    def get(cls: type[BaseArgsType]) -> BaseArgsType:

        if cls.__name__ not in cls.configs:
            cls.configs[cls.__name__] = cls(**PakkArgs.kwargs)

        return cls.configs[cls.__name__]  # type: ignore

    @classmethod
    def set(cls: type[BaseArgsType], **kwargs: str) -> BaseArgsType:
        cls.__config = cls(**kwargs)
        return cls.get()


class PakkArgs:
    kwargs: dict[str, str | bool | list[str]] = {}

    @classmethod
    def init(cls, **kwargs: str | list[str] | bool):
        cls.kwargs = kwargs

    @classmethod
    def update(cls, **kwargs: str | list[str] | bool):
        cls.kwargs.update(kwargs)
