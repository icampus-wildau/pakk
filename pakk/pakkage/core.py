from __future__ import annotations

import configparser
import enum
import io
import json
import logging
import os
import re
import shutil
import subprocess
from typing import TYPE_CHECKING
from typing import Any
from typing import Type

import dotenv
import jsons
from extended_configparser.parser import ExtendedConfigParser
from semver.version import Version

from pakk.args.manager_args import ManagerArgs
from pakk.config.main_cfg import MainConfig
from pakk.helper.file_util import remove_dir
from pakk.modules.environments.loader import get_current_environment_cls
from pakk.modules.manager.systemd.unit_generator import PakkChildService
from pakk.modules.types.base import TypeBase
from pakk.modules.types.base import TypeConfigSection

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pakk.modules.connector.base import Connector
    from pakk.modules.environments.base import EnvironmentBase


class PakkageInstallState(enum.Enum):
    """The installation state of a pakkage."""

    INSTALLED = "installed"
    UNINSTALLED = "uninstalled"
    FETCHED = "fetched"
    DISCOVERED = "discovered"
    FAILED = "failed"


class PakkageState:
    """The state of a pakkage, including the installation state, the autostart and the running state."""

    DIRECTORY_NAME = ".pakk"
    JSON_FILE_NAME = "state.json"

    def __init__(self, install_state: PakkageInstallState = PakkageInstallState.DISCOVERED):
        self.install_state: PakkageInstallState = install_state
        self.auto_start_enabled: bool = False
        self.running: bool = False
        self.failed_types: list[str] = list()

    def copy_from(self, other: PakkageState | PakkageConfig | None):
        if other is None:
            return

        if isinstance(other, PakkageConfig):
            other = other.state

        """Copy the state from another PakkageState object."""
        # self.install_state = other.install_state
        self.auto_start_enabled = other.auto_start_enabled
        self.running = other.running


class CompactPakkageConfig:
    def __init__(self):
        self.cfg_sections: list[str] = list()
        """The sections of the pakkage config."""
        self.options: dict[str, dict[str, str]] = dict()
        """The options of the pakkage config."""

        self.id: str = ""
        """The ID of the pakkage. E.g. ros2-motors"""
        self.version: str = ""
        """The version of the pakkage. E.g. 0.1.0"""
        self.name: str = ""
        """The name of the pakkage. E.g. ROS2 Motors"""
        self.description: str = ""
        """The description of the pakkage. E.g. A pakkage for controlling motors."""
        self.author: str = ""
        """The author of the pakkage."""
        self.keywords: list[str] = list()
        """The keywords of the pakkage. E.g. ['ros2', 'motors']"""
        self.license: str = ""
        """The license of the pakkage. E.g. MIT"""

        self.dependencies: dict[str, str] = dict()
        """The dependencies of the pakkage. E.g. {"ros2": "0.1.0"}"""

        # self.attributes: dict[str, Any] = dict()
        # """Custom attributes for following modules."""

        self.connector_attributes: dict[Type[Connector], ConnectorAttributes] = dict()
        """Custom connector attributes stored during discovery process."""

    @staticmethod
    def from_pakkage_config(config: PakkageConfig) -> CompactPakkageConfig:
        cpc = CompactPakkageConfig()
        cpc.cfg_sections = config.cfg_sections

        for section in config.cfg_sections:
            cpc.options[section] = dict()
            for key, value in config.cfg.items(section, raw=True):
                cpc.options[section][key] = value

        cpc.id = config.id
        cpc.version = config.version
        cpc.name = config.name
        cpc.description = config.description
        cpc.author = config.author
        cpc.keywords = config.keywords
        cpc.license = config.license
        cpc.dependencies = config.dependencies
        cpc.connector_attributes = config.connector_attributes

        return cpc


