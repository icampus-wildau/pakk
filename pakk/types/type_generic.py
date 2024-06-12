from __future__ import annotations

from typing import TYPE_CHECKING

from pakk.environments.base import Environment
from pakk.pakkage.core import PakkageInstallState
from pakk.types.base import TypeBase

if TYPE_CHECKING:
    from pakk.pakkage.core import PakkageConfig


class TypeGeneric(TypeBase):
    PAKKAGE_TYPE: str = "Generic"
    VISIBLE_TYPE = False
    CONFIGURABLE_TYPE = False
    ALLOWS_MULTIPLE_SIMULTANEOUS_INSTALLATIONS = True

    def __init__(self, pakkage_version: PakkageConfig, env: Environment | None = None):
        super().__init__(pakkage_version, env or Environment())
        self.install_type.has_impact_on_children = False

    @classmethod
    def supports(cls, pakkage_version: PakkageConfig) -> bool:
        """Generic type supports all pakkages."""
        return True

    def install(self) -> None:
        """As final step in the installation, set the state of the pakkage to INSTALLED."""
        self.pakkage_version.state.install_state = PakkageInstallState.INSTALLED

    def uninstall(self) -> None:
        pass
