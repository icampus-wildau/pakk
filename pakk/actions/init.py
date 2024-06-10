from __future__ import annotations

import configparser
import io
import logging
import os
import re
from typing import TYPE_CHECKING

import semver
from InquirerPy import inquirer
from InquirerPy.validator import Validator
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion
from prompt_toolkit.validation import ValidationError

from pakk.args.base_args import BaseArgs
from pakk.helper.loader import PakkLoader
from pakk.logger import Logger
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.local import LocalConnector
from pakk.modules.module import Module
from pakk.modules.types.base import TypeBase
from pakk.pakkage.init_helper import InitConfigOption
from pakk.pakkage.init_helper import InitConfigSection
from pakk.pakkage.init_helper import InitHelperBase

# pyright: reportPrivateImportUsage=false


# from git import Repo


if TYPE_CHECKING:
    from prompt_toolkit.document import Document

    from pakk.pakkage.core import Pakkage
    from pakk.pakkage.core import PakkageConfig

logger = logging.getLogger(__name__)


class IdValidator(Validator):
    def validate(self, document: Document):
        val = document.text
        pos = document.cursor_position
        if len(val) == 0:
            raise ValidationError(pos, "ID cannot be empty")

        # Check if value contains uppercase letters
        if any(c.isupper() for c in val):
            raise ValidationError(pos, "ID must be lowercase")

        # Check if value contains spaces
        if any(c.isspace() for c in val):
            raise ValidationError(pos, "ID must not contain spaces")

        # Check if value contains special characters
        if any(c in "!@#$%^&*()[]{};:,./<>?\|`~=+" for c in val):
            raise ValidationError(pos, "ID must not contain special characters")

        if any(c == "_" for c in val):
            raise ValidationError(pos, "ID should use `-` instead of underscores")

        return True


class VersionValidator(Validator):
    def validate(self, document: Document):
        val = document.text
        pos = document.cursor_position
        try:
            semver.VersionInfo.parse(val)
        except ValueError:
            raise ValidationError(pos, "Invalid version")

        return True


class DependencyCompleter(Completer):
    def __init__(self, packages: dict[str, Pakkage]):
        self.packages = packages
        self.ids = [pakkage.id for pakkage in packages.values()]

    @staticmethod
    def split_depedencies(line: str) -> list[str]:
        splits = re.split(r"[\s,]+", line)
        splits = [s.strip() for s in splits if s.strip() != ""]
        return splits

    def get_completions(self, document: Document, complete_event: CompleteEvent):

        # word = document.get_word_before_cursor()
        if document.current_line_before_cursor.endswith(" "):
            return

        # Split by spaces and commas
        splits = DependencyCompleter.split_depedencies(document.current_line_before_cursor)

        if len(splits) > 0:
            current_prefix = splits[-1]
            for id in self.ids:
                if current_prefix in id:
                    p = self.packages[id]
                    v = self.packages[id].versions.installed or (
                        list(self.packages[id].versions.available.values())[-1]
                        if len(self.packages[id].versions.available) > 0
                        else None
                    )
                    if v is not None:
                        v = v.version
                    else:
                        v = "0.0.0"

                    v = "^" + v
                    # ver = semver.VersionInfo.parse(v)

                    id_with_version = f"{id}={v}"
                    yield Completion(
                        text=id_with_version,
                        start_position=-len(current_prefix),
                    )


