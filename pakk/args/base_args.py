from __future__ import annotations

from typing import TypeVar

BaseArgsType = TypeVar("BaseArgsType", bound="BaseArgs")


class BaseArgs:
    __config: BaseArgs | None = None

    def __init__(self, **kwargs: str):
        self.verbose: bool = bool(kwargs.get("verbose", False))
        self.rebuild_base_images: bool = bool(kwargs.get("rebuild_base_images", False))

        if BaseArgs.__config is None:
            BaseArgs.__config = self

    @classmethod
    def get(cls: type[BaseArgsType], **kwargs) -> BaseArgsType:
        if cls.__config is None:
            cls.__config = cls(**kwargs)
        return cls.__config  # type: ignore[return-value]

    @classmethod
    def set(cls: type[BaseArgsType], **kwargs: str) -> BaseArgsType:
        cls.__config = cls(**kwargs)
        return cls.get()
