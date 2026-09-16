#!/usr/bin/env python3

"""Cross-platform build script for packaging java-inventory as a standalone executable."""

import argparse
import shutil
import sys
from pathlib import Path

from common.inventory_common import (
    InventoryError,
    error,
    info,
    require_directory,
    run,
    set_debug,
    success,
)

EXECUTABLE_NAME = "java-inventory"
DEFAULT_SPEC = "java_inventory.spec"
VENV_DIRECTORY = "venv"
REQUIRED_DIRECTORIES = (
    ("checkstyle/target", "Checkstyle build output"),
    ("maven/target", "Maven build output"),
)


def venv_python(project_root: Path) -> Path:
    """Return the Python executable inside the build virtual environment."""
    if sys.platform == "win32":
        return project_root / VENV_DIRECTORY / "Scripts" / "python.exe"
    return project_root / VENV_DIRECTORY / "bin" / "python"


def create_venv(project_root: Path) -> Path:
    """Create the build virtual environment if it does not exist."""
    python = venv_python(project_root)

    if python.is_file():
        info(f"using existing virtual environment: {VENV_DIRECTORY}")
        return python
    info(f"creating virtual environment: {VENV_DIRECTORY}")

    run(
        [
            sys.executable,
            "-m",
            "venv",
            str(project_root / VENV_DIRECTORY),
        ],
        cwd=project_root,
    )

    if not python.is_file():
        raise InventoryError(
            f"virtual environment was created but python was not found: {python}"
        )

    success("virtual environment created")
    return python


def ensure_pyinstaller(python: Path) -> None:
    """Install PyInstaller in the build virtual environment if necessary."""
    result = run(
        [
            str(python),
            "-m",
            "PyInstaller",
            "--version",
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode == 0:
        info("PyInstaller is already installed")
        return

    info("installing PyInstaller")

    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "pyinstaller",
        ],
        capture_output=False,
    )
    success("PyInstaller installed")


def clean_builds(project_root: Path) -> None:
    """Remove previous PyInstaller build artifacts."""
    info("cleaning previous builds")

    paths = (
        project_root / "build",
        project_root / "dist",
        project_root / "__pycache__",
        project_root / "bin",
        project_root / "venv",
        project_root / "checkstyle" / "target",
        project_root / "maven" / "target",
    )

    for path in paths:
        if path.is_dir():
            shutil.rmtree(path)
            info(f"removed: {path}")

    for path in project_root.glob("*.spec.bak"):
        if path.is_file():
            path.unlink()
            info(f"removed: {path}")

    for path in project_root.glob("*.egg-info"):
        if path.is_dir():
            shutil.rmtree(path)
            info(f"removed: {path}")


def run_setup(project_root: Path) -> None:
    """Run java_inventory setup to build required Java artifacts."""
    run(
        [
            sys.executable,
            str(project_root / "java_inventory.py"),
            "setup",
        ],
        cwd=project_root,
    )
    success("java_inventory setup completed")


def validate_build_outputs(project_root: Path) -> None:
    """Validate that all required build outputs exist."""
    info("validating required build outputs")

    for relative_path, description in REQUIRED_DIRECTORIES:
        require_directory(
            project_root / relative_path,
            description,
        )

    success("required build outputs found")


def build_executable(project_root: Path, spec_file: Path) -> None:
    """Build the executable using PyInstaller."""
    info("building executable with PyInstaller")

    run(
        [
            venv_python(project_root),
            "-m",
            "PyInstaller",
            str(spec_file),
        ],
        cwd=project_root,
    )

    success("PyInstaller build completed")


def find_executable(dist_dir: Path) -> Path:
    """Find the built executable."""
    filename = f"{EXECUTABLE_NAME}.exe" if sys.platform == "win32" else EXECUTABLE_NAME

    executable = dist_dir / filename

    if not executable.is_file():
        raise InventoryError(
            f"Build completed but executable was not found: {executable}"
        )

    return executable


def format_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable size."""
    size = float(size_bytes)

    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} TB"


def report_success(executable: Path) -> None:
    """Print information about the generated executable."""
    size = format_size(executable.stat().st_size)

    success("build successful")
    info(f"executable: {executable} ({size})")
    info(f"to run: {executable.name} --help")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build java-inventory as a standalone executable"
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleaning previous PyInstaller build artifacts",
    )

    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help=f"Path to PyInstaller spec file (default: {DEFAULT_SPEC})",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )

    return parser.parse_args()


def main() -> int:
    """Build java-inventory."""
    args = parse_arguments()
    set_debug(args.debug)

    project_root = Path(__file__).resolve().parent
    spec_file = args.spec or (project_root / DEFAULT_SPEC)

    if not spec_file.is_absolute():
        spec_file = project_root / spec_file

    try:
        if not spec_file.is_file():
            raise InventoryError(f"spec file not found: {spec_file}")

        if not args.no_cleanup:
            clean_builds(project_root)

        python = create_venv(project_root)
        ensure_pyinstaller(python)

        run_setup(project_root)
        validate_build_outputs(project_root)

        build_executable(project_root, spec_file)

        executable = find_executable(project_root / "dist")
        report_success(executable)

        return 0

    except InventoryError as exc:
        error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
