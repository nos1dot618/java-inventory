"""Shared utilities for java-inventory commands."""


# pylint: disable=missing-class-docstring, missing-function-docstring, too-few-public-methods

import os
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEBUG = False


class InventoryError(Exception):
    """Base exception for expected inventory-tool failures."""


class CommandNotFoundError(InventoryError):
    """Raised when an external command is unavailable."""


class CommandExecutionError(InventoryError):
    """Raised when an external command fails."""

    def __init__(self, command, returncode, stdout="", stderr=""):
        self.command = list(command)
        self.returncode = returncode
        self.stdout = stdout or ""
        self.stderr = stderr or ""
        formatted = " ".join(shlex.quote(str(arg)) for arg in command)
        super().__init__(f"command failed with exit code {returncode}: {formatted}")


class MissingFileError(InventoryError):
    """Raised when a required file is missing."""


class MissingDirectoryError(InventoryError):
    """Raised when a required directory is missing or invalid."""


class UnsupportedBuildToolError(InventoryError):
    """Raised when a project uses an unsupported build system."""


# pylint: disable=global-statement
def set_debug(enabled: bool):
    global DEBUG
    DEBUG = enabled


def color_enabled():
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") is not None:
        return os.environ["FORCE_COLOR"] != "0"
    return sys.stdout.isatty()


USE_COLOR = color_enabled()


class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


def colored(level: str) -> str:
    colors = {
        "info": Colors.BLUE,
        "error": Colors.RED,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
    }
    if USE_COLOR:
        return f"{colors.get(level, '')}{level}{Colors.RESET}"
    return level


def log(level: str, message: str, *, force=False):
    if not DEBUG and not force:
        return
    print(f"{colored(level)}: {message}")


def info(message: str, **kwargs):
    log("info", message, **kwargs)


def error(message: str, **kwargs):
    log("error", message, **kwargs)


def success(message: str, **kwargs):
    log("success", message, **kwargs)


def warning(message: str, **kwargs):
    log("warning", message, **kwargs)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    check=True,
) -> subprocess.CompletedProcess[str]:
    formatted = " ".join(shlex.quote(str(arg)) for arg in command)
    info(f"running: {formatted}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:
        raise CommandNotFoundError(f"command not found: {command[0]}") from exc

    if check and result.returncode != 0:
        raise CommandExecutionError(
            command, result.returncode, result.stdout, result.stderr
        )
    return result


def require_command(command: str):
    if shutil.which(command) is None:
        raise CommandNotFoundError(f"required command not found: {command}")


def require_file(path: Path, description: str):
    if not path.is_file():
        raise MissingFileError(f"{description} not found: {path}")


def require_directory(path: Path, description: str):
    if not path.exists():
        raise MissingDirectoryError(f"{description} does not exist: {path}")
    if not path.is_dir():
        raise MissingDirectoryError(f"{description} is not a directory: {path}")


def read_pom_coordinates(pom: Path) -> tuple[str, str]:
    root = ET.parse(pom).getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}

    artifact_id = root.findtext("m:artifactId", namespaces=ns)
    version = root.findtext("m:version", namespaces=ns)

    if not artifact_id or not version:
        raise InventoryError(f"Unable to determine artifact coordinates from {pom}")

    return artifact_id, version
