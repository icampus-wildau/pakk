import re
from typing import Callable, TypedDict

import click
import yaml
from click import Option

from pakk.config.process import Process
from pakk.pakkage.core import PakkageConfig

# class _Option():

#     flag: str
#     flag_abbreviation: str

#     def __init__(self, option: str, value: str):


class OptionDef:
    flag: str | None
    flag_abbreviation: str | None
    type: str | None
    env: str | None
    help: str | None
    default: str | None
    required: bool

    def __init__(self, flag: str, definition: str):
        self.flag = None
        self.flag_abbreviation = None
        self.type = None
        self.env = None
        self.help = None
        self.default = None
        self.required = False

        if flag.startswith("--"):
            self.flag = flag
        elif flag.startswith("-"):
            self.flag_abbreviation = flag

        self.parse_string(definition)

    def parse_string(self, defintion: str):
        # Case for dict definition
        if defintion.startswith("{"):
            data: dict = yaml.safe_load(defintion)
            if flag := data.get("flag"):
                self.flag = flag
            if flag_abbreviation := data.get("flag_abbreviation"):
                self.flag_abbreviation = flag_abbreviation
            if type := data.get("type"):
                self.type = type
            if env := data.get("env"):
                self.env = env
            if help := data.get("help"):
                self.help = help
            if default := data.get("default"):
                self.default = default
            if required := data.get("required"):
                self.required = str(required).lower() in ["true", "1", "yes", "y"]
        else:
            # Group 1 --> env var name
            # Group 3 --> default value
            pattern = r"^([^:]*)(:-)?(.*?)$"

            match = re.match(pattern, defintion)

            if match:
                self.env = match.group(1).strip()
                self.default = match.group(3).strip()
            else:
                self.env = defintion.strip()
                self.default = None

    def to_click_option(self) -> click.Option:
        param_declarations = [d for d in [self.flag_abbreviation, self.flag] if d is not None]

        return click.Option(
            param_declarations,
            help=self.help,
            default=self.default,
            required=self.required,
            # type=self.type,
            # envvar=self.env,
        )

    def __str__(self):
        return f"OptionDef(flag={self.flag}, flag_abbreviation={self.flag_abbreviation}, type={self.type}, env={self.env}, help={self.help}, default={self.default}, required={self.required})"


