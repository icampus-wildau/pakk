# from __future__ import annotations
from __future__ import annotations

import builtins

import click
from click import Context
from click_aliases import ClickAliasedGroup


def show_figlet(message: str):
    from pyfiglet import Figlet

    # See for fonts: http://www.figlet.org/examples.html
    f = Figlet(font="thin")
    click.echo(f.renderText("message"))


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"], max_content_width=800)


def init_pakk(**kwargs):
    import logging

    from pakk.args.base_args import BaseArgs
    from pakk.args.base_args import PakkArgs
    from pakk.logger import Logger
    from pakk.setup.checker import PakkSetupChecker
    from pakk.setup.setup_group import PakkGroupSetup
    from pakk.setup.setup_service import ServiceSetup
    from pakk.setup.setup_sudoers import PakkSudoersSetup

    # Initialize the pakk args to be globally available
    PakkArgs.init(**kwargs)
    # Initialize logger that prints to rich console
    Logger.setup_logger(logging.DEBUG if BaseArgs.get().verbose else logging.INFO)

    PakkSetupChecker.require_setups(
        [
            PakkGroupSetup,
            ServiceSetup,
            PakkSudoersSetup,
        ]
    )


@click.group(cls=ClickAliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx: Context, **kwargs):
    pass


@cli.command(aliases=["i"])
@click.argument("pakkage", nargs=-1, required=True)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option(
    "-F",
    "--force-reinstall",
    is_flag=True,
    default=False,
    help="Reinstall defined pakkage even if it is already installed and up-to-date.",
)
@click.option(
    "-U",
    "--upgrade",
    is_flag=True,
    default=False,
    help="Upgrade all specified packages to the newest available version. The handling of dependencies depends on the upgrade-strategy used.",
)
@click.option(
    "--upgrade-strategy",
    default="only-if-needed",
    help='Determines how dependency upgrading should be handled [default: only-if-needed]. "eager" - dependencies are upgraded regardless of whether the currently installed version satisfies the requirements of the upgraded pakkage(s). "only-if-needed" -  are upgraded only when they do not satisfy the requirements of the upgraded pakkage(s).',
)
@click.option(
    "--dry-run", is_flag=True, default=False, help="Don't actually install anything, just print what would be."
)  #  Can be used in combination with --ignore-installed to 'resolve' the requirements.
@click.option("--no-deps", is_flag=True, default=False, help="Don't install pakkage dependencies.")
@click.option(
    "--repair",
    is_flag=True,
    default=False,
    help="Repair dependencies of installed pakkages if they are missing or broken.",
)
# @click.option("--ignore-installed", is_flag=True, default=False,
#               help="[TODO] Ignore the installed pakkages (reinstalling instead of upgrading). Use with caution, as it can easily break your system.")
@click.option(
    "--refetch",
    is_flag=True,
    default=False,
    help="Refetches the pakkage from the server, otherwise already fetched pakkages are reused. Use in combination with `--force-reinstall` to reinstall a clean fetched copy of the package.",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    default=False,
    help="Clear the complete cache before installing. Use if you don't find versions that should be actually available.",
)
@click.option("--rebuild-base-images", is_flag=True, default=False, help="Rebuilds the base environment docker images.")
@click.pass_context
def install(ctx: Context, **kwargs):
    """
    Install a PAKKAGE (or multiple PAKKAGES).

    You can specify a version with PAKKAGE@VERSION.
    If no version is specified, the latest version will be installed."""
    from configparser import InterpolationMissingOptionError

    from pakk.actions.install import PakkageNotFoundException
    from pakk.actions.install import install

    # from pakk.config.pakk_config import MissingConfigSectionOptionException
    # from pakk.config.pakk_config import get_cfg_paths
    from pakk.config.main_cfg import MainConfig

    # from pakk.helper.module_importer import PakkModuleNotFoundException
    from pakk.modules.resolver.base import ResolverException

    init_pakk(**kwargs)

    try:
        install(builtins.list(kwargs["pakkage"]), **kwargs)
    # except MissingConfigSectionOptionException as e:
    #     from pakk.logger import Logger

    #     if kwargs["verbose"]:
    #         Logger.get_console().print_exception()

    #     p = get_cfg_paths()
    #     Logger.get_console().print(e.message)

    #     fix_msg = "To fix this, do one of the following:\n"
    #     fix_msg += f"  - adapt the config files at [b]{p}[/b]\n"
    #     fix_msg += f"  - run [b]pakk setup[/b] to create a new fixed config file\n"

    #     Logger.get_console().print(fix_msg)
    except InterpolationMissingOptionError as e:
        from pakk.logger import Logger

        if kwargs["verbose"]:
            Logger.get_console().print_exception()

        # p = get_cfg_paths()
        p = MainConfig.get_configs_dir()
        Logger.get_console().print("[bold red]" + e.message)

        fix_msg = "To fix this, do one of the following:\n"
        fix_msg += f"  - check if you are running pakk in the correct environment with the correct env vars\n"
        fix_msg += (
            f"  - adapt the option '{e.option}' under section '[{e.section}]' in the config files at [b]{p}[/b]\n"
        )

        Logger.get_console().print(fix_msg)

    # except PakkModuleNotFoundException as e:
    #     from pakk.logger import Logger

    #     if kwargs["verbose"]:
    #         Logger.get_console().print_exception()

    #     Logger.print_exception_message(e)
    #     p = get_cfg_paths()

    #     fix_msg = "To fix this, do one of the following:\n"
    #     fix_msg += (
    #         f"  - adapt the entry '{e.module_name}' under section '[{e.section}]' in the config files at [b]{p}[/b]\n"
    #     )

    #     if e.class_name is None:
    #         fix_msg += f"  - check if '{e.module_name}' is an importable module from an installed python package\n"
    #     else:
    #         fix_msg += f"  - check if '{e.class_name}' is a class in the module '{e.module_name}'\n"

    #     Logger.get_console().print(fix_msg)
    except PakkageNotFoundException as e:
        from pakk.logger import Logger

        if kwargs["verbose"]:
            Logger.get_console().print_exception()

        Logger.print_exception_message(e)

        fix_msg = "To fix this, do one of the following:\n"
        fix_msg += (
            f"  - choose as argument an existing pakkage (run 'ls --all' to get a list of available remote pakkages)\n"
        )
        fix_msg += f"  - check if your sources for discovery are reachable and correctly configured\n"

        Logger.get_console().print(fix_msg)
    except ResolverException as e:
        from pakk.logger import Logger

        if kwargs["verbose"]:
            Logger.get_console().print_exception()
        Logger.print_exception_message(e)
        x = e.get_msg()

        # Logger.get_console().print_exception()
    except Exception as e:
        from pakk.logger import Logger

        Logger.get_console().print_exception()
    except KeyboardInterrupt:
        from pakk.logger import Logger

        Logger.get_console().print("Keyboard interrupt at CLI...")
    #     pass
    # finally:
    #     ctx.exit(0)


