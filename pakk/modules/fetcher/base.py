from __future__ import annotations

from pakk.modules.module import Module
from pakk.pakkage.core import Pakkage


class Fetcher(Module):
    def __init__(self, pakkages: dict[str, Pakkage], config_requirements: dict[str, list[str]] | None = None):
        super().__init__(config_requirements)
        self.pakkages = pakkages

    def fetch(self) -> dict[str, Pakkage]:
        """Fetch all the packages with the implemented fetcher."""
        raise NotImplementedError()
