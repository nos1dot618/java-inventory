"""Checkstyle-based Java inventory commands."""

# pylint: disable=missing-function-docstring, too-many-lines

import csv
import re
from collections import defaultdict
from html import escape
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
    r"([A-Za-z0-9_$.]+),"
    r"([A-Za-z0-9_]+),"
    r"([A-Za-z0-9_]+),"
    r"(public|protected|private|package-private)"
)
MISSING_CLASS_KEY = "missingClass"
MISSING_METHODS_KEY = "missingMethods"


def collect_methods(output: str):
    result = defaultdict(set)
    for line in output.splitlines():
        match = METHOD_RE.search(line)
        if match:
            class_path, class_name, method_name, access_modifier = match.groups()
            result[(class_path, class_name)].add((method_name, access_modifier))
    return result


# pylint: disable=too-many-locals, line-too-long
def generate_html_report(
    coverage: list[dict],
    stats: dict,
    output_file: Path,
):
    def pct(value: int, total: int) -> str:
        return f"{(value / total * 100):.1f}%" if total else "100.0%"

    def status_class(status: str) -> str:
        return {
            "covered": "status-covered",
            "partial": "status-partial",
            "missing": "status-missing",
        }[status]

    rows = []
    for index, entry in enumerate(coverage):
        status = entry["status"]
        missing = entry["missing"]
        covered = entry["covered"]
        required = entry["required"]
        optional = entry["optional"]
        details_id = f"details_{index}"

        method_rows = []
        for method_name, access_modifier, test_names in entry["methods"]:
            if access_modifier == "private":
                state = '<span class="method-state optional">Optional</span>'
            elif test_names:
                tests = ", ".join(test_names)
                state = f'<span class="method-state covered">✓ {escape(tests)}</span>'
            else:
                state = '<span class="method-state missing">Missing</span>'

            method_rows.append(
                f"""
                <div class="method-row">
                    <div class="method-name">{escape(method_name)}</div>
                    <div class="visibility">{access_modifier}</div>
                    <div>{state}</div>
                </div>"""
            )

        missing_text = (
            f'<span class="count-missing">{len(missing)}</span> missing'
            if missing
            else '<span class="count-covered">All required methods covered</span>'
        )

        rows.append(
            f"""
            <section class="class-card">
                <button class="class-header" type="button"
                        onclick="toggleRow('{details_id}')"
                        aria-controls="{details_id}" aria-expanded="false">
                    <span class="class-info">
                        <span class="class-name">{escape(entry["class_name"])}</span>
                        <span class="package">{escape(entry["class_path"])}</span>
                    </span>
                    <span class="class-summary">
                        <span>{covered}/{required} required</span>
                        <span class="status {status_class(status)}">{status.title()}</span>
                        <span class="chevron" id="{details_id}_icon">⌄</span>
                    </span>
                </button>
                <div id="{details_id}" class="class-details">
                    <div class="detail-summary">
                        <span>{missing_text}</span>
                        <span>{optional} private method{"s" if optional != 1 else ""} optional</span>
                    </div>
                    <div class="method-list">
                        <div class="method-row method-heading">
                            <div>Method</div>
                            <div>Access</div>
                            <div>Test</div>
                        </div>
                        {"".join(method_rows)}
                    </div>
                </div>
            </section>"""
        )

    visibility_rows = []
    for visibility in ("public", "protected", "package-private", "private"):
        data = stats["visibility"][visibility]
        coverage_text = (
            "optional"
            if visibility == "private"
            else f"{data['covered']}/{data['required']} · {pct(data['covered'], data['required'])}"
        )
        visibility_rows.append(
            f"""
            <div class="breakdown-row">
                <span>
                    <span class="dot dot-{visibility.replace("-", "")}"></span>
                    {visibility}
                </span>
                <span>{data["total"]} methods</span>
                <strong>{coverage_text}</strong>
            </div>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Test Coverage</title>
<style>
:root {{
    --bg: #f6f8fb;
    --surface: #ffffff;
    --border: #e5e9f0;
    --text: #172033;
    --muted: #687386;
    --accent: #4f46e5;
    --accent-soft: #eef2ff;
    --green: #16803c;
    --green-soft: #eaf7ef;
    --amber: #a16207;
    --amber-soft: #fff7df;
    --red: #c0392b;
    --red-soft: #fff0ee;
    --shadow: 0 1px 3px rgba(15, 23, 42, .06), 0 8px 24px rgba(15, 23, 42, .04);
}}

* {{ box-sizing: border-box; }}

body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.45;
}}

.container {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 36px 24px 56px;
}}

.header {{
    margin-bottom: 24px;
}}

.eyebrow {{
    color: var(--accent);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin-bottom: 5px;
}}

h1 {{
    margin: 0;
    font-size: 28px;
    letter-spacing: -.025em;
}}

.subtitle {{
    margin: 5px 0 0;
    color: var(--muted);
}}

.cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
}}

.card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 17px 18px;
    box-shadow: var(--shadow);
}}

.card-label {{
    color: var(--muted);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .04em;
}}

.card-value {{
    margin-top: 5px;
    font-size: 25px;
    font-weight: 700;
    letter-spacing: -.02em;
}}

.card-subtitle {{
    margin-top: 2px;
    color: var(--muted);
    font-size: 12px;
}}

.card.coverage .card-value {{ color: var(--accent); }}
.card.missing .card-value {{ color: var(--red); }}
.card.covered .card-value {{ color: var(--green); }}

.section {{
    margin-top: 24px;
}}

.section-title {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 10px;
}}

.section-title h2 {{
    margin: 0;
    font-size: 16px;
}}

.section-title span {{
    color: var(--muted);
    font-size: 12px;
}}

.breakdown {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    box-shadow: var(--shadow);
}}

.breakdown-row {{
    display: grid;
    grid-template-columns: 1fr 140px 190px;
    align-items: center;
    min-height: 48px;
    padding: 0 17px;
    border-bottom: 1px solid var(--border);
}}

.breakdown-row:last-child {{ border-bottom: 0; }}

.breakdown-row > span:nth-child(2) {{
    color: var(--muted);
    text-align: right;
}}

.breakdown-row strong {{
    text-align: right;
    font-size: 13px;
}}

.dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
    background: var(--accent);
}}

.dot-public {{ background: #4f46e5; }}
.dot-protected {{ background: #0f766e; }}
.dot-packageprivate {{ background: #b7791f; }}
.dot-private {{ background: #94a3b8; }}

.class-list {{
    display: grid;
    gap: 8px;
}}

.class-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    box-shadow: var(--shadow);
}}

.class-header {{
    width: 100%;
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 14px 16px;
    text-align: left;
}}

.class-header:hover {{
    background: #fafbff;
}}

.class-info {{
    min-width: 0;
    display: flex;
    flex-direction: column;
}}

.class-name {{
    font-weight: 650;
}}

.package {{
    color: var(--muted);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.class-summary {{
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--muted);
    white-space: nowrap;
    font-size: 12px;
}}

.status {{
    border-radius: 999px;
    padding: 3px 8px;
    font-weight: 650;
}}

.status-covered {{
    background: var(--green-soft);
    color: var(--green);
}}

.status-partial {{
    background: var(--amber-soft);
    color: var(--amber);
}}

.status-missing {{
    background: var(--red-soft);
    color: var(--red);
}}

.chevron {{
    color: #98a2b3;
    font-size: 17px;
    width: 14px;
    transition: transform .15s ease;
}}

.class-details {{
    display: none;
    border-top: 1px solid var(--border);
    background: #fbfcfe;
    padding: 14px 16px 16px;
}}

.detail-summary {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 12px;
}}

.count-missing {{ color: var(--red); font-weight: 650; }}
.count-covered {{ color: var(--green); font-weight: 650; }}

.method-list {{
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    background: var(--surface);
}}

.method-row {{
    display: grid;
    grid-template-columns: 1fr 130px 1.5fr;
    align-items: center;
    gap: 12px;
    min-height: 40px;
    padding: 0 12px;
    border-bottom: 1px solid var(--border);
}}

.method-row:last-child {{ border-bottom: 0; }}

.method-heading {{
    min-height: 34px;
    background: #f7f8fb;
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .04em;
}}

.method-name {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}

.visibility {{
    color: var(--muted);
    font-size: 12px;
}}

.method-state {{
    font-size: 12px;
}}

.method-state.covered {{ color: var(--green); }}
.method-state.missing {{ color: var(--red); font-weight: 650; }}
.method-state.optional {{ color: var(--muted); font-style: italic; }}


.footer {{
    margin - top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    font-size: 12px;
    text-align: center;
}}

.footer a {{
    color: var(--muted);
    text-decoration: none;
}}

.footer a:hover {{
    color: var(--accent);
    text-decoration: underline;
}}

.footer-separator {{
    color: #c2c8d2;
}}

@media (max-width: 760px) {{
    .container {{ padding: 24px 14px 40px; }}
    .cards {{ grid-template-columns: repeat(2, 1fr); }}
    .breakdown-row {{ grid-template-columns: 1fr 90px 130px; }}
    .method-row {{ grid-template-columns: 1fr 100px; }}
    .method-row > :last-child {{ grid-column: 1 / -1; padding-bottom: 8px; }}
    .method-heading > :last-child {{ display: none; }}
    .class-summary > span:first-child {{ display: none; }}
}}

@media (max-width: 480px) {{
    .cards {{ grid-template-columns: 1fr 1fr; gap: 8px; }}
    .card {{ padding: 14px; }}
    .card-value {{ font-size: 21px; }}
    .class-header {{ padding: 12px; }}
    .class-summary {{ gap: 6px; }}
    .breakdown-row {{ grid-template-columns: 1fr auto; gap: 8px; padding: 8px 12px; }}
    .breakdown-row > span:nth-child(2) {{ display: none; }}
    .breakdown-row strong {{ text-align: right; }}
}}
</style>
<script>
function toggleRow(id) {{
    const row = document.getElementById(id);
    const button = row.previousElementSibling;
    const icon = document.getElementById(id + "_icon");
    const open = row.style.display === "block";
    row.style.display = open ? "none" : "block";
    button.setAttribute("aria-expanded", String(!open));
    icon.style.transform = open ? "rotate(0deg)" : "rotate(180deg)";
}}
</script>
</head>
<body>
<main class="container">
    <header class="header">
        <div class="eyebrow">Java Inventory</div>
        <h1>Test Coverage</h1>
        <p class="subtitle">Method-level test coverage across {
        stats["classes_total"]
    } analyzed classes.</p>
    </header>

    <section class="cards">
        <div class="card">
            <div class="card-label">Classes</div>
            <div class="card-value">{stats["classes_total"]}</div>
            <div class="card-subtitle">{stats["classes_covered"]} fully covered</div>
        </div>
        <div class="card covered">
            <div class="card-label">Tested</div>
            <div class="card-value">{stats["methods_covered"]}</div>
            <div class="card-subtitle">of {
        stats["methods_required"]
    } required methods</div>
        </div>
        <div class="card missing">
            <div class="card-label">Missing</div>
            <div class="card-value">{stats["methods_missing"]}</div>
            <div class="card-subtitle">required tests</div>
        </div>
        <div class="card coverage">
            <div class="card-label">Coverage</div>
            <div class="card-value">{
        pct(stats["methods_covered"], stats["methods_required"])
    }</div>
            <div class="card-subtitle">{
        stats["private_methods"]
    } private methods optional</div>
        </div>
    </section>

    <section class="section">
        <div class="section-title">
            <h2>Breakdown by access</h2>
            <span>Private methods are optional</span>
        </div>
        <div class="breakdown">
            {"".join(visibility_rows)}
        </div>
    </section>

    <section class="section">
        <div class="section-title">
            <h2>Classes</h2>
            <span>{stats["classes_missing"]} with missing tests</span>
        </div>
        <div class="class-list">
            {"".join(rows)}
        </div>
    </section>

    <footer class="footer">
        <span>© 2026 Lakshay Chauhan</span>
        <span class="footer-separator">·</span>
        <span>MIT License</span>
        <span class="footer-separator">·</span>
        <a href="https://github.com/nos1dot618/java-inventory"
           target="_blank" rel="noopener noreferrer">github.com/nos1dot618/java-inventory</a>
    </footer>

</main>
</body>
</html>"""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    success(f"HTML report generated '{output_file}'")


# pylint: disable=too-many-locals, too-many-branches
def generate_test_coverage_report(source_dir: Path, test_dir: Path, output_file: Path):
    source_methods = collect_methods(run_checkstyle(METHOD_CONFIG, source_dir))
    test_methods = collect_methods(run_checkstyle(METHOD_CONFIG, test_dir))

    coverage = []
    stats = {
        "classes_total": len(source_methods),
        "classes_covered": 0,
        "classes_missing": 0,
        "methods_total": 0,
        "methods_required": 0,
        "methods_covered": 0,
        "methods_missing": 0,
        "private_methods": 0,
        "visibility": {
            "public": {"total": 0, "required": 0, "covered": 0},
            "protected": {"total": 0, "required": 0, "covered": 0},
            "package-private": {"total": 0, "required": 0, "covered": 0},
            "private": {"total": 0, "required": 0, "covered": 0},
        },
    }

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

        method_details = []
        missing = []
        covered_count = 0
        required_count = 0
        optional_count = 0

        for method_name, access_modifier in sorted(methods):
            stats["methods_total"] += 1
            stats["visibility"][access_modifier]["total"] += 1

            if access_modifier == "private":
                optional_count += 1
                stats["private_methods"] += 1
                method_details.append((method_name, access_modifier, []))
                continue

            required_count += 1
            stats["methods_required"] += 1
            stats["visibility"][access_modifier]["required"] += 1

            expected_method = f"test{method_name[0].upper()}{method_name[1:]}"
            matching_tests = sorted(
                test_method
                for test_method, _ in available_test_methods
                if test_method.startswith(expected_method)
            )

            if matching_tests:
                covered_count += 1
                stats["methods_covered"] += 1
                stats["visibility"][access_modifier]["covered"] += 1
            else:
                missing.append(method_name)
                stats["methods_missing"] += 1

            method_details.append((method_name, access_modifier, matching_tests))

        status = (
            "covered"
            if required_count == covered_count
            else "missing"
            if covered_count == 0
            else "partial"
        )

        if status == "covered":
            stats["classes_covered"] += 1
        else:
            stats["classes_missing"] += 1

        coverage.append(
            {
                "class_path": class_path,
                "class_name": class_name,
                "status": status,
                "required": required_count,
                "covered": covered_count,
                "missing": missing,
                "optional": optional_count,
                "has_test_class": found_test_class,
                "methods": method_details,
            }
        )

    coverage.sort(
        key=lambda entry: (
            entry["status"] == "covered",
            entry["class_path"],
            entry["class_name"],
        )
    )

    if stats["methods_missing"] == 0:
        success("no unit tests missing in any of the classes")
    else:
        warning("missing unit tests:")
        for entry in coverage:
            if entry["missing"]:
                info(f"- {entry['class_name']}")

    generate_html_report(coverage, stats, output_file)


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