# @cli.command()
# @click.option('--version', default=1.0, prompt='Version', help='Version number.')
# @click.argument('package_name')
# def show(version, package_name):
#     """SHOW PACKAGE DETAILS"""
#     # TODO
#     click.echo(f'show package details of {package_name}@{version}')


# alternatively @all_commands.command()
@cli.command(aliases=["ls"])
@click.argument("REGEX_FILTER", required=False)
@click.option("-x", "--extended", is_flag=True, default=False, help="Show extended information.")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("--available", is_flag=True, default=False, help="Show available versions for installed pakkages.")
@click.option("-a", "--all", is_flag=True, default=False, help="Show all available pakkages.")
@click.option("-l", "--location", multiple=True, help="Add lookup locations for pakkages.")
@click.option("--limit-available", default=5, help="Limit the number of shown available versions to the newest n'th.")
@click.option("-n", "--name", is_flag=True, default=False, help="Show the name of the pakkage.")
# @click.option('-d', '--description', is_flag=True, default=False, help='Show the description of the pakkage.')
@click.option("-k", "--keywords", is_flag=True, default=False, help="Show the keywords of the pakkage.")
@click.option("-t", "--types", is_flag=True, default=False, help="Show the install types of the pakkage.")
@click.option("--lines", is_flag=True, default=False, help="Show lines between rows for more clarity.")
@click.pass_context
def list(ctx: Context, **kwargs):
    """
    List all installed pakkages.

    You can optionally specify a REGEX_FILTER expression to filter the list.
    """
    from pakk.actions.list import list

    init_pakk(**kwargs)
    list(**kwargs)


