from __future__ import annotations

from typing import TypeVar

BaseConfigType = TypeVar("BaseConfigType", bound="BaseConfig")

class BaseConfig:
    __config: BaseConfig | None = None

    def __init__(self, **kwargs: str):
        self.verbose: bool = bool(kwargs.get("verbose", False))
        self.rebuild_base_images: bool = bool(kwargs.get("rebuild_base_images", False))

        if BaseConfig.__config is None:
            BaseConfig.__config = self

    @classmethod
    def get(cls: type[BaseConfigType], **kwargs) -> BaseConfigType:
        if cls.__config is None:
            cls.__config = cls(**kwargs)
        return cls.__config  # type: ignore[return-value]

    @classmethod
    def set(cls: type[BaseConfigType], **kwargs: dict[str, str]) -> BaseConfigType:
        cls.__config = cls(**kwargs)
        return cls.get()
