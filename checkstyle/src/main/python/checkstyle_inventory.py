"""Checkstyle-based Java inventory commands."""

# pylint: disable=missing-function-docstring

import csv
import re
from collections import defaultdict
from pathlib import Path

from common.inventory_common import (
    colored,
    info,
    read_pom_coordinates,
    require_command,
    require_directory,
    require_file,
    run,
    success,
    warning,
)

CHECKSTYLE_JAR = None
CHECKS_JAR = None
CONFIGS_DIR = None
PACKAGE_CONFIG = None
CHECKSTYLE_STYLE_GUIDE = None
METHOD_CONFIG = None
REST_API_CONFIG = None

CHECK_CLASSES = ("MethodInventoryCheck", "RestApiInventoryCheck")


# pylint: disable=global-statement
def configure(root: Path):
    global CHECKSTYLE_JAR, CHECKS_JAR, CONFIGS_DIR, PACKAGE_CONFIG
    global CHECKSTYLE_STYLE_GUIDE, METHOD_CONFIG, REST_API_CONFIG
    CHECKSTYLE_JAR = root / "resources" / "checkstyle-12.3.0-all.jar"
    artifact_id, version = read_pom_coordinates(root / "checkstyle" / "pom.xml")
    CHECKS_JAR = root / "checkstyle" / "target" / f"{artifact_id}-{version}.jar"
    CONFIGS_DIR = root / "resources" / "configs"
    PACKAGE_CONFIG = root / "resources" / "checkstyle_packages.xml"
    CHECKSTYLE_STYLE_GUIDE = root / "resources" / "style_guide.xml"
    METHOD_CONFIG = CONFIGS_DIR / "method_inventory_check_config.xml"
    REST_API_CONFIG = CONFIGS_DIR / "rest_api_inventory_check_config.xml"


def check_common_requirements():
    require_command("java")
    require_command("mvn")
    require_file(PACKAGE_CONFIG, "Checkstyle package configuration")
    require_file(METHOD_CONFIG, "method inventory configuration")
    require_file(REST_API_CONFIG, "REST API inventory configuration")


def build_checkstyle_checks(root: Path):
    configure(root)
    check_common_requirements()
    run(["mvn", "package", "-q"], cwd=root / "checkstyle")
    require_file(CHECKS_JAR, "Checkstyle inventory JAR")
    success(f"generated '{CHECKS_JAR}'")


def ensure_checks_jar():
    require_file(CHECKS_JAR, "compiled Checkstyle JAR")


def run_checkstyle(config_file: Path, target_dir: Path) -> str:
    ensure_checks_jar()
    require_file(config_file, "Checkstyle configuration")
    require_directory(target_dir, "target directory")
    result = run(
        ["java", "-jar", str(CHECKS_JAR), "-c", str(config_file), str(target_dir)],
        capture_output=True,
    )
    return result.stdout


def generate_rest_api_report(source_dir: Path, output_file: Path):
    output = run_checkstyle(REST_API_CONFIG, source_dir)
    rest_api_re = re.compile(
        r"\[DEBUG]\s+\[REST-API Inventory Check]\s+"
        r"([A-Za-z0-9_]+)\s+(GET|POST|PUT|DELETE|PATCH)\s+(\S+)\s+\"([^\"]+)\""
    )
    rows = []
    for line in output.splitlines():
        match = rest_api_re.search(line)
        if match:
            rows.append(list(match.groups()))
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