@cli.command(aliases=["t"])
# @click.argument('NAME_REGEX', required=False)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("-d", "--depth", default=0, help="Maximum depth of the tree. 0 prints the complete tree.")
@click.pass_context
def tree(ctx: Context, **kwargs):
    """
    Show the dependency tree of all installed pakkages.
    """
    # You can optionally specify a NAME_REGEX expression to filter the list.

    from pakk.actions.tree import show_tree

    init_pakk(**kwargs)
    show_tree(**kwargs)


@cli.command(aliases=["cfg"])
@click.argument("configuration", required=False)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("-r", "--reset", is_flag=True, default=False, help="Reset the configuration.")
@click.pass_context
def configure(ctx: Context, **kwargs):
    """
    Configure pakk.
    If no configuration is given, everything of pakk is configured.
    You can specify a CONFIGURATION to configure only a specific part / connector of pakk.
    """
    from pakk.actions.configure import configure

    init_pakk(**kwargs)
    configure(**kwargs)


@cli.command(aliases=["s"])
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("-r", "--reset", is_flag=True, default=False, help="Reset and rerun the configuration.")
@click.pass_context
def setup(ctx: Context, **kwargs):
    """
    Run the setup for Pakk.
    This initiates all necessary rights and files to let Pakk run successfully.
    """
    from pakk.actions.setup import setup

    init_pakk(**kwargs)
    setup(**kwargs)


@cli.command(aliases=["ros_env", "env"])
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("-r", "--rebuild", is_flag=True, default=False, help="Rebuilds the docker image if it already exists.")
@click.option("--rebuild_base_images", is_flag=True, default=False, help="Rebuilds the base environment docker images.")
def ros_environment(**kwargs):
    """
    Starts a ROS environment.
    """

    from pakk.actions.environment import environment

    init_pakk(**kwargs)
    environment(**kwargs)


