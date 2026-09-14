#!/usr/bin/env python3

"""Master CLI for the Java inventory utilities."""

# pylint: disable=missing-function-docstring

import argparse
import importlib.util
import sys
from pathlib import Path

from common.inventory_common import error, require_command, run, set_debug

ROOT = Path(__file__).resolve().parent

# Make the repository root importable so modules can share common utilities.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def subcommand_setup(_args, root: Path):
    require_command("git")
    require_command("mvn")
    run(["git", "submodule", "update", "--init", "--recursive"], cwd=root)


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

    checkstyle.register_commands(subparsers, ROOT, setup_handlers)
    maven.register_commands(subparsers, ROOT, setup_handlers)

    setup.set_defaults(setup_handlers=setup_handlers)

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

        args.handler(args)
        return 0
    except Exception as exc:  # pylint: disable=broad-exception-caught # noqa: BLE001
        error(str(exc), force=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
