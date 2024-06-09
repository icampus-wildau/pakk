from __future__ import annotations

import datetime
import os
import re

from InquirerPy import inquirer
from InquirerPy import prompt

# from pakk import DEFAULT_CFG_FILENAME
# from pakk import DEFAULT_USR_CFG_FILENAME
from pakk import DEFAULT_CFG_DIR
from pakk import ENVS
from pakk.logger import Logger
from pakk.modules.module import Module

# print("Import figlet")
# from pyfiglet import Figlet


# Probably using https://github.com/CITGuru/PyInquirer


CFG_REPLACE_PATTERN = re.compile(r"((#+ .*?\n)*)(.*?)( ?[=:] ?)(\[\[((.*?)(\|\|))?(.*?)\]\])\n", re.MULTILINE)
# Group 1: Comment lines above the config entry
# Group 3: The config option key name
# Group 5: The config option value with double brackets as placeholder
# Group 7: The config option name for inquire
# Group 9: The config option default value


def config(**kwargs):
    # f = Figlet(font='cyberlarge')

    print("THIS IS DEPRECATED")
    return

    console = Logger.get_console()
    Module.print_rule("Setup of Pakk")
    # console.print(f.renderText("pakk"))

    console.print("This will guide you through the setup of pakk and create a config file for you.\n")

    config_dir = os.environ.get(ENVS.CONFIG_DIR, DEFAULT_CFG_DIR)
    out_name = os.environ.get(ENVS.CONFIG_NAME, DEFAULT_USR_CFG_FILENAME)
    path = os.path.abspath(os.path.join(config_dir, out_name))

    console.print(f"The config file will be created at: {path}")
    console.print(
        f"You can change the config file location by setting the environment variables {ENVS.CONFIG_DIR} and {ENVS.CONFIG_NAME}.\n"
    )

    template_path = os.path.join(DEFAULT_CFG_DIR, "user_cfg_template.cfg")

    abs_path = os.path.abspath(template_path)

    if not os.path.exists(abs_path):
        raise Exception("Template file not found")

    with open(abs_path, "r") as f:
        config_str = f.read()

    # Iterate over all matches and ask the user for the value
    start_pos = 0
    while (match := CFG_REPLACE_PATTERN.search(config_str, start_pos)) is not None:
        start_pos = match.end()

        comment = match.group(1)
        comment_lines = [c.strip() for c in comment.splitlines()]
        comment_lines = [c for c in comment_lines if not c.startswith("##")]
        comment_lines = [c[2:] if c.startswith("# ") else c for c in comment_lines]
        comment_cleaned = "\n".join(comment_lines)

        key_name = match.group(3)
        placeholder = match.group(5)
        placeholder_start = match.start(5)
        placeholder_end = match.end(5)
        inquire_name = match.group(7)
        default_value = match.group(9)

        if key_name.startswith("#"):
            continue

        if inquire_name is None or inquire_name == "":
            inquire_name = key_name

        print(f"\n{comment_cleaned}")

        value = inquirer.text(
            message=f"{inquire_name}:",
            # long_instruction=comment_cleaned,
            default=default_value,
            amark="!",
            qmark="?",
        ).execute()

        # Replace the placeholder with the value
        config_str = config_str[:placeholder_start] + value + config_str[placeholder_end:]

        # Adapt start position to the new string length
        start_pos += len(value) - len(placeholder)

    console.print("")

    # Write the config file
    proceed = inquirer.confirm(message="Save the config file now?", default=False).execute()
    if not proceed:
        return

    if os.path.exists(path):
        console.print(f"Config file already exists at {path}")
        proceed = inquirer.confirm(message="Create backup of current config file?", default=True).execute()
        if proceed:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path + f".{timestamp}.bak"
            os.rename(path, backup_path)
            console.print(f"Backup created at {backup_path}")

    with open(os.path.join(config_dir, out_name), "w") as f:
        f.write(config_str)


if __name__ == "__main__":
    config()