@cli.command(aliases=["ros"])
@click.argument("run_args", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
# @click.option("-r", "--rebuild", is_flag=True, default=False, help='Rebuilds the docker image if it already exists.')
# @click.option("--rebuild_base_images", is_flag=True, default=False, help='Rebuilds the base environment docker images.')
def ros2(run_args, **kwargs):
    """
    Run a ROS node from a package.
    """

    from pakk.actions.ros2 import ros2

    init_pakk(**kwargs)
    ros2(run_args, **kwargs)


@cli.command(aliases=["source"])
# @click.argument('run_args', nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
# @click.option("-r", "--rebuild", is_flag=True, default=False, help='Rebuilds the docker image if it already exists.')
# @click.option("--rebuild_base_images", is_flag=True, default=False, help='Rebuilds the base environment docker images.')
def source(**kwargs):
    """
    Sources the environment with all settings from the installed pakkages.
    """

    from pakk.actions.source import source

    init_pakk(**kwargs)
    source(**kwargs)


if __name__ == "__main__":
    cli(["cfg"])


@cli.command(aliases=["r"])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
def run(**kwargs):
    """
    Runs the given pakkage interactively.
    """

    from pakk.actions.manager import run as r

    init_pakk(**kwargs)
    r(**kwargs)


@cli.command(aliases=[])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("-R", "--reload_service_files", is_flag=True, default=False, help="Reloads the service files.")
def start(**kwargs):
    """
    Starts the given executable pakkage as services.
    """

    from pakk.actions.manager import start

    init_pakk(**kwargs)
    start(**kwargs)
    # print("RUN DUMMY")


@cli.command(aliases=["e"])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
def enable(**kwargs):
    """
    Enables the given executable pakkage.
    """

    from pakk.actions.manager import enable

    init_pakk(**kwargs)
    enable(**kwargs)


@cli.command(aliases=[])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
def stop(**kwargs):
    """
    Stops the given executable pakkage service.
    """

    from pakk.actions.manager import stop

    init_pakk(**kwargs)
    stop(**kwargs)


@cli.command(aliases=["d"])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
def disable(**kwargs):
    """
    Disables the given executable pakkage.
    """

    from pakk.actions.manager import disable

    init_pakk(**kwargs)
    disable(**kwargs)


@cli.command(aliases=[])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("-r", "--running", is_flag=True, default=False, help="Only restart running pakkages.")
@click.option("-e", "--enabled", is_flag=True, default=False, help="Only restart enabled pakkages.")
def restart(**kwargs):
    """
    Restarts the given executable pakkage.
    """

    from pakk.actions.manager import restart

    init_pakk(**kwargs)
    restart(**kwargs)


@cli.command(aliases=[])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option(
    "-f", "--follow_logs", is_flag=True, default=False, help="Follow the logs of the given executable pakkage."
)
def log(**kwargs):
    """
    Follows the log of the given executable pakkage.
    """

    from pakk.actions.manager import follow_log

    init_pakk(**kwargs)
    follow_log(**kwargs)


@cli.command(aliases=[])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
def status(**kwargs):
    """
    Shows the status of startable pakkages in the system.
    """

    from pakk.actions.status import status

    init_pakk(**kwargs)
    status(**kwargs)


if __name__ == "__main__":
    cli(["cfg"])


@cli.command(aliases=[])
@click.argument("path", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
def init(**kwargs):
    """
    Initialize a pakkage in the given path.
    """
    from pakk.actions.init import init

    init_pakk(**kwargs)
    init(**kwargs)


if __name__ == "__main__":
    cli(["cfg"])


@cli.command(aliases=[])
@click.argument("path", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
def dev(**kwargs):
    """
    Switches a pakkage to development mode.
    """
    from pakk.actions.dev import dev

    init_pakk(**kwargs)
    dev(**kwargs)


if __name__ == "__main__":
    cli(["cfg"])


@cli.command(aliases=["u"])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
@click.option("-a", "--all", is_flag=True, default=False, help="Updates all packages to the newest (fitting) version.")
@click.option(
    "--auto",
    is_flag=True,
    default=False,
    help="Flag to indicate the call of the autoupdater, checks if auto update is set to true in the config.",
)
@click.option("-s", "--selfupdate", is_flag=True, default=False, help="Updates pakk itself.")
def update(**kwargs):
    """
    Updates the given pakkage(s) to the newest version.
    """

    from pakk.actions.update import update

    init_pakk(**kwargs)
    update(**kwargs)


@cli.command(aliases=[])
@click.argument("pakkage_names", nargs=-1)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Give more output.")
# @click.option("-a", "--all", is_flag=True, default=False, help='Updates all packages to the newest (fitting) version.')
# @click.option("--auto", is_flag=True, default=False, help='Flag to indicate the call of the autoupdater, checks if auto update is set to true in the config.')
# @click.option("-s", "--selfupdate", is_flag=True, default=False, help='Updates pakk itself.')
def clean(**kwargs):
    """
    Cleans errors from pakkages.
    """

    from pakk.actions.clean import clean

    init_pakk(**kwargs)
    clean(**kwargs)
