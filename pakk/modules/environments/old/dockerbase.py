from __future__ import annotations

import logging
import os

from pakk.args.base_args import BaseArgs
from pakk.config import pakk_config
from pakk.config.pakk_config import Sections as ConfigSections
from pakk.modules.module import Module

logger = logging.getLogger(__name__)


class DockerfileGenerator:
    """
    Helper class for generating Dockerfiles.
    """

    def __init__(self):
        self.base_image = None
        self._lines = []

    def add_line(self, line: str) -> None:
        """
        Add a line to the Dockerfile.

        Parameters:
        -----------
        line : str
            A line of the Dockerfile to add.
        """
        self._lines.append(line.strip())

    def add_lines(self, *lines: str) -> None:
        """
        Add multiple lines to the Dockerfile.

        Parameters:
        -----------
        lines : str
            Lines of the Dockerfile to add.
        """
        for line in lines:
            self.add_line(line)

    @property
    def content(self) -> str:
        """
        Get the contents of the Dockerfile as a string.
        """
        if self.base_image is None:
            raise ValueError("Base image not set")

        lines = "\n".join(self._lines)

        return f"FROM {self.base_image}\n" + lines


class DockerEnvironment(Module):
    IMAGE_NAME = "pakk_docker_env"

    MNT_HOST_PREFIX = "/mnt/host/"

    SECTION_NAME = "Env.Docker"

    CONFIG_REQUIREMENTS = {
        SECTION_NAME: ["dockerfiles_dir"],
    }

    _image_exists = False

    def __init__(self, image_name: str):
        super().__init__()
        self.dockerfile = DockerfileGenerator()

        self.dockerfile_name = image_name
        self.image_name = self.fix_docker_image_name(image_name)
        """Name of the docker image."""

        self.mounts: dict[str, str] = {}
        """Paths to mount into the docker container. Keys are the container paths, values are the host paths."""

        # Mount all_pakkges_dir to make symlinked modules available
        # Get the dest path for mounting the all_pakkges_dir into the container
        container_all_path = self.get_mnt_destination_path(self.all_pakkges_dir_path)
        self.mounts[container_all_path] = self.all_pakkges_dir_path

    @staticmethod
    def fix_docker_image_name(image_name: str) -> str:
        return image_name.replace(":", "_").replace("/", "_").replace("@", ":")

    def get_interactive_docker_command(self):
        cmd_parts = ["docker run -it --rm"]

        for container_path, host_path in self.mounts.items():
            cmd_parts.append(f'-v "{host_path}":"{container_path}"')

        cmd_parts.append(f"{self.image_name}")

        return " ".join(cmd_parts)

    def get_docker_command(self, commands: str | list[str]):
        if isinstance(commands, str):
            commands = [commands]

        command = " && ".join(commands)

        cmd_parts = ["docker run --rm"]

        for container_path, host_path in self.mounts.items():
            cmd_parts.append(f'-v "{host_path}":"{container_path}"')

        cmd_parts.append(f'{self.image_name} bash -c "{command}"')

        return " ".join(cmd_parts)

    @classmethod
    def require_image(cls: type[DockerEnvironment]):
        if not cls._image_exists:
            cls(image_name=cls.IMAGE_NAME).build_image(rebuild_if_exists=BaseConfig.get().rebuild_base_images)
            cls._image_exists = True

    @staticmethod
    def image_exists(image_name):
        output = Module.run_commands(f'docker image inspect {image_name} --format="exists"').strip()
        return output == "exists"

    def build_image(self, rebuild_if_exists=False, dockerfile_path: str = None):
        if self.image_exists(self.image_name):
            if not rebuild_if_exists:
                logger.debug(f"Using existing docker image '{self.image_name}'")
                return

            logger.debug(f"Rebuilding docker image '{self.image_name}'")

        # Save dockerfile
        content = self.dockerfile.content
        if dockerfile_path is None:
            dockerfile_path = os.path.join(
                self.config.get_abs_path("dockerfiles_dir", DockerEnvironment.SECTION_NAME, create_dir=True),
                f"{self.dockerfile_name}.dockerfile",
            )
        with open(dockerfile_path, "w") as f:
            f.write(content)

        logger.info(f"Building docker image '{self.image_name}'")

        # Build image
        self.run_commands(f"docker build -t {self.image_name} -f {dockerfile_path} .", print_output=True)

        logger.debug(f"Finished docker image '{self.image_name}', stored dockerfile at {dockerfile_path}")

    @staticmethod
    def get_mnt_destination_path(host_path: str) -> str:
        """
        Get the equivalent mount destination path inside the container for a host path that is used in symlinks inside the container.

        Parameters
        ----------
        host_path:
            The host path to get the equivalent mount destination for.

        Returns
        -------
        str: The equivalent path for the mounted path.
        """

        # Create path for mounting the all_pakkges_dir into the container
        # to support the symlinked modules
        mnt_prefix = DockerEnvironment.MNT_HOST_PREFIX

        # Fix windows path syntax
        fixed_path = host_path
        splits = fixed_path.split(":")
        if len(splits) == 2:
            fixed_path = splits[0].lower() + splits[1]
        container_path = os.path.join(mnt_prefix, fixed_path).replace("\\", "/")

        return container_path