class PakkageConfig:
    """
    The configuration of a pakkage, defined in the pakk.json / pakk.cfg / etc.
    Since a pakkage itself can have multiple versions, a pakkage config also represents a single installable version.
    Thus, the pakkage config also includes a state, which does not come from the pakk.x file, but from the installation process.
    """

    PAKK_DIRECTORY_NAME = ".pakk"
    """The name of the hidden directory in which additional local pakkage like the state is stored."""

    ENV_FILE_NAME = "pakk.env"

    def __init__(self, state: PakkageState | None = None):
        # self._cfg = configparser.ConfigParser(interpolation=EnvInterpolation(allow_uninterpolated_values=True), allow_no_value=True)
        self._cfg = configparser.ConfigParser(interpolation=configparser.Interpolation(), allow_no_value=True)
        self._cfg.optionxform = str  # type: ignore
        """The configparser object, which is used to store the pakk.cfg data."""
        self.cfg_sections: list[str] = list()
        """The sections of the pakkage config."""

        self.id: str = ""
        """The ID of the pakkage. E.g. ros2-motors"""
        self.version: str = ""
        """The version of the pakkage. E.g. 0.1.0"""
        self.name: str = ""
        """The name of the pakkage. E.g. ROS2 Motors"""
        self.description: str = ""
        """The description of the pakkage. E.g. A pakkage for controlling motors."""
        self.author: str = ""
        """The author of the pakkage."""
        self.keywords: list[str] = list()
        """The keywords of the pakkage. E.g. ['ros2', 'motors']"""
        self.license: str = ""
        """The license of the pakkage. E.g. MIT"""

        self.dependencies: dict[str, str] = dict()
        """The dependencies of the pakkage. E.g. {"ros2": "0.1.0"}"""

        self.local_path: str | None = None

        self.state: PakkageState = state or PakkageState()
        """The state of the pakkage, including the installation state, the autostart and the running state."""

        # self.attributes: dict[str, Any] = dict()
        # """Custom attributes for following modules."""

        self.connector_attributes: dict[str, ConnectorAttributes] = dict()
        """Custom connector attributes stored during discovery process."""

        self._types: list[TypeBase] | None = None
        """The types of the pakkage. E.g. ["ros2", "python"]"""

        self._environments: dict[type[EnvironmentBase], EnvironmentBase] = dict()
        """The stored environments of the pakkage. Used to use the same environment for multiple types."""

    def set_attributes(self, connector: Connector, attributes: ConnectorAttributes):
        self.connector_attributes[connector.connector_attributes_key] = attributes

    def get_attributes(self, connector: Connector) -> ConnectorAttributes | None:
        return self.connector_attributes.get(connector.connector_attributes_key, None)

    @staticmethod
    def from_compact_pakkage_config(compact: CompactPakkageConfig) -> PakkageConfig:
        pc = PakkageConfig()
        pc.cfg_sections = compact.cfg_sections

        for section in compact.cfg_sections:
            pc._cfg.add_section(section)
            for key, value in compact.options[section].items():
                pc._cfg.set(section, key, value)

        pc.id = compact.id
        pc.version = compact.version
        pc.name = compact.name
        pc.description = compact.description
        pc.author = compact.author
        pc.keywords = compact.keywords
        pc.license = compact.license
        pc.dependencies = compact.dependencies
        pc.connector_attributes = compact.connector_attributes
        return pc

    @property
    def cfg(self):
        """The configparser object, which is used to store the pakk.cfg data."""
        return self._cfg

    @property
    def basename(self):
        """The name of the directory in which the pakkage is stored."""
        return f"{self.id}@{self.version}".replace("/", "_")

    def is_startable(self) -> bool:
        """Returns true if the pakkage is startable."""
        if self.state.install_state != PakkageInstallState.INSTALLED:
            return False

        startable_types = [t for t in self.pakk_types if t.is_runnable()]
        if len(startable_types) == 0:
            return False

        if len(startable_types) > 1:
            raise Exception("Multiple startable types are not supported yet.")

        return True

    def _run_command_with_return_code_and_output(self, cmd: str) -> tuple[int, str]:
        """Run a command and return the return code and the output."""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return_code = result.returncode
        output = result.stdout.strip()
        return return_code, output

    def run(self):
        """Runs the pakkage interactively."""
        if not self.is_startable():
            raise Exception("Pakkage is not runnable.")

        startable_types = [t for t in self.pakk_types if t.is_runnable()]
        startable_types[0].run()

    def start(self):
        """Starts the pakkage as service."""
        if not self.is_startable():
            raise Exception("Pakkage is not startable.")

        service = PakkChildService(self)
        reload_service_files = ManagerArgs.get().reload_service_files
        if reload_service_files or not os.path.exists(f"/etc/systemd/system/{service.service_file.filename}"):
            logger.info(f"Writing service file to {service.service_file.filepath}")
            service.service_file.write()
            logger.info(f"Linking service file to /etc/systemd/system/{service.service_file.filename}")
            os.system(
                f"sudo ln -sf {service.service_file.filepath} {os.path.join('/etc/systemd/system', service.service_file.filename)}"
            )
            logger.info(f"Reloading systemd daemon")
            os.system(f"sudo systemctl daemon-reload")

        logger.info(f"Starting {service.service_file.name}")
        # os.system(f"sudo systemctl enable {service.service_file.filepath}")
        os.system(f"sudo systemctl start {service.service_file.name}")

    def stop(self):
        """Stops the pakkage service."""
        if not self.is_startable():
            raise Exception("Pakkage is not startable.")

        service = PakkChildService(self)
        logger.info(f"Stopping {service.service_file.name}")
        os.system(f"sudo systemctl stop {service.service_file.name}")

    def follow_log(self):
        """Follows the log of the pakkage service."""
        if not self.is_startable():
            raise Exception(f"Pakkage {self.id} is not startable.")

        service = PakkChildService(self)
        follow = ManagerArgs.get().follow_logs
        logger.info(f"Following log of {service.service_file.name}")
        # os.system(f"sudo journalctl -f -u {service.service_file.name}")
        if follow:
            cmd = f"journalctl -fu {service.service_file.name}"
        else:
            cmd = f"journalctl -ru {service.service_file.name}"
        os.system(cmd)

    def is_active(self) -> bool:
        """Returns true if the pakkage service is active."""
        if not self.is_startable():
            raise Exception(f"Pakkage {self.id} is not startable.")

        service = PakkChildService(self)
        code, output = self._run_command_with_return_code_and_output(
            f"sudo systemctl is-active {service.service_file.name}"
        )
        return code == 0

    def is_enabled(self) -> bool:
        """Returns true if the pakkage service is enabled."""
        if not self.is_startable():
            raise Exception(f"Pakkage {self.id} is not startable.")

        service = PakkChildService(self)
        code, output = self._run_command_with_return_code_and_output(
            f"sudo systemctl is-enabled {service.service_file.name}"
        )
        return code == 0

    def enable(self):
        """Enables the autostart of the pakkage as service."""
        if not self.is_startable():
            raise Exception(f"Pakkage {self.id} is not startable.")

        service = PakkChildService(self)
        logger.info(f"Writing service file to {service.service_file.filepath}")
        service.service_file.write()

        logger.info(f"Enabling {service.service_file.name}")
        os.system(f"sudo systemctl enable {service.service_file.filepath}")
        logger.info(f"Starting {service.service_file.name}")
        os.system(f"sudo systemctl start {service.service_file.name}")

    def disable(self):
        """Disables the autostart of the pakkage service."""
        if not self.is_startable():
            raise Exception("Pakkage is not startable.")

        service = PakkChildService(self)
        logger.info(f"Stopping {service.service_file.name}")
        os.system(f"sudo systemctl stop {service.service_file.name}")
        logger.info(f"Disabling {service.service_file.name}")
        os.system(f"sudo systemctl disable {service.service_file.name}")

    def restart(self):
        """Restarts the pakkage service."""
        if not self.is_startable():
            raise Exception("Pakkage is not startable.")

        service = PakkChildService(self)
        logger.info(f"Restarting {service.service_file.name}...")
        os.system(f"sudo systemctl restart {service.service_file.name}")
        logger.info(f"... {service.service_file.name} restarted")

    @property
    def pakk_types(self) -> list[TypeBase]:
        """Returns the types of the pakkage. Depending on the types that are defined in the config."""
        if self._types is not None and len(self._types) > 0:
            return self._types

        type_classes = TypeBase.get_type_classes()
        self._types = list()
        added_types: set[type] = set()

        # Get all type names from the config sections
        section_names = self.cfg_sections
        type_names = [re.split(TypeConfigSection.TYPE_DELIMITER, section)[0] for section in section_names]
        # Delete duplicates
        type_names: list[str] = list(dict.fromkeys(type_names))

        # Append all types according to the type names defined in the config
        for type_name in type_names:
            type_class = next((t for t in type_classes if t.supports_section(type_name)), None)
            if type_class is None:
                if type_name[0].isupper():
                    logger.warning(f"Type {type_name} @ cfg of {self.id} is not supported.")
                continue

            self._types.append(type_class(self, self.get_environment()))
            added_types.add(type_class)

        # Check if there are types that are not defined by the sections in the config but still support the pakkage
        for type_class in type_classes:
            if type_class not in added_types and type_class.supports(self):
                self._types.append(type_class(self, self.get_environment()))
                added_types.add(type_class)

        self._types = [t for t in self._types if t is not None]

        return self._types

    @property
    def pakk_type_names(self) -> list[str]:
        """Returns the names of the types of the pakkage. Depending on the types that are defined in the config."""
        return [t.PAKKAGE_TYPE for t in self.pakk_types if t.PAKKAGE_TYPE is not None]

    @property
    def env_vars(self) -> dict[str, str | None]:
        """Returns the env vars of the pakkage."""

        """Load the env vars of the pakkage from the pakk.env file in the .pakk directory of the module."""
        if self.local_path is None:
            raise Exception("No path to load the env vars from.")
        path = self.local_path

        env_vars = dict()

        pakk_dir = PakkageConfig.PAKK_DIRECTORY_NAME
        env_file = PakkageConfig.ENV_FILE_NAME

        env_file_path = os.path.join(path, pakk_dir, env_file)

        if not os.path.exists(env_file_path):
            return env_vars

        env_vars = dotenv.dotenv_values(env_file_path)
        return env_vars

    def save_env_vars(self, env_vars: dict[str, str]):
        """Save the env vars of the pakkage to the pakk.env file in the .pakk directory of the module."""

        if self.local_path is None:
            raise Exception("No path to save the env vars to.")
        path = self.local_path

        pakk_dir = PakkageConfig.PAKK_DIRECTORY_NAME
        env_file = PakkageConfig.ENV_FILE_NAME

        env_file_path = os.path.join(path, pakk_dir, env_file)

        with open(env_file_path, "w") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

    def load_state(self, path: str | None = None, ignore_if_not_exists: bool = True):
        """Load the state of the pakkage from the state.json file in the .pakk directory of the module."""

        if path is None:
            if self.local_path is None:
                raise Exception(
                    "No path to load the state from. Provide explicitly or use fetcher that stores ATTR_LOCAL_PATH in the attributes."
                )
            path = self.local_path

        pakk_dir = PakkageState.DIRECTORY_NAME
        state_file = PakkageState.JSON_FILE_NAME

        state_path = os.path.join(path, pakk_dir, state_file)

        if not os.path.exists(state_path):
            if ignore_if_not_exists:
                return
            raise Exception(f"State file does not exist: {state_path}")

        with open(state_path, "r") as f:
            dat = f.read()
            try:
                self.state = jsons.loads(dat, PakkageState)
            except Exception:
                logger.warning(f"Pakkage state from {state_path} could not be loaded.")
                self.state = PakkageState()

    def save_state(self, path: str | None = None):
        """Save the state of the pakkage to the state.json file in the .pakk directory of the module."""

        if path is None:
            if self.local_path is None:
                raise Exception(
                    "No path to save the state to. Provide explicitly or use fetcher that stores ATTR_LOCAL_PATH in the attributes."
                )
            path = self.local_path

        pakk_dir = PakkageState.DIRECTORY_NAME
        state_file = PakkageState.JSON_FILE_NAME
        gitignore = ".gitignore"
        os.makedirs(os.path.join(path, pakk_dir), exist_ok=True)

        # state file
        with open(os.path.join(path, pakk_dir, state_file), "w") as f:
            dat = jsons.dumps(self.state)
            f.write(dat)

        # gitignore to completely ignore the .pakk directory
        with open(os.path.join(path, pakk_dir, gitignore), "w") as f:
            dat = "**"
            f.write(dat)

    def move_to(self, directory: str):
        """
        Move the pakkage to a new directory.

        Parameters
        ----------
        directory: str
            The directory to move the pakkage to.
        """

        if not os.path.basename(directory) == self.basename:
            directory = os.path.join(directory, self.basename)

        current_path = self.local_path
        if current_path is None:
            raise Exception("No path to move from.")

        if current_path == directory:
            return

        if not os.path.exists(current_path):
            raise Exception(f"Path to move from does not exist: {current_path}")

        if os.path.exists(directory):
            remove_dir(directory)

        # Copy the pakkage to the new path
        shutil.move(current_path, directory)

        # self.local_path = os.path.join(directory)
        self.local_path = directory

    def set_group(self, group: str, recursive: bool = True):
        """Set the group of the pakkage."""
        if self.local_path is None:
            raise Exception("No path to set the group of.")

        if not os.path.exists(self.local_path):
            raise Exception(f"Path to set the group of does not exist: {self.local_path}")

        # TODO: only viable for linux
        if recursive:
            # Set group
            os.system(f"chgrp -R {group} {self.local_path}")
            # Set permission for group
            os.system(f"chmod -R g+rwx {self.local_path}")
        else:
            os.system(f"chgrp {group} {self.local_path}")
            os.system(f"chmod g+rwx {self.local_path}")

        # shutil.chown(self.local_path, group=group)

    def delete_directory(self):
        """Delete the directory of the pakkage."""
        if self.local_path is None:
            raise Exception("No path to delete.")

        if not os.path.exists(self.local_path):
            raise Exception(f"Path to delete does not exist: {self.local_path}")

        remove_dir(self.local_path)

    def path_in_pakkage(self, path: str) -> str:
        """Get the path in the pakkage."""
        if self.local_path is None:
            raise Exception("No path to get the path in the pakkage from.")

        return os.path.abspath(os.path.join(self.local_path, path))

    def __str__(self):
        return f"{self.id}@{self.version} ({len(self.dependencies)} deps)"

    @staticmethod
    def from_string(cfg_string: str) -> PakkageConfig:
        """
        Create a PakkageConfig object from a string.
        This method assumes a cfg format.
        """

        io_file = io.StringIO(cfg_string)
        return PakkageConfig.from_cfg_file(io_file)

    @staticmethod
    def from_json(jsond: dict) -> PakkageConfig:
        """
        Create a PakkageConfig object from a json object.
        This method try to maintain compatibility with the old module.rose.json format.
        """
        logger.warning("PakkageConfig.from_json() is deprecated. Use cfg format instead.")

        pc = PakkageConfig()

        dependencies = jsond.get("dependencies", dict())
        new_deps = dict()
        # Old format for dependencies was a list of objects with id and version entries.
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if "id" in dependency and "version" in dependency:
                    new_deps[dependency["id"]] = dependency["version"]
        # New format for dependencies is a dictionary of (id, version) pairs.
        elif isinstance(dependencies, dict):
            new_deps = dependencies

        jsond["dependencies"] = new_deps

        assets = jsond.get("assets", dict())
        new_assets = dict()
        # Old format for assets was a list of objects with name and path entries.
        if isinstance(assets, list):
            for asset in assets:
                if "name" in asset and "path" in asset:
                    new_assets[asset["name"]] = asset["path"]
        # New format for assets is a dictionary of (name, path) pairs.
        elif isinstance(assets, dict):
            new_assets = assets

        jsond["assets"] = new_assets

        def insert_to_cfg(d: dict, section_base=""):
            """Insert the json object into the config."""

            for k, v in d.items():
                if isinstance(v, dict):
                    insert_to_cfg(v, section_base + ("." if len(section_base) > 0 else "") + k)
                elif isinstance(v, list):
                    pc.cfg[section_base][k] = ",".join(v)
                else:
                    b = section_base
                    if b == "":
                        b = "info"

                    if not pc.cfg.has_section(b):
                        pc.cfg.add_section(b)

                    pc.cfg.set(b, k, str(v))

        insert_to_cfg(jsond)

        if pc.cfg.get("info", "version").startswith("v"):
            pc.cfg.set("info", "version", pc.cfg.get("info", "version")[1:])

        pc.id = pc.cfg["info"]["id"]
        pc.version = pc.cfg["info"]["version"]
        pc.dependencies = (
            {k: v for k, v in pc.cfg.items("dependencies")} if pc.cfg.has_section("dependencies") else dict()
        )

        if "name" in pc.cfg["info"]:
            pc.name = pc.cfg["info"]["name"]
        elif "title" in pc.cfg["info"]:
            pc.name = pc.cfg["info"]["title"]
        else:
            pc.name = pc.id

        pc.description = pc.cfg["info"]["description"] if "description" in pc.cfg["info"] else ""
        pc.keywords = (
            [kw.strip() for kw in pc.cfg["info"]["keywords"].split(",") if kw.strip() != ""]
            if "keywords" in pc.cfg["info"]
            else []
        )
        pc.author = pc.cfg["info"]["author"] if "author" in pc.cfg["info"] else ""
        pc.license = pc.cfg["info"]["license"] if "license" in pc.cfg["info"] else ""

        return pc

    @staticmethod
    def from_cfg_file(cfg_path: str | io.StringIO) -> "PakkageConfig":
        """
        Create a PakkageConfig object from a configparser object.
        """

        pc = PakkageConfig()
        if isinstance(cfg_path, io.StringIO):
            pc.cfg.read_file(cfg_path)
        else:
            pc.cfg.read(cfg_path)
        pc.cfg_sections = pc.cfg.sections()

        cfg = pc.cfg
        pc.id = cfg.get("info", "id", fallback="")
        pc.version = cfg.get("info", "version", fallback="")

        pc.name = cfg.get("info", "title", fallback="")
        if pc.name == "":
            pc.name = cfg.get("info", "name", fallback=pc.id)

        pc.description = cfg.get("info", "description", fallback="")
        pc.author = cfg.get("info", "author", fallback="")
        pc.license = cfg.get("info", "license", fallback="")
        pc.keywords = ExtendedConfigParser.split_to_list(cfg.get("info", "keywords", fallback=""))

        if cfg.has_section("dependencies"):
            pc.dependencies = dict()
            for d_id, d_version in cfg.items("dependencies"):
                pc.dependencies[d_id] = d_version

        # TODO: Test this
        # TODO: Implement configparser here to allow interpolation
        # pc.attributes = cfg.__dict__

        return pc

    @staticmethod
    def from_file(file_path: str) -> PakkageConfig | None:
        if file_path.endswith(".json"):
            jsond = jsons.load(json.load(open(file_path, "r")))
            return PakkageConfig.from_json(jsond)

        if file_path.endswith(".cfg"):
            return PakkageConfig.from_cfg_file(file_path)

        return None

    @staticmethod
    def from_directory(abs_path: str) -> PakkageConfig | None:
        pakk_files = MainConfig.get_config().pakk_cfg_files

        # Check if the directory contains a pakkage file
        for _, _, files in os.walk(abs_path):
            for f in files:
                if f in pakk_files:
                    c = PakkageConfig.from_file(str(os.path.join(abs_path, f)))
                    if c is None:
                        return None
                    c.local_path = abs_path
                    c.load_state()
                    return c
            break

        return None

    def get_environment(self) -> EnvironmentBase:
        """
        Get the environment for this pakkage.
        """

        env_cls = get_current_environment_cls()
        if env_cls not in self._environments:
            self._environments[env_cls] = env_cls()

        return self._environments[env_cls]

    def __lt__(self, other: PakkageConfig):
        return self.id < other.id


