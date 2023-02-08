"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
``[options.entry_points]`` section in ``setup.cfg``::

    console_scripts =
         fibonacci = make2check.skeleton:run

Then run ``pip install .`` (or ``pip install -e .`` for editable mode)
which will install the command ``fibonacci`` inside your current environment.

Besides console scripts, the header (i.e. until ``_logger``...) of this file can
also be used as template for Python modules.

Note:
    This skeleton file can be safely removed if not needed!

References:
    - https://setuptools.pypa.io/en/latest/userguide/entry_point.html
    - https://pip.pypa.io/en/stable/reference/pip_install
"""

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

import colorama
from colorama import Fore, Back, Style
from colorama.ansi import AnsiBack, AnsiFore
from make2check import __version__

__author__ = "Eelco van Vliet"
__copyright__ = "Eelco van Vliet"
__license__ = "MIT"

FOREGROUND_COLOR_OPTIONS = set([c for c in dir(AnsiFore) if "__" not in c])
BACKGROUND_COLOR_OPTIONS = set([c for c in dir(AnsiBack) if "__" not in c])
# dit is nodig om kleuren in een powershell te kunnen gebruiken
colorama.init(True)

_logger = logging.getLogger(__name__)


# ---- Python API ----
# The functions defined in this section can be imported by users in their
# Python scripts/interactive interpreter, e.g. via
# `from make2check.skeleton import fib`,
# when using this Python module as a library.

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.

class TerminalColors:
    def __init__(self, foreground_color=None, background_color=None, use_terminal_colors=False):
        self.use_terminal_colors = use_terminal_colors
        self.foreground_color = self.set_color(color_name=foreground_color, foreground=True)
        self.background_color = self.set_color(color_name=background_color, foreground=False)
        if use_terminal_colors:
            self.reset_colors = Style.RESET_ALL
        else:
            self.reset_colors = ""

    def set_color(self, color_name, foreground=True):
        if color_name is not None and self.use_terminal_colors:
            if foreground:
                color = getattr(Fore, color_name)
            else:
                color = getattr(Back, color_name)
        else:
            color = ""

        return color


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Run make in debug mode  and find the missing files")
    parser.add_argument(
        "--version",
        action="version",
        version="make2check {ver}".format(ver=__version__),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--debug",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    parser.add_argument(
        "--test",
        help="Do een droge run zonder iets te doen",
        action="store_true",
    )
    parser.add_argument(
        "target",
        help="Specificeer de make target die je wilt checken",
        nargs="?"
    )

    parser.add_argument(
        "--no_colors",
        help="Geef geen kleur aan de commando's die naar terminal geschreven worden",
        action="store_false", default=True, dest="use_terminal_colors"
    )
    parser.add_argument(
        "--warning_foreground_color", help="Voorgrondkleur van warnings",
        choices=FOREGROUND_COLOR_OPTIONS, default="RED"
    )
    parser.add_argument(
        "--warning_background_color", help="Achtergrondkleur van commando's",
        choices=BACKGROUND_COLOR_OPTIONS, default=None
    )
    parser.add_argument(
        "--message_foreground_color", help="Voorgrondkleur van warnings",
        choices=FOREGROUND_COLOR_OPTIONS, default="GREEN"
    )
    parser.add_argument(
        "--message_background_color", help="Achtergrondkleur van commando's",
        choices=BACKGROUND_COLOR_OPTIONS, default=None
    )

    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def match_consider(line):
    if m := re.search("Considering target file '(.*)'", line):
        match = m
    elif m := re.search("Doelbestand '(.*)' wordt overwogen", line):
        match = m
    else:
        match = None
    return match


def match_implicit_rule(line, rule):
    if m := re.search(f"No implicit rule found for '({rule})'", line):
        match = m
    elif m := re.search(f"Geen impliciete regel voor '({rule})' gevonden", line):
        match = m
    else:
        match = None
    return match


def match_must_remake(line, target):
    if m := re.search(f"Must remake target '({target})'", line):
        match = m
    elif m := re.search(f"'({target})' moet opnieuw gemaakt worden", line):
        match = m
    else:
        match = None
    return match


class CheckRule:
    def __init__(self,
                 message_foreground_color=None,
                 message_background_color=None,
                 warning_foreground_color=None,
                 warning_background_color=None,
                 use_terminal_colors=True,
                 ):
        self.rule = None
        self.analyse = False
        self.missing_counter = 0

        self.message_colors = TerminalColors(foreground_color=message_foreground_color,
                                             background_color=message_background_color,
                                             use_terminal_colors=use_terminal_colors)
        self.warning_colors = TerminalColors(foreground_color=warning_foreground_color,
                                             background_color=warning_background_color,
                                             use_terminal_colors=use_terminal_colors)
        self.all_targets = list()

    def update(self, line):
        mfc = self.message_colors.foreground_color
        mbc = self.message_colors.background_color
        mrc = self.message_colors.reset_colors
        wfc = self.warning_colors.foreground_color
        wbc = self.warning_colors.background_color
        wrc = self.warning_colors.reset_colors
        if match := match_consider(line):
            target = match.group(1)
            self.rule = target
            self.analyse = True
        elif match := match_implicit_rule(line, self.rule):
            target = match.group(1)
            self.analyse = False
        elif match := match_must_remake(line, self.rule):
            target = match.group(1)
        else:
            target = None

        if target is not None and target not in self.all_targets:
            self.all_targets.append(target)
            target = Path(match.group(1))
            if not target.exists():
                if target.suffix != "":
                    self.missing_counter += 1
                    print(f"{wfc}{wbc}" + f"Missing target: {target}" + f"{wrc}")
                else:
                    _logger.debug(f"Found rule {target}")
            elif target.as_posix().lower() != "makefile":
                print(f"{mfc}{mbc}" + f"Found source/target: {target}" + f"{mrc}")

        if self.analyse:
            pass


def check_make_file(dryrun=False,
                    target=None,
                    message_foreground_color=None,
                    message_background_color=None,
                    warning_foreground_color=None,
                    warning_background_color=None,
                    use_terminal_colors=True,
                    ):
    """
    Functie die the make file checks
    Args:
        dryrun: bool
            Doe geen echt check, maar laat alleen de make commando's zien
        target: str
            Specificeer de makefile rule om te checken
        message_foreground_color: str
            Kleur van de voorgrond boodschappen
        message_background_color:
            Kleur van de achtergrond boodschappen
        warning_foreground_color:
            Kleur van de voorgrond waarschuwwing
        warning_background_color:
            Kleur van de achtergrond waarschuwingen
        use_terminal_colors: bool
            Gebruik de terminalkleuren

    Returns:
        None

    """

    make_cmd = []

    if dryrun:
        make_cmd.append("echo")

    make_cmd.append("make")
    make_cmd.append("-Bdn")

    if target is not None:
        make_cmd.append(target)

    _logger.info("Running {}".format(" ".join(make_cmd)))

    try:
        # probeer eerst make op de command line te runnen
        process = subprocess.Popen(make_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False)
    except FileNotFoundError as err:
        # als dit niet lukt proberen we het nog eens maar nu met 'gmake'
        make_cmd = [a.replace("make", "gmake") for a in make_cmd]
        process = subprocess.Popen(make_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False)

    out, err = process.communicate()
    checker = CheckRule(
        message_foreground_color=message_foreground_color,
        message_background_color=message_background_color,
        warning_foreground_color=warning_foreground_color,
        warning_background_color=warning_background_color,
        use_terminal_colors=use_terminal_colors,

    )
    clean_lines = out.decode().split("\n")
    for line in clean_lines:

        if checker is not None:
            checker.update(line.strip())

    return checker.missing_counter


def main(args):
    """Wrapper allowing :func:`fib` to be called with string arguments in a CLI fashion

    Instead of returning the value from :func:`fib`, it prints the result to the
    ``stdout`` in a nicely formatted message.

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--verbose", "42"]``).
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    _logger.debug("Starting make file check...")
    missing = check_make_file(dryrun=args.test,
                              target=args.target,
                              message_foreground_color=args.message_foreground_color,
                              message_background_color=args.message_background_color,
                              warning_foreground_color=args.warning_foreground_color,
                              warning_background_color=args.warning_background_color,
                              use_terminal_colors=args.use_terminal_colors)
    if missing == 0:
        print("All done")
    else:
        if missing == 1:
            files = "file"
        else:
            files = "files"
        print(f"We missen {missing} {files}")

    _logger.info("Done make2check!")


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html

    # After installing your project with pip, users can also run your Python
    # modules as scripts via the ``-m`` flag, as defined in PEP 338::
    #
    #     python -m make2check.skeleton 42
    #
    run()