def init(path: str, **kwargs: str):
    base_config = BaseArgs.get()
    flag_verbose = kwargs.get("verbose", False)

    if path is None or len(path) == 0:
        # Get current working directory
        path = os.getcwd()

    logger.info(f"Initializing pakkage in {path}")

    # Check if path is a directory
    if not os.path.isdir(path):
        logger.error(f"{path} is not a directory")
        return

    # Check if path is a git repository
    if not os.path.isdir(os.path.join(path, ".git")):
        logger.warn(f"{path} is not a git repository")
        # return
    # repo = Repo(path)
    # if not repo.bare:
    #     logger.warning(f"{path} is already a git repository")

    # Check if there is already a pakk.cfg file
    if os.path.isfile(os.path.join(path, "pakk.cfg")):
        logger.warning(f"{path} already has a pakk.cfg file")
        proceed = inquirer.confirm("Overwrite pakk.cfg", default=False).execute()
        if not proceed:
            logger.info("Aborting")
            return

    cfg_sections: list[InitConfigSection] = []

    basename = os.path.basename(path)

    pid = inquirer.text(
        "Pakkage ID:",
        validate=IdValidator(),
        long_instruction="The unique id to identify your pakkage",
        default=basename,
    ).execute()
    ptitle = inquirer.text("Title:", default=pid, long_instruction="The verbose title of your pakkage").execute()
    pver = inquirer.text(
        "Current version:",
        validate=VersionValidator(),
        default="0.0.1",
        long_instruction="Current semnatic version of your pakkage",
    ).execute()
    pdescription = inquirer.text("Description:", long_instruction="A short description of your pakkage").execute()
    pkeywords = inquirer.text("Keywords:", long_instruction="A comma separated list of keywords").execute()

    cfg_sections.append(
        InitConfigSection(
            "info",
            [
                InitConfigOption("id", pid),
                InitConfigOption("version", pver),
                InitConfigOption("title", ptitle),
                InitConfigOption("description", pdescription),
                InitConfigOption("keywords", pkeywords),
            ],
        )
    )

    pakkages = PakkageCollection()
    pakkages.discover([LocalConnector()], quiet=not flag_verbose)

    dep_confirmed = False
    dependencies = []
    while not dep_confirmed:
        dependencies_str = inquirer.text(
            message="Dependencies:",
            long_instruction="A comma separated list of dependencies (pakkage IDs)",
            completer=DependencyCompleter(pakkages.pakkages),
            qmark=">",
        ).execute()

        dependencies = DependencyCompleter.split_depedencies(dependencies_str)
        conf_msg = "Proceed with these dependencies:\n" + str(dependencies)
        if len(dependencies) == 0:
            conf_msg = "No dependencies selected. Proceed?"
        dep_confirmed = inquirer.confirm(conf_msg, default=True).execute()

    if dependencies and len(dependencies) > 0:
        options = []
        for d in dependencies:
            splits = [s.strip() for s in d.split("=") if len(s.strip()) > 0]
            if len(splits) == 2:
                options.append(InitConfigOption(splits[0], splits[1]))
            else:
                options.append(InitConfigOption(d, ">=0.0.0"))
        cfg_sections.append(InitConfigSection("dependencies", options))

    TypeBase.initialize()
    types = TypeBase.get_type_classes()
    type_map = {t.PAKKAGE_TYPE: t for t in types}
    available_type_choices = [t.PAKKAGE_TYPE for t in types if t.CONFIGURABLE_TYPE]
    while True:
        type_choices = inquirer.checkbox(
            message="Select pakkage types (select with TAB, proceed with ENTER)",
            choices=available_type_choices,
            cycle=True,
        ).execute()
        if len(type_choices) > 0:
            break
        if inquirer.confirm("No pakkage types selected. Proceed?", default=False).execute():
            break

    for choice in type_choices:
        logger.info(f"### Adding pakkage type '{choice}' ###")
        c = type_map[choice]
        # Get module name
        module_name = c.__module__
        # Try to get InitHelper class from the module
        # helper_cls = ModuleImporter.get_class_from_module(module_name, "InitHelper")
        helper_cls = PakkLoader.get_module_subclasses(module_name, InitHelperBase)
        helper_cls = helper_cls[0] if len(helper_cls) > 0 else None
        if helper_cls is None:
            logger.warning(f"Could not find InitHelper class in {module_name}")
            cfg_sections.append(InitConfigSection(c.PAKKAGE_TYPE, []))
            continue
        if not issubclass(helper_cls, InitHelperBase):
            logger.warning(
                f"InitHelper class {helper_cls.__name__} from {module_name} is not a subclass of InitHelperBase"
            )
            cfg_sections.append(InitConfigSection(c.PAKKAGE_TYPE, []))
            continue

        helper: InitHelperBase = helper_cls()
        sections = helper.help()
        cfg_sections.extend(sections)

    # Create the config file from the saved sections
    config = configparser.ConfigParser()

    for section in cfg_sections:
        config.add_section(section.name)
        for option in section.options:
            config.set(section.name, option.key, option.value)

    f = io.StringIO()
    config.write(f)

    Module.print_rule(f"Content of pakk.cfg")
    print(f.getvalue())
    Module.print_rule(f"EOF")

    proceed = inquirer.confirm("Proceed with this configuration?", default=True).execute()

    if not proceed:
        logger.info("Aborting")
        return

    with open(os.path.join(path, "pakk.cfg"), "w") as f:
        logger.info("Writing pakk.cfg")
        config.write(f)

    return


if __name__ == "__main__":
    # kwargs = {
    #     # "all": True,
    #     "types": True,
    #     # "extended": True,
    # }
    kwargs = {}

    init("", **kwargs)