class PakkageVersions:
    def __init__(
        self,
        available: list[PakkageConfig] | dict[str, PakkageConfig] | None = None,
        installed: PakkageConfig | None = None,
        target: PakkageConfig | None = None,
    ):
        if isinstance(available, list):
            self.available: dict[str, PakkageConfig] = dict()
            for pakkage_config in available:
                pakkage_config: PakkageConfig
                self.available[pakkage_config.version] = pakkage_config
        else:
            self.available: dict[str, PakkageConfig] = available or dict()

        self.installed: PakkageConfig | None = installed
        """Installed version of the pakkage."""

        self.target: PakkageConfig | None = target
        """Current target version for the pakkaage."""

        self.reinstall = False
        """True if the pakkage should be reinstalled."""

        self.target_fixed: bool = False
        """True if the target is fixed during the resolving process."""

        self.target_explicitly_given: bool = False
        """True if the target version was explicitly given by the user."""

        self.resolved: bool = False
        """True if the pakkage has been resolved during the resolving process."""

        self.is_repairing_install: bool = False
        """
        True if the pakkage installation is a fix for a missing pakkage as dependency of an installed pakkage.
        """

    def is_installed(self) -> bool:
        """Returns true if the pakkage is installed."""
        return self.installed is not None

    def is_update_candidate(self, only_newer_versions=False, on_reinstall=True) -> bool:
        """
        Returns true if the pakkage is an update candidate.
        If only_newer_versions is true, this is the case if the pakkage has a target version newer than the installed version.
        Otherwise, this is the case if the pakkage has a target version different from the installed version.
        """

        if self.target is None:
            return False

        if self.installed is None:
            return True

        if self.reinstall and on_reinstall:
            return True

        if only_newer_versions:
            return Version.parse(self.installed.version).compare(self.target.version) < 0
            # return 1.compare(self.installed.version, self.target.version) < 0

        return self.installed.version != self.target.version

    def __str__(self):
        return f"available: {self.available}, installed: {self.installed}, target: {self.target}"