class PakkCliOptions:
    """
    Parser for [run_options] section in pakk.cfg.
    Maps CLI options to environment variables.

    Supports three approaches:
    1. Simple assignment in pakk.cfg:
    ```
    [run_options]
    -d = MICROPHONE_DEVICE_NAME

    or with default value
    -d = MICROPHONE_DEVICE_NAME:-all
    ```

    2. Detailed options in pakk.cfg:
    ```
    [run_options]
    -d = {type: str, env: MICROPHONE_DEVICE_NAME, help: "Device name", default: ReSpeaker}
    ```

    3. Dynamic env vars:
    ```
    pakk run --env-MICROPHONE_DEVICE_NAME=value
    ```
    """

    PAKK_SECTION_NAME = "run_options"

    def __init__(self, pakkage_version: PakkageConfig):
        self.pakkage_version = pakkage_version
        # self.env_mappings: dict[str, str] = {}
        self.option_defs: list[OptionDef] = []
        self.options: list[click.Option] = []

        self.parse_cfg_file()

    def parse_cfg_file(self):
        cfg = self.pakkage_version.cfg

        if not cfg.has_section(self.PAKK_SECTION_NAME):
            return

        option_defs: list[OptionDef] = []

        options = cfg.options(self.PAKK_SECTION_NAME)
        for option in options:
            if option.startswith("-"):
                option_defs.append(OptionDef(option, cfg.get(self.PAKK_SECTION_NAME, option)))
                # self.env_mappings[option] = cfg.get(self.PAKK_SECTION_NAME, option)

        self.option_defs = option_defs
        self._option_map: dict[str, OptionDef] = {}

        for option_def in self.option_defs:
            option = option_def.to_click_option()
            self.options.append(option)  # type: ignore
            self._option_map[option.name] = option_def

        # print("--------------------------------")

        # for option in option_defs:
        #     print(option)

    def build_command(self, cb: Callable[[dict], None], cmd_name="run", **kwargs) -> click.Command:
        ctx = kwargs.get("ctx")

        params = self.options.copy()

        # Add default options
        params.append(
            click.Option(
                ["-v", "--verbose"],
                help="Give more output.",
                default=False,
                is_flag=True,
            )
        )

        cmd = click.Command(
            cmd_name,
            context_settings=dict(help_option_names=["-h", "--help"], max_content_width=ctx.max_content_width),
            params=params,
            callback=cb,
        )

        return cmd

    def run(self, **kwargs):
        env_vars: dict[str, str] = {}

        # Convert the kwargs to environment variables
        for option in self.options:
            if option.name in kwargs:
                env_var = self._option_map[option.name].env
                if env_var is None:
                    raise ValueError(f"Pakk run option {option.name} has no environment variable defined in pakk.cfg")

                val = kwargs[option.name]
                if val is not None:
                    env_vars[env_var] = val

        # print("ASSIGNING ENV VARS")
        # print(env_vars)

        Process.update_env_vars(env_vars)
        # print(Process.get_env_vars())

        self.pakkage_version.run()

    #     def parse_run_options(self, instruction_content: str):
    #     """Parse the run_options section content"""
    #     # This will be called for each line in the [RunOptions] section
    #     # The instruction_content will be the full section content
    #     lines = instruction_content.strip().split('\n')

    #     for line in lines:
    #         line = line.strip()
    #         if not line or line.startswith('#'):
    #             continue

    #         if '=' in line:
    #             key, value = line.split('=', 1)
    #             key = key.strip()
    #             value = value.strip()

    #             # Approach 1: Simple assignment
    #             if key.startswith('-') and not value.startswith('{'):
    #                 self.simple_mappings[key] = value

    #             # Approach 2: Dynamic options
    #             elif value.startswith('{') and value.endswith('}'):
    #                 try:
    #                     # Simple JSON-like parsing for the dynamic options
    #                     import ast
    #                     option_config = ast.literal_eval(value)
    #                     self.dynamic_options[key] = option_config
    #                 except:
    #                     # Fallback to simple assignment if parsing fails
    #                     self.simple_mappings[key] = value

    #             # Approach 3: Direct environment variable assignment
    #             elif key.startswith('--env-'):
    #                 env_var = key[6:]  # Remove '--env-' prefix
    #                 self.simple_mappings[f"--env-{env_var}"] = env_var

    #             else:
    #                 # Default to simple assignment
    #                 self.simple_mappings[key] = value

    # def get_cli_to_env_mapping(self) -> dict[str, str]:
    #     """Get the complete CLI to environment variable mapping"""
    #     mapping = self.simple_mappings.copy()

    #     # Add dynamic options to the mapping
    #     for option, config in self.dynamic_options.items():
    #         if 'env' in config:
    #             mapping[option] = config['env']

    #     return mapping

    # def get_dynamic_options_config(self) -> dict[str, dict]:
    #     """Get the dynamic options configuration for Click"""
    #     return self.dynamic_options.copy()


# def parse_run_arguments(run_args: list[str], pakkage_config) -> dict[str, str]:
#     """
#     Parse run arguments and convert them to environment variables.

#     Supports three approaches:
#     1. Simple assignment from pakk.cfg: -d=value -> MICROPHONE_DEVICE_NAME=value
#     2. Dynamic options: --device=value -> MICROPHONE_DEVICE_NAME=value
#     3. Arbitrary env vars: --env-MICROPHONE_DEVICE_NAME=value -> MICROPHONE_DEVICE_NAME=value
#     """
#     env_vars = {}

#     if not run_args:
#         return env_vars

#     # Get CLI to environment variable mappings from the package
#     cli_to_env_mapping = {}
#     dynamic_options_config = {}

#     # Check if the package has RunOptions type
#     for type_instance in pakkage_config.pakk_types:
#         if hasattr(type_instance, 'get_cli_to_env_mapping'):
#             cli_to_env_mapping.update(type_instance.get_cli_to_env_mapping())
#             if hasattr(type_instance, 'get_dynamic_options_config'):
#                 dynamic_options_config.update(type_instance.get_dynamic_options_config())

#     for arg in run_args:
#         if '=' in arg:
#             option, value = arg.split('=', 1)
#             option = option.strip()
#             value = value.strip().strip('"\'')

#             # Approach 1 & 2: Use mappings from pakk.cfg
#             if option in cli_to_env_mapping:
#                 env_var = cli_to_env_mapping[option]
#                 env_vars[env_var] = value

#             # Approach 3: Arbitrary environment variables with --env- prefix
#             elif option.startswith('--env-'):
#                 env_var = option[6:]  # Remove '--env-' prefix
#                 env_vars[env_var] = value

#     return env_vars
