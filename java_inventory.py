#!/usr/bin/env python3

"""Build and development tool for the Java inventory utilities."""

# pylint: disable=missing-class-docstring, missing-function-docstring, too-few-public-methods

import argparse
import csv
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RESOURCES_DIR = ROOT / "resources"
BUILD_DIR = ROOT / "build"

CHECKSTYLE_JAR = RESOURCES_DIR / "checkstyle-12.3.0-all.jar"
CHECKS_JAR = BUILD_DIR / "java-inventory-checkstyle-checks.jar"
CONFIGS_DIR = RESOURCES_DIR / "configs"
PACKAGE_CONFIG = RESOURCES_DIR / "checkstyle_packages.xml"
CHECKSTYLE_STYLE_GUIDE = RESOURCES_DIR / "style_guide.xml"

METHOD_CONFIG = CONFIGS_DIR / "method_inventory_check_config.xml"
REST_API_CONFIG = CONFIGS_DIR / "rest_api_inventory_check_config.xml"

CHECK_CLASSES = (
    "MethodInventoryCheck",
    "RestApiInventoryCheck",
)


class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


def color_enabled():
    if os.environ.get("NO_COLOR") is not None:
        return False

    if os.environ.get("FORCE_COLOR") is not None:
        return os.environ["FORCE_COLOR"] != "0"

    return sys.stdout.isatty()


USE_COLOR = color_enabled()
DEBUG = False


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


def log(level: str, message: str, **kwargs):
    force = kwargs.get("force", False)

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
    command: list[str], *, cwd: Path = ROOT, capture_output: bool = False, check=True
) -> subprocess.CompletedProcess[str]:
    formatted = " ".join(shlex.quote(str(arg)) for arg in command)
    info(f"running: {formatted}")

    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=check,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError:
        error(f"command not found: {command[0]}")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        error(f"command failed with exit code {exc.returncode}")

        if exc.stdout:
            print(exc.stdout, end="")

        if exc.stderr:
            print(exc.stderr, end="", file=sys.stderr)

        sys.exit(exc.returncode)


def require_command(command: str):
    if shutil.which(command) is None:
        error(f"required command not found: {command}")
        sys.exit(1)


def require_file(path: Path, description: str):
    if not path.is_file():
        error(f"{description} not found: {path}")
        sys.exit(1)


def require_directory(path: Path, description: str):
    if not path.exists():
        error(f"{description} does not exist: {path}")
        sys.exit(1)

    if not path.is_dir():
        error(f"{description} is not a directory: {path}")
        sys.exit(1)


def java_source_file(class_name: str) -> Path:
    return ROOT / "src" / "main" / "java" / "fun" / "ninth" / f"{class_name}.java"


def classpath() -> str:
    return os.pathsep.join(
        [
            str(CHECKSTYLE_JAR),
            str(CHECKS_JAR),
        ]
    )


def check_common_requirements():
    for command in ("java", "javac", "jar"):
        require_command(command)

    require_file(CHECKSTYLE_JAR, "Checkstyle JAR")
    require_file(PACKAGE_CONFIG, "Checkstyle package configuration")

    require_file(METHOD_CONFIG, "method inventory configuration")
    require_file(REST_API_CONFIG, "REST API inventory configuration")


def initialize_checkstyle_check(class_name: str):
    source_file = java_source_file(class_name)

    require_file(source_file, f"Checkstyle source file for {class_name}")

    run(
        [
            "javac",
            "-cp",
            str(CHECKSTYLE_JAR),
            "-d",
            str(BUILD_DIR),
            str(source_file),
        ]
    )

    info(f"compiled '{source_file}'")


def build_checkstyle_checks():
    check_common_requirements()

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    info(f"initialized build directory: {BUILD_DIR}")

    for class_name in CHECK_CLASSES:
        initialize_checkstyle_check(class_name)

    run(
        [
            "jar",
            "cf",
            str(CHECKS_JAR),
            "-C",
            str(BUILD_DIR),
            "fun/ninth",
            "-C",
            str(RESOURCES_DIR),
            "checkstyle_packages.xml",
        ]
    )

    success(f"generated '{CHECKS_JAR}'")