class ConnectorAttributes:
    def __init__(self):

        self.url: str | None = None
        self.branch: str | None = None
        self.commit: str | None = None


class Pakkage:
    def __init__(self, pakkage_versions: PakkageVersions | None = None):
        self.versions: PakkageVersions = pakkage_versions or PakkageVersions()
        """The versions of the pakkage. This includes the available versions,
        the installed version and the target version for new installations and updated."""

        info_version = None
        if self.versions.installed:
            info_version = self.versions.installed
        elif self.versions.target:
            info_version = self.versions.target
        elif len(self.versions.available) > 0:
            info_version = list(self.versions.available.values())[0]

        self.id: str = "" if info_version is None else info_version.id
        """The id of the pakkage. This is used to identify the pakkages in the CLI commands
         and the same as the id in the pakkage config file."""

        self.name: str = "" if info_version is None else info_version.name
        """The name of the pakkage."""

        self.description: str = "" if info_version is None else info_version.description
        """If available, the description of the pakkage."""

        # self.attributes: dict[str, Any] = dict()
        # """Custom attributes for following modules."""

        # self.connector_attributes: dict[Type[Connector], ConnectorAttributes] = dict()
        # """Custom connector attributes stored during discovery process."""

    def __str__(self):
        s = f"{self.id} @ {self.versions.installed.version if self.versions.installed else 'None'}"
        if (
            self.versions.installed is not None
            and self.versions.installed.state.install_state == PakkageInstallState.FAILED
        ):
            s += " ([red]failed[/red])"
        if self.versions.target and self.versions.target != self.versions.installed:
            s += f" -> {self.versions.target.version}"
            if self.versions.is_repairing_install:
                s += " (repairing)"
        if self.versions.target_fixed:
            s += " (fixed)"

        return s

    def __repr__(self):
        return self.__str__()
