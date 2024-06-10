from __future__ import annotations

import getpass
import os
import tempfile
from typing import TYPE_CHECKING

from pakk import PAKK_CMD_PATH
from pakk.config.main_cfg import MainConfig
from pakk.modules.manager.systemd.unit_file_definition import UnitFileDefinition

if TYPE_CHECKING:
    from pakk.pakkage.core import PakkageConfig


class UnitFileSection:
    def __init__(self, name: str):
        self.name: str = name
        self.lines: list[str] = []

    def add_line(self, option: str, value: str):
        self.lines.append(f"{option}={value}")

    def __str__(self):
        return f"[{self.name}]\n" + "\n".join(self.lines)


class ServiceFile:
    """Generate unit file for systemd"""

    PATH = MainConfig.get_config().paths.services_dir.value

    def __init__(self, name: str):
        name = self.escape_name(name)
        self.name: str = name
        if name.endswith(".service"):
            self.name = name[: -len(".service")]

        self.sections: list[UnitFileSection] = []

    @staticmethod
    def escape_name(name: str) -> str:
        return name.replace("/", "-")

    def add_section(self, name: str) -> UnitFileSection:
        s = UnitFileSection(name)
        self.sections.append(s)
        return s

    def write(self):
        temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        temp_file.write(self.content)
        temp_file.flush()
        temp_file.close()
        temp_file_path = temp_file.name
        os.system(f"cp {temp_file_path} {self.filepath}")
        os.system(f"rm {temp_file_path}")

    @property
    def content(self) -> str:
        return "\n\n".join([str(s) for s in self.sections])

    @property
    def filename(self):
        return f"{self.name}.service"

    @property
    def filepath(self):
        if self.PATH is None:
            raise ValueError("ServiceFile.PATH is None")
        return f"{os.path.join(self.PATH, self.filename)}"

    def __str__(self):
        return self.name


class PakkServiceFileBase:
    def __init__(self, name: str):
        self.service_file = ServiceFile(name)


class PakkParentService(PakkServiceFileBase):
    PATH = os.path.join(ServiceFile.PATH, "/pakk.service") if ServiceFile.PATH is not None else None

    def __init__(self):
        super().__init__("pakk")
        unit_section = self.service_file.add_section(UnitFileDefinition.Unit.NAME)
        unit_section.add_line(UnitFileDefinition.Unit.Description, "Main Pakk Service starting all child services")
        unit_section.add_line(UnitFileDefinition.Unit.After, "pakk-auto-update.service")

        service_section = self.service_file.add_section(UnitFileDefinition.Service.NAME)
        service_section.add_line(UnitFileDefinition.Service.Type.NAME, "oneshot")
        service_section.add_line(UnitFileDefinition.Service.RemainAfterExit, "yes")
        service_section.add_line(UnitFileDefinition.Service.ExecStart, "/bin/true")

        install_section = self.service_file.add_section(UnitFileDefinition.Install.NAME)
        install_section.add_line(UnitFileDefinition.Install.WantedBy, "multi-user.target")


class PakkAutoUpdateService(PakkServiceFileBase):
    PATH = os.path.join(ServiceFile.PATH, "/pakk-auto-update.service") if ServiceFile.PATH is not None else None

    def __init__(self):
        super().__init__("pakk-auto-update")
        unit_section = self.service_file.add_section(UnitFileDefinition.Unit.NAME)
        unit_section.add_line(UnitFileDefinition.Unit.Description, "Pakk Auto Update Service")

        service_section = self.service_file.add_section(UnitFileDefinition.Service.NAME)
        service_section.add_line("User", getpass.getuser())
        service_section.add_line(UnitFileDefinition.Service.Type.NAME, "oneshot")
        service_section.add_line(
            UnitFileDefinition.Service.ExecStart, f"{PAKK_CMD_PATH} update --selfupdate --all --auto"
        )

        install_section = self.service_file.add_section(UnitFileDefinition.Install.NAME)
        install_section.add_line(UnitFileDefinition.Install.WantedBy, "multi-user.target")


class PakkChildService(PakkServiceFileBase):
    def __init__(self, pakkage_version: PakkageConfig):
        self.pakkage_version: PakkageConfig = pakkage_version
        super().__init__(self.pakkage_version.id)

        unit_section = self.service_file.add_section(UnitFileDefinition.Unit.NAME)
        unit_section.add_line(UnitFileDefinition.Unit.Description, f"Pakk service for {self.pakkage_version.name}")
        unit_section.add_line(UnitFileDefinition.Unit.PartOf, "pakk.service")
        unit_section.add_line(UnitFileDefinition.Unit.After, "pakk.service")

        service_section: UnitFileSection = self.service_file.add_section(UnitFileDefinition.Service.NAME)
        service_section.add_line("User", getpass.getuser())
        service_section.add_line(
            # UnitFileDefinition.Service.ExecStart, f"{PAKK_CMD_PATH} run {self.pakkage_version.basename}"
            UnitFileDefinition.Service.ExecStart,
            f"{PAKK_CMD_PATH} run {self.pakkage_version.id}",
        )
        # service_section.add_line(UnitFileDefinition.Service.ExecStart, f"pakk run {self.pakkage_version.basename}")
        service_section.add_line(UnitFileDefinition.Service.Restart, "on-failure")
        service_section.add_line(UnitFileDefinition.Service.TimeoutSec, "15s")
        service_section.add_line(UnitFileDefinition.Service.KillSignal, "SIGINT")

        install_section = self.service_file.add_section(UnitFileDefinition.Install.NAME)
        install_section.add_line(UnitFileDefinition.Install.WantedBy, "pakk.service")