def ensure_checks_jar():
    if not CHECKS_JAR.is_file():
        error(f"compiled Checkstyle JAR not found: {CHECKS_JAR}")
        error("run the 'build' command first")
        sys.exit(1)


def run_checkstyle(
    config_file: Path,
    target_dir: Path,
) -> str:
    ensure_checks_jar()

    require_file(config_file, "Checkstyle configuration")
    require_directory(target_dir, "target directory")

    result = run(
        [
            "java",
            "-cp",
            classpath(),
            "com.puppycrawl.tools.checkstyle.Main",
            "-c",
            str(config_file),
            str(target_dir),
        ],
        capture_output=True,
    )

    return result.stdout


def generate_rest_api_report(source_dir: Path, output_file: Path):
    output = run_checkstyle(REST_API_CONFIG, source_dir)

    rest_api_re = re.compile(
        r"\[DEBUG]\s+\[REST-API Inventory Check]\s+"
        r"([A-Za-z0-9_]+)\s+"
        r"(GET|POST|PUT|DELETE|PATCH)\s+"
        r'(\S+)\s+"([^"]+)"'
    )

    rows = []

    for line in output.splitlines():
        match = rest_api_re.search(line)

        if match:
            class_name, method, endpoint, description = match.groups()
            rows.append([class_name, method, endpoint, description])

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["class", "method", "endpoint", "description"])
        writer.writerows(rows)

    success(f"CSV report generated '{output_file}'")
    info(f"REST APIs found: {len(rows)}")


METHOD_RE = re.compile(
    r"\[DEBUG]\s+\[Method Inventory Check]\s+"
    r"([A-Za-z0-9_]+)\s+([A-Za-z0-9_$.]+)\s+([A-Za-z0-9_]+)"
)

MISSING_CLASS_KEY = "missingClass"
MISSING_METHODS_KEY = "missingMethods"


def collect_methods(output: str):
    result = defaultdict(set)

    for line in output.splitlines():
        match = METHOD_RE.search(line)

        if match:
            class_name, class_path, method_name = match.groups()
            result[(class_path, class_name)].add(method_name)

    return result


def generate_html_report(
    missing_tests: dict,
    source_methods: dict,
    output_file: Path,
):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Test-Coverage Report</title>

<style>
    body {{
        font-family: Arial, sans-serif;
        font-size: 14px;
        margin: 20px;
        background-color: #f9f9f9;
    }}

    h1 {{
        font-size: 20px;
    }}

    table {{
        border-collapse: collapse;
        width: 100%;
    }}

    th, td {{
        border: 1px solid #ccc;
        padding: 6px 10px;
        text-align: left;
    }}

    th {{
        background-color: #eee;
    }}

    tr.failed {{
        background-color: #f8d7da;
        cursor: pointer;
    }}

    tr.passed {{
        background-color: #d4edda;
        cursor: pointer;
    }}

    tr.details {{
        display: none;
        background-color: #fff3cd;
    }}
</style>

<script>
function toggleRow(id) {{
    var row = document.getElementById(id);
    row.style.display =
        (row.style.display === 'table-row') ? 'none' : 'table-row';
}}
</script>

</head>

<body>
<h1>Test-Coverage Report</h1>

<p>Total classes analyzed: {len(source_methods)}</p>

<table>
<tr>
    <th>Class</th>
    <th>Classpath</th>
    <th>Missing Methods</th>
</tr>
"""

    sorted_classes = sorted(
        source_methods.keys(),
        key=lambda key: (
            key not in missing_tests,
            key[0],
            key[1],
        ),
    )

    for index, (class_path, class_name) in enumerate(sorted_classes):
        missing_test_entry = missing_tests.get(
            (class_path, class_name),
            {
                MISSING_CLASS_KEY: False,
                MISSING_METHODS_KEY: [],
            },
        )

        missing_count = len(missing_test_entry[MISSING_METHODS_KEY])

        row_class = "failed" if missing_count > 0 else "passed"
        details_id = f"details_{index}"

        html += f"""
