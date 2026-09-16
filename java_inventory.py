#!/usr/bin/env python3

"""Master CLI for the Java inventory utilities."""

# pylint: disable=missing-function-docstring

import argparse
import importlib.util
import sys
import textwrap
import tomllib
from pathlib import Path

from common.inventory_common import error, require_command, set_debug

ROOT = Path(__file__).resolve().parent

# Make the repository root importable so modules can share common utilities.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def project_metadata() -> dict:
    """Load project metadata from pyproject.toml."""
    with (ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)["project"]


def load_module(name: str, path: Path):
    """Load a Python module from a path without requiring package layout."""
    if not path.is_file():
        raise FileNotFoundError(f"inventory module not found: {path}")

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load inventory module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def subcommand_setup(_args, _root: Path):
    require_command("git")
    require_command("mvn")


def subcommand_version(_args):
    metadata = project_metadata()
    print(f"{metadata['name']} {metadata['version']}")


def subcommand_about(_args):
    metadata = project_metadata()
    name = metadata["name"]
    version = metadata["version"]
    description = metadata["description"]
    authors = metadata.get("authors", [])
    license_info = metadata.get("license", {})
    urls = metadata.get("urls", {})

    print(f"{name} {version}")
    print()
    print(textwrap.fill(description, width=80))
    print()
    if authors:
        print(f"Author:       {authors[0]['name']}")
    if license_info:
        print(f"License:      {license_info}")
    if "Repository" in urls:
        print(f"Repository:   {urls['Repository']}")
    if "Issues" in urls:
        print(f"Issues:       {urls['Issues']}")
    print()
    print(f"Run '{name} --help' for help.")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="java_inventory.py",
        description="Java inventory and development tools",
    )
    parser.add_argument("--debug", action="store_true", help="show debug logs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_handlers = [lambda args: subcommand_setup(args, ROOT)]

    checkstyle = load_module(
        "java_inventory_checkstyle",
        ROOT / "checkstyle" / "src" / "main" / "python" / "checkstyle_inventory.py",
    )
    maven = load_module(
        "java_inventory_maven",
        ROOT / "maven" / "src" / "main" / "python" / "maven_inventory.py",
    )

    setup = subparsers.add_parser(
        "setup",
        help="set up all inventory components",
    )

    info = subparsers.add_parser(
        "about",
        help="show tool information and available commands",
    )

    version = subparsers.add_parser(
        "version",
        help="show the tool version",
    )

    checkstyle.register_commands(subparsers, ROOT, setup_handlers)
    maven.register_commands(subparsers, ROOT, setup_handlers)

    setup.set_defaults(setup_handlers=setup_handlers)
    info.set_defaults(handler=subcommand_about)
    version.set_defaults(handler=subcommand_version)

    return parser


def main() -> int:
    try:
        parser = build_parser()
        args = parser.parse_args()

        set_debug(args.debug)

        if args.command == "setup":
            for handler in args.setup_handlers:
                handler(args)
            return 0

        if args.command == "info":
            subcommand_about(args)
            return 0

        args.handler(args)
        return 0
    except Exception as exc:  # pylint: disable=broad-exception-caught # noqa: BLE001
        error(str(exc), force=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
