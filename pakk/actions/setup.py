from __future__ import annotations

import logging
import os
import tempfile

from pakk import ROOT_DIR
from pakk.config import pakk_config
from pakk.config.base_config import BaseConfig
from pakk.config.pakk_config import Sections
from pakk.logger import Logger
from pakk.modules.manager.systemd.unit_generator import PakkParentService, PakkServiceFileBase, ServiceFile, PakkAutoUpdateService

from InquirerPy import inquirer
# from pyfiglet import Figlet

# Probably using https://github.com/CITGuru/PyInquirer

logger = logging.getLogger(__name__)


def setup(**kwargs):
    base_config = BaseConfig.set(**kwargs)
    flag_verbose = base_config.verbose

    Logger.setup_logger(logging.DEBUG if flag_verbose else logging.INFO)

    # Check if executed on linux
    if os.name != "posix":
        logger.error("This command is only available on linux")
        return

    logger.info("Starting pakk setup")

    # Check if config exists
    config = pakk_config.get()
    data_root_dir = config.get_abs_path("data_root_dir", Sections.MAIN)
    app_data_dir = config.get_abs_path("app_data_dir", Sections.MAIN)
    log_dir = config.get_abs_path("log_dir", Sections.MAIN)
    service_dir = config.get_abs_path("service_dir", Sections.MAIN)

    dirs = [ROOT_DIR, data_root_dir, app_data_dir, log_dir, service_dir]

    group_name = "pakk"

    # Create pakk group
    logger.info(f"Creating group {group_name}")
    os.system(f"sudo groupadd {group_name}")

    # Get the user name:
    user_name = os.environ.get("USER")
    logger.info(f"Adding user {user_name} to group {group_name}")
    os.system(f"sudo usermod -a -G {group_name} {user_name}")

    # Assign pakk package and data directory to pakk group
    for dir in dirs:
        logger.info(f"Assigning {dir} to group {group_name} and grant write access")
        os.system(f"sudo chgrp -R {group_name} {dir}")
        os.system(f"sudo chmod -R g+w {dir}")

    # Create sudoers file for pakk group
    # TODO: script execution is security risk, allow that only for checked system pakkages
    paths = [
        "# Created by pakk setup\n",
        "# Allow pakk group to execute setup scripts in pakkages",
        f"{data_root_dir}/*/*/*", # TODO: bspw. für Lilv benötigt, das muss aber besser gehen
        f"{data_root_dir}/*/*/*/*",
        "/usr/bin/bash",
        "# Allow pakk group to execute apt commands for setups",
        f"/usr/bin/apt",
        f"/usr/bin/apt-get",
        "# Allow pakk group to control systemctl and link service files into the systemd directory",
        f"/usr/bin/systemctl",
        f"/usr/bin/ln",
        "# Allow pakk group to control nginx",
        f"/usr/sbin/nginx",
    ]

    sudoers_file_content = ""
    for p in paths:
        s = p if p.startswith("#") else f"%{group_name} ALL=(root) NOPASSWD: {p}"
        s+= "\n"
        sudoers_file_content += s

    # Copy sudoers file to /etc/sudoers.d/pakk and change mod to 440
    sudoers_file_path = "/etc/sudoers.d/sudo_pakk"
    logger.info(f"Creating sudoers file at {sudoers_file_path}")
    logger.info(f"Content of sudoers file:\n{sudoers_file_content}")

    temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    temp_file.write(sudoers_file_content)
    temp_file.flush()
    temp_file.close()
    temp_file_path = temp_file.name

    logger.info(f"Copying {temp_file_path} to {sudoers_file_path}")
    os.system(f"sudo cp {temp_file_path} {sudoers_file_path}")

    logger.info(f"Changing mod of {sudoers_file_path} to 440")
    os.system(f"sudo chmod 440 {sudoers_file_path}")

    # Adapt nginx to work with user_name user
    logger.info(f"Adapting nginx' www-data to work with {user_name} user")
    os.system(f"sudo gpasswd -a www-data {user_name}")

    # Adapt nginx config
    logger.info("Adapting nginx config")
    nginx_config_path = "/etc/nginx/sites-enabled/default"
    locations_dir = config.get_abs_path("locations", "Env.Nginx")

    # Search for the following pattern
    # ### PAKK LOCATIONS ###
    # include {locations_dir/*};
    # ### END PAKK LOCATIONS ###

    start_pattern = "### PAKK LOCATIONS ###"
    end_pattern = "### END PAKK LOCATIONS ###"
    content = f"include {locations_dir}/*;"
    all_content = fr"{start_pattern}\n{content}\n{end_pattern}"
    # Escape every $.*/[\]^+?(){}| so that sed does not interpret them as regex
    escape_dict = {
        "$": r"\$",
        ".": r"\.",
        "*": r"\*",
        "/": r"\/",
        "[": r"\[",
        "]": r"\]",
        "^": r"\^",
        "+": r"\+",
        "?": r"\?",
        "(": r"\(",
        ")": r"\)",
        "{": r"\{",
        "}": r"\}",
        "|": r"\|"
    }
    escaped_content = all_content.translate(str.maketrans(escape_dict))

    grep_command = f"sudo grep -q '{start_pattern}' {nginx_config_path}"

    # If the pattern already exists, replace the content
    if os.system(grep_command) == 0:
        logger.info(f"Replacing existing nginx content")
        sed_command = fr"sudo sed -i '/{start_pattern}/,/{end_pattern}/c\\{escaped_content}' {nginx_config_path}"
        os.system(sed_command)
    # Otherwise append the content after the server_name
    else:
        sed_command = fr"sudo sed -i '/server_name _;/a\\{escaped_content}' {nginx_config_path}"
        logger.info(f"Appending nginx sites content: {sed_command}")
        os.system(sed_command)

    # Init pakk service
    logger.info("Setup pakk services")

    services: list[PakkServiceFileBase] = [PakkParentService(), PakkAutoUpdateService()]
    os.system(f"sudo mkdir -p {ServiceFile.PATH}")

    for s in services:
        logger.info(f"Creating service file for {s.service_file.name}")
        with open(temp_file_path, "w") as f:
            f.write(s.service_file.content)

        logger.info(f"Copying {temp_file_path} to {s.service_file.filepath}")
        os.system(f"sudo cp {temp_file_path} {s.service_file.filepath}")

    # Remove temp file
    os.system(f"rm {temp_file_path}")

    logger.info(f"Reloading systemctl daemon")
    os.system(f"sudo systemctl daemon-reload")

    for s in services:
        logger.info(f"Enabling {s.service_file.filepath}")
        os.system(f"sudo systemctl enable {s.service_file.filepath}")

    # logger.info(f"It is recommended to restart the system now to apply all changes properly")
    proceed = inquirer.confirm(message="It is recommended to restart the system now to apply all changes properly. Restart now?", default=True).execute()

    if proceed:
        logger.info(f"Restarting system")
        os.system(f"sudo reboot now")

    return

if __name__ == "__main__":
    setup()