<tr class="{row_class}" onclick="toggleRow('{details_id}')">
    <td>{class_name}</td>
    <td>{class_path}.{class_name}</td>
    <td>{missing_count}</td>
</tr>

<tr id="{details_id}" class="details">
    <td colspan="3">
"""

        if missing_count > 0:
            html += "<b>Unit-Test-Methods missing in the Test-Class:</b><ul>"

            for method in missing_test_entry[MISSING_METHODS_KEY]:
                html += f"<li>{method}</li>"

            html += "</ul>"
        else:
            html += "<b>No unit-test-methods missing in the Test-Class.</b><br>"

        html += "<b>Methods present in Original-Class:</b><ul>"

        for method in sorted(source_methods[(class_path, class_name)]):
            html += f"<li>{method}</li>"

        html += "</ul></td></tr>"

    html += """
</table>
</body>
</html>
"""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file:
        file.write(html)

    success(f"HTML report generated '{output_file}'")


def generate_test_coverage_report(
    source_dir: Path,
    test_dir: Path,
    output_file: Path,
):
    source_output = run_checkstyle(METHOD_CONFIG, source_dir)
    test_output = run_checkstyle(METHOD_CONFIG, test_dir)

    source_methods = collect_methods(source_output)
    test_methods = collect_methods(test_output)

    missing_tests = {}

    for (class_path, class_name), methods in source_methods.items():
        test_class_key = (
            class_path,
            f"{class_name}Test",
        )

        if test_class_key not in test_methods:
            missing_tests[(class_path, class_name)] = {
                MISSING_CLASS_KEY: True,
                MISSING_METHODS_KEY: sorted(methods),
            }

            continue

        expected_tests = {f"test{method[0].upper()}{method[1:]}" for method in methods}

        actual_tests = {
            f"test{method[0].upper()}{method[1:]}"
            for method in methods
            for test_method in test_methods[test_class_key]
            if test_method.startswith(f"test{method[0].upper()}{method[1:]}")
        }

        missing = sorted(expected_tests - actual_tests)

        if missing:
            missing_tests[(class_path, class_name)] = {
                MISSING_CLASS_KEY: False,
                MISSING_METHODS_KEY: missing,
            }

    if not missing_tests:
        success("no unit tests missing in any of the classes")
    else:
        warning("missing unit tests:")

        for class_path, class_name in missing_tests:
            info(f"- {class_name}")

    generate_html_report(
        missing_tests,
        source_methods,
        output_file,
    )


def run_git(*args: str, cwd: Path = ROOT) -> str:
    result = run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
    )
    return result.stdout


# pylint: disable=too-many-branches
def get_changed_lines(
    git_dir: Path,
    cached: bool = False,
    include_untracked: bool = False,
):
    """Return changed Java files/lines as (filepath, line_or_none) tuples.

    A line number identifies a changed line in a modified file. None identifies
    an added file, for which the entire file should be analyzed.
    """
    diff_commands = [["diff", "--unified=0", "--no-color"]]
    if cached:
        diff_commands.append(["diff", "--cached", "--unified=0", "--no-color"])

    changed = []
    file = None
    added_file = False

    for diff_command in diff_commands:
        diff = run_git(*diff_command, cwd=git_dir)
        for line in diff.splitlines():
            if line.startswith("diff --git "):
                file = None
                added_file = False

            elif line.startswith("--- /dev/null"):
                added_file = True

            elif line.startswith("+++ b/"):
                file = line[6:]

                if added_file:
                    changed.append((file, None))

            elif line.startswith("@@") and file and not added_file:
                match = re.search(r"\+(\d+)(?:,(\d+))?", line)
                if not match:
                    continue

                start = int(match.group(1))
                count = int(match.group(2) or 1)

                for line_no in range(start, start + count):
                    changed.append((file, line_no))

    if include_untracked:
        for file in run_git(
            "ls-files",
            "--others",
            "--exclude-standard",
            cwd=git_dir,
        ).splitlines():
            if file:
                changed.append((file, None))

    return changed


def run_checkstyle_file(file: Path):
    """Run Checkstyle for one Java file and return (output, exit_code)."""
    ensure_checks_jar()

    require_file(CHECKSTYLE_STYLE_GUIDE, "Checkstyle configuration")
    require_file(file, "Java source file")

    result = run(
        [
            "java",
            "-cp",
            classpath(),
            "com.puppycrawl.tools.checkstyle.Main",
            "-c",
            str(CHECKSTYLE_STYLE_GUIDE),
            str(file),
        ],
        capture_output=True,
        check=False,
    )

    return result.stdout + result.stderr, result.returncode


def parse_checkstyle_violation(line: str):
    """Return (file, line, column, severity, message) for a Checkstyle line."""
    match = re.match(
        r"^\[(WARN|ERROR)\]\s+(.*):(\d+):(\d+):\s*(.*)$",
        line,
    )
    if not match:
        return None

    severity, file, row, column, message = match.groups()

    return (
        file,
        int(row),
        int(column),
        "warning" if severity == "WARN" else "error",
        message,
    )


def parse_checkstyle_exception(output: str):
    """Return the deepest Checkstyle exception with a message."""
    exceptions = re.findall(
        r"Caused by:\s+([\w.$]+)(?::\s+(.*))?",
        output,
    )

    for exception, message in reversed(exceptions):
        if message:
            return exception, message

    return None


# pylint: disable=too-many-locals
def subcommand_changed_lines(
    git_dir: Path,
    cached: bool,
    include_untracked: bool,
    run_checkstyle: bool,  # pylint: disable=redefined-outer-name
):
    """Show changed Java lines, optionally filtered through Checkstyle."""
    changed = get_changed_lines(
        git_dir=git_dir,
        cached=cached,
        include_untracked=include_untracked,
    )

    if not run_checkstyle:
        for file, line_no in changed:
            if line_no is None:
                print(file)
            else:
                print(f"{file}:{line_no}")
        return

    changed_by_file = defaultdict(set)
    whole_files = set()

    for file, line_no in changed:
        if line_no is None:
            whole_files.add(file)
        else:
            changed_by_file[file].add(line_no)

    warn_count = 0
    error_count = 0
    diagnostics = []

    for file in sorted(set(changed_by_file) | whole_files):
        source_file = git_dir / file

        if not source_file.is_file():
            continue

        if source_file.suffix.lower() != ".java":
            warning(f"ignoring '{source_file}'")
            continue

        output, exit_code = run_checkstyle_file(source_file)

        violations = []
        for line in output.splitlines():
            violation = parse_checkstyle_violation(line)
            if violation:
                violations.append(violation)

        if exit_code != 0 and not violations:
            exception = parse_checkstyle_exception(output)

            if exception:
                exception_name, message = exception
                diagnostics.append(
                    f"{colored('error')}: {file}: {exception_name}: {message}"
                )
            else:
                diagnostics.append(
                    f"{colored('error')}: {file}: Checkstyle failed to analyze the file."
                )

            error_count += 1
            continue

        for violation_file, row, column, severity, message in violations:
            # Checkstyle may report an absolute path while the diff uses a
            # repository-relative path.
            try:
                reported_file = (
                    Path(violation_file)
                    .resolve()
                    .relative_to(git_dir.resolve())
                    .as_posix()
                )
            except ValueError:
                reported_file = Path(violation_file).as_posix()

            if reported_file != file:
                continue

            if file not in whole_files and row not in changed_by_file[file]:
                continue

            diagnostics.append(f"{colored(severity)}: {file}:{row}:{column}: {message}")

            if severity == "warning":
                warn_count += 1
            else:
                error_count += 1

    print("\n".join(diagnostics))
    info(
        f"checkstyle summary: {error_count} error(s), {warn_count} warning(s).",
        force=True,
    )


def subcommand_setup():
    require_command("git")

    info("initializing git submodules")

    run(
        [
            "git",
            "submodule",
            "update",
            "--init",
            "--recursive",
        ]
    )

    check_common_requirements()

    success("project setup complete")


def subcommand_build():
    build_checkstyle_checks()


def subcommand_inventory_method(
    source_dir: Path,
    output_file: Path | None,
):
    require_directory(source_dir, "source directory")

    output = run_checkstyle(METHOD_CONFIG, source_dir)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output, encoding="utf-8")
        success(f"method inventory generated '{output_file}'.")
    else:
        print(output, end="")


def subcommand_inventory_rest_api(
    source_dir: Path,
    output_file: Path,
):
    require_directory(source_dir, "source directory")
    generate_rest_api_report(source_dir, output_file)


def subcommand_test_coverage(
    source_dir: Path,
    test_dir: Path,
    output_file: Path,
):
    require_directory(source_dir, "source directory")
    require_directory(test_dir, "test directory")

    generate_test_coverage_report(
        source_dir,
        test_dir,
        output_file,
    )


def main():
    global DEBUG  # pylint: disable=global-statement

    parser = argparse.ArgumentParser(
        prog="java_inventory.py",
        description="Java inventory and test-coverage development tool",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="show debug logs",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "setup",
        help="initialize git submodules and validate dependencies",
    )

    subparsers.add_parser(
        "build",
        help="compile and package custom Checkstyle checks",
    )

    changed_lines_parser = subparsers.add_parser(
        "lint",
        help="run Checkstyle on changed Java lines",
    )

    changed_lines_parser.add_argument(
        "git_dir",
        type=Path,
        help="Git repository directory",
    )

    changed_lines_parser.add_argument(
        "--cached",
        action="store_true",
        help="analyze staged changes instead of unstaged working-tree changes",
    )

    changed_lines_parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="include untracked Java files as whole-file changes",
    )

    changed_lines_parser.add_argument(
        "--no-checkstyle",
        action="store_true",
        help="only show changed Java files and lines without running Checkstyle",
    )

    method_parser = subparsers.add_parser(
        "inventory-method",
        help="generate a method inventory",
    )

    method_parser.add_argument(
        "source_dir",
        type=Path,
        help="Java source directory",
    )

    method_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="optional output file",
    )

    rest_parser = subparsers.add_parser(
        "inventory-rest-api",
        help="generate a REST API inventory CSV",
    )

    rest_parser.add_argument(
        "source_dir",
        type=Path,
        help="Java source directory",
    )

    rest_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=BUILD_DIR / "rest_apis.csv",
        help="output CSV file",
    )

    coverage_parser = subparsers.add_parser(
        "test-coverage",
        help="generate the test-coverage report",
    )

    coverage_parser.add_argument(
        "source_dir",
        type=Path,
        help="Java source directory",
    )

    coverage_parser.add_argument(
        "test_dir",
        type=Path,
        help="Java test directory",
    )

    coverage_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=BUILD_DIR / "test_coverage_report.html",
        help="output HTML report",
    )

    args = parser.parse_args()

    DEBUG = args.debug

    match args.command:
        case "setup":
            subcommand_setup()

        case "build":
            subcommand_build()

        case "lint":
            subcommand_changed_lines(
                git_dir=args.git_dir.resolve(),
                cached=args.cached,
                include_untracked=args.include_untracked,
                run_checkstyle=not args.no_checkstyle,
            )

        case "inventory-method":
            subcommand_inventory_method(
                args.source_dir.resolve(),
                args.output.resolve() if args.output else None,
            )

        case "inventory-rest-api":
            subcommand_inventory_rest_api(
                args.source_dir.resolve(),
                args.output.resolve(),
            )

        case "test-coverage":
            subcommand_test_coverage(
                args.source_dir.resolve(),
                args.test_dir.resolve(),
                args.output.resolve(),
            )


if __name__ == "__main__":
    main()
