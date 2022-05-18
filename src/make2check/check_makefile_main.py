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
import sys
import re
import subprocess
from pathlib import Path

from make2check import __version__

__author__ = "Eelco van Vliet"
__copyright__ = "Eelco van Vliet"
__license__ = "MIT"

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
    def __init__(self):
        self.rule = None
        self.analyse = False
        self.missing_counter = 0

        self.all_targets = list()

    def update(self, line):
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
            if not target.exists() and target.suffix != "":
                self.missing_counter += 1
                print(f"Missing target: {target}")
            else:
                _logger.info(f"Target {target} already there!")

        if self.analyse:
            pass


def check_make_file(dryrun=False):
    """
    Functie die the make file checks

    Returns: int
        Integer
    """

    make_cmd = []

    if dryrun:
        make_cmd.append("echo")

    make_cmd.append("make")
    make_cmd.append("-Bdn")

    _logger.info("Running {}".format(" ".join(make_cmd)))

    process = subprocess.Popen(make_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=False)
    out, err = process.communicate()
    start_analyse = False
    analyse = {}
    checker = None
    checker = CheckRule()
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
    missing = check_make_file(dryrun=args.test)
    if missing == 0:
        print("All done")
    else:
        print(f"We missen {missing} files")

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