def generate_html_report(missing_tests: dict, source_methods: dict, output_file: Path):
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Test-Coverage Report</title>
<style>
body {{ font-family: Arial, sans-serif; font-size: 14px; margin: 20px; background-color: #f9f9f9; }}
h1 {{ font-size: 20px; }} table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }} th {{ background-color: #eee; }}
tr.failed {{ background-color: #f8d7da; cursor: pointer; }} tr.passed {{ background-color: #d4edda; cursor: pointer; }}
tr.details {{ display: none; background-color: #fff3cd; }}
</style>
<script>function toggleRow(id) {{ var row=document.getElementById(id); row.style.display=(row.style.display==='table-row')?'none':'table-row'; }}</script>
</head><body><h1>Test-Coverage Report</h1>
<p>Total classes analyzed: {len(source_methods)}</p><table>
<tr><th>Class</th><th>Classpath</th><th>Missing Methods</th></tr>"""

    sorted_classes = sorted(
        source_methods.keys(),
        key=lambda key: (key not in missing_tests, key[0], key[1]),
    )
    for index, (class_path, class_name) in enumerate(sorted_classes):
        entry = missing_tests.get(
            (class_path, class_name),
            {MISSING_CLASS_KEY: False, MISSING_METHODS_KEY: []},
        )
        missing = entry[MISSING_METHODS_KEY]
        row_class = "failed" if missing else "passed"
        details_id = f"details_{index}"
        html += f"""
<tr class="{row_class}" onclick="toggleRow('{details_id}')"><td>{class_name}</td>
<td>{class_path}.{class_name}</td><td>{len(missing)}</td></tr>
<tr id="{details_id}" class="details"><td colspan="3">"""
        if missing:
            html += "<b>Unit-Test-Methods missing in the Test-Class:</b><ul>"
            html += "".join(f"<li>{method}</li>" for method in missing)
            html += "</ul>"
        else:
            html += "<b>No unit-test-methods missing in the Test-Class.</b><br>"
        html += "<b>Methods present in Original-Class:</b><ul>"
        html += "".join(
            f"<li>{method}</li>"
            for method in sorted(source_methods[(class_path, class_name)])
        )
        html += "</ul></td></tr>"

    html += "</table></body></html>"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    success(f"HTML report generated '{output_file}'")


def generate_test_coverage_report(source_dir: Path, test_dir: Path, output_file: Path):
    source_methods = collect_methods(run_checkstyle(METHOD_CONFIG, source_dir))
    test_methods = collect_methods(run_checkstyle(METHOD_CONFIG, test_dir))
    missing_tests = {}

    for (class_path, class_name), methods in source_methods.items():
        test_keys = [
            (class_path, f"{class_name}Test"),
            (class_path, f"{class_name}NGTest"),
        ]

        available_test_methods = set()
        found_test_class = False

        for test_key in test_keys:
            if test_key in test_methods:
                found_test_class = True
                available_test_methods.update(test_methods[test_key])

        if not found_test_class:
            missing_tests[(class_path, class_name)] = {
                MISSING_CLASS_KEY: True,
                MISSING_METHODS_KEY: sorted(methods),
            }
            continue
        expected = {f"test{method[0].upper()}{method[1:]}" for method in methods}
        actual = {
            expected_method
            for expected_method in expected
            if any(
                test_method.startswith(expected_method)
                for test_method in available_test_methods
            )
        }
        missing = sorted(expected - actual)
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
    generate_html_report(missing_tests, source_methods, output_file)


def run_git(*args: str, cwd: Path) -> str:
    return run(["git", *args], cwd=cwd, capture_output=True).stdout


def get_changed_lines(git_dir: Path, cached=False, include_untracked=False):
    diff_commands = [["diff", "--unified=0", "--no-color"]]
    if cached:
        diff_commands.append(["diff", "--cached", "--unified=0", "--no-color"])
    changed = []
    for command in diff_commands:
        diff = run_git(*command, cwd=git_dir)
        file = None
        added_file = False
        for line in diff.splitlines():
            if line.startswith("diff --git "):
                file, added_file = None, False
            elif line.startswith("--- /dev/null"):
                added_file = True
            elif line.startswith("+++ b/"):
                file = line[6:]
                if added_file:
                    changed.append((file, None))
            elif line.startswith("@@") and file and not added_file:
                match = re.search(r"\+(\d+)(?:,(\d+))?", line)
                if match:
                    start = int(match.group(1))
                    count = int(match.group(2) or 1)
                    changed.extend(
                        (file, number) for number in range(start, start + count)
                    )
    if include_untracked:
        changed.extend(
            (file, None)
            for file in run_git(
                "ls-files", "--others", "--exclude-standard", cwd=git_dir
            ).splitlines()
            if file
        )
    return changed


def run_checkstyle_file(file: Path):
    ensure_checks_jar()
    require_file(CHECKSTYLE_STYLE_GUIDE, "Checkstyle configuration")
    require_file(file, "Java source file")
    result = run(
        ["java", "-jar", str(CHECKS_JAR), "-c", str(CHECKSTYLE_STYLE_GUIDE), str(file)],
        capture_output=True,
        check=False,
    )
    return result.stdout + result.stderr, result.returncode


def parse_checkstyle_violation(line: str):
    match = re.match(r"^\[(WARN|ERROR)\]\s+(.*):(\d+):(\d+):\s*(.*)$", line)
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
    exceptions = re.findall(r"Caused by:\s+([\w.$]+)(?::\s+(.*))?", output)
    for exception, message in reversed(exceptions):
        if message:
            return exception, message
    return None


# pylint: disable=too-many-branches, too-many-locals
def subcommand_changed_lines(
    git_dir: Path,
    cached: bool,
    include_untracked: bool,
    run_checkstyle: bool,  # pylint: disable=redefined-outer-name
):
    changed = get_changed_lines(git_dir, cached, include_untracked)
    if not run_checkstyle:
        for file, line_no in changed:
            print(file if line_no is None else f"{file}:{line_no}")
        return

    changed_by_file = defaultdict(set)
    whole_files = set()
    for file, line_no in changed:
        (whole_files if line_no is None else changed_by_file[file]).add(
            file if line_no is None else line_no
        )

    warn_count = error_count = 0
    diagnostics = []
    for file in sorted(set(changed_by_file) | whole_files):
        source_file = git_dir / file
        if not source_file.is_file():
            continue
        if source_file.suffix.lower() != ".java":
            warning(f"ignoring '{source_file}'")
            continue
        output, exit_code = run_checkstyle_file(source_file)
        violations = [
            v for line in output.splitlines() if (v := parse_checkstyle_violation(line))
        ]
        if exit_code != 0 and not violations:
            exception = parse_checkstyle_exception(output)
            if exception:
                diagnostics.append(f"error: {file}: {exception[0]}: {exception[1]}")
            else:
                diagnostics.append(
                    f"error: {file}: Checkstyle failed to analyze the file."
                )
            error_count += 1
            continue
        for violation_file, row, column, severity, message in violations:
            try:
                reported_file = (
                    Path(violation_file)
                    .resolve()
                    .relative_to(git_dir.resolve())
                    .as_posix()
                )
            except ValueError:
                reported_file = Path(violation_file).as_posix()
            if reported_file != file or (
                file not in whole_files and row not in changed_by_file[file]
            ):
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


def subcommand_setup(_args, root: Path):
    require_command("git")
    require_command("mvn")
    build_checkstyle_checks(root)


def register_commands(subparsers, root: Path, setup_handlers):
    configure(root)
    setup_handlers.append(lambda args: subcommand_setup(args, root))

    parser = subparsers.add_parser("lint", help="run Checkstyle on changed Java lines")
    parser.add_argument("git_dir", type=Path, help="Git repository directory")
    parser.add_argument("--cached", action="store_true", help="analyze staged changes")
    parser.add_argument(
        "--include-untracked", action="store_true", help="include untracked Java files"
    )
    parser.add_argument(
        "--no-checkstyle",
        action="store_true",
        help="only show changed Java files and lines",
    )
    parser.set_defaults(
        handler=lambda args: subcommand_changed_lines(
            args.git_dir.resolve(),
            args.cached,
            args.include_untracked,
            not args.no_checkstyle,
        )
    )

    parser = subparsers.add_parser(
        "inventory-method", help="generate a method inventory"
    )
    parser.add_argument("source_dir", type=Path, help="Java source directory")
    parser.add_argument("-o", "--output", type=Path, help="optional output file")
    parser.set_defaults(
        handler=lambda args: inventory_method(
            args.source_dir.resolve(), args.output.resolve() if args.output else None
        )
    )

    parser = subparsers.add_parser(
        "inventory-rest-api", help="generate a REST API inventory CSV"
    )
    parser.add_argument("source_dir", type=Path, help="Java source directory")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default="rest_apis.csv",
        help="output CSV file",
    )
    parser.set_defaults(
        handler=lambda args: inventory_rest_api(
            args.source_dir.resolve(), args.output.resolve()
        )
    )

    parser = subparsers.add_parser(
        "test-coverage", help="generate the test-coverage report"
    )
    parser.add_argument("source_dir", type=Path, help="Java source directory")
    parser.add_argument("test_dir", type=Path, help="Java test directory")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default="test_coverage_report.html",
        help="output HTML report",
    )
    parser.set_defaults(
        handler=lambda args: test_coverage(
            args.source_dir.resolve(), args.test_dir.resolve(), args.output.resolve()
        )
    )


def inventory_method(source_dir: Path, output_file: Path | None):
    require_directory(source_dir, "source directory")
    output = run_checkstyle(METHOD_CONFIG, source_dir)
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output, encoding="utf-8")
        success(f"method inventory generated '{output_file}'.")
    else:
        print(output, end="")


def inventory_rest_api(source_dir: Path, output_file: Path):
    require_directory(source_dir, "source directory")
    generate_rest_api_report(source_dir, output_file)


def test_coverage(source_dir: Path, test_dir: Path, output_file: Path):
    require_directory(source_dir, "source directory")
    require_directory(test_dir, "test directory")
    generate_test_coverage_report(source_dir, test_dir, output_file)
