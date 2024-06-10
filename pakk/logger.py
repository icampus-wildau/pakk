from __future__ import annotations

import logging
import time
from functools import wraps

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress
from rich.progress import TaskID

console = Console()

logger = None


class Logger:
    @staticmethod
    def get_console():
        global console
        return console

    @staticmethod
    def setup_logger(level: int = logging.INFO, ignore_if_already_setup: bool = True):
        global logger
        if ignore_if_already_setup and logger is not None:
            return
        logger = logging.getLogger("pakk")
        # logger.setLevel(level)
        # logger.addHandler(ConsoleLogger())
        # return
        #####

        verbose = level < logging.INFO

        if verbose:
            # FORMAT = "%(asctime)s - %(name)s - %(message)s"
            # FORMAT = "%(asctime)s %(message)s"
            FORMAT = "%(message)s"
        else:
            FORMAT = "%(message)s"

        # Set the format and handler for the logger
        handler = RichHandler(
            show_time=verbose,
            show_level=verbose,
            console=Logger.get_console(),
            markup=True,
        )
        # formatter = logging.Formatter(fmt=FORMAT, datefmt="[%X]")
        formatter = RichFormatter(fmt=FORMAT, datefmt="[%X]")

        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    @staticmethod
    def get_plain_text(message):
        """Returns a plain text without any rich formatting"""
        return Logger.get_console().render_str(message).plain

    @staticmethod
    def print_exception_message(exception: Exception, include_exception_name=True):
        """
        Prints an exception message to the console.

        Parameters
        ----------
        exception: Exception
            The exception to print
        include_exception_name: bool
            If True, the exception name will be included in the message
        """
        if include_exception_name:
            msg = f"[bold red]{type(exception).__name__}: [/bold red][red][/red]: {exception}"
        else:
            msg = f"[bold red]{exception}[/bold red]"
        Logger.get_console().print(msg)


class RichFormatter(logging.Formatter):
    def __init__(self, fmt: str, datefmt: str):
        super().__init__(fmt=fmt, datefmt=datefmt)
        # self.base_format = "[%(levelname)s] %(message)s [%(asctime)s] (%(name)s - %(filename)s:%(lineno)d)"
        # self.compact_format = "[%(levelname)s] %(message)s"
        # self.raw_format = "%(message)s"

        # f = self.compact_format if compact else self.base_format

        self.colored_formats = {
            logging.DEBUG: "[grey]" + fmt,
            logging.INFO: "[grey]" + fmt,
            logging.WARNING: "[yellow]" + fmt,
            logging.ERROR: "[red]" + fmt,
            logging.CRITICAL: "[bold red]" + fmt,
        }

        self.formatters = {
            logging.DEBUG: logging.Formatter(self.colored_formats[logging.DEBUG]),
            logging.INFO: logging.Formatter(self.colored_formats[logging.INFO]),
            logging.WARNING: logging.Formatter(self.colored_formats[logging.WARNING]),
            logging.ERROR: logging.Formatter(self.colored_formats[logging.ERROR]),
            logging.CRITICAL: logging.Formatter(self.colored_formats[logging.CRITICAL]),
        }

    def format(self, record: logging.LogRecord):
        formatter = self.formatters[record.levelno]
        s = formatter.format(record)

        # Now also render rich markup in the log message
        # print(s)
        # s = console.render_str(s).
        return s


class ConsoleLogger(logging.StreamHandler):
    def __init__(self):
        super().__init__()
        global console
        self.console = console

        self.setFormatter(RichFormatter(fmt="%(message)s", datefmt="[%X]"))

    def emit(self, record):
        try:
            msg = self.format(record)
            # TODO add real logging
            self.console.print(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
