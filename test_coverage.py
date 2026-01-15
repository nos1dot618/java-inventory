import subprocess
import re
from collections import defaultdict
from pathlib import Path
import sys

METHOD_RE = re.compile(
    r"\[DEBUG\]\s+\[Method Inventory Check\]\s+"
    r"([A-Za-z0-9_]+)\s+([A-Za-z0-9_$.]+)\s+([A-Za-z0-9_]+)"
)

MISSING_CLASS_KEY = "missingClass"
MISSING_METHODS_KEY = "missingMethods"


def error(message):
    print(f"[\033[31mERROR\033[0m] {message}")


def info(message):
    print(f"[\033[34mINFO\033[0m] {message}")


def testDirPath(path: str):
    if not path.exists():
        error(f"'{path}' does not exist.")
        sys.exit(1)
    if not path.is_dir():
        error(f"'{path}' is not a directory.")
        sys.exit(1)


def runCheckstyleMethodInventoryCheck(targetDir: Path) -> str:
    cmd = [
        "java",
        "-cp",
        "resources/checkstyle-12.3.0-all.jar;build/MethodInventoryCheck.jar",
        "com.puppycrawl.tools.checkstyle.Main",
        "-c",
        "./resources/method_inventory_check_config.xml",
        str(targetDir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout


def collectMethods(output: str):
    result = defaultdict(set)
    for line in output.splitlines():
        match = METHOD_RE.search(line)
        if match:
            className, classPath, methodName = match.groups()
            result[(classPath, className)].add(methodName)
    return result


def generateHtmlReport(
    missingTests: dict,
    sourceMethods: dict,
    outputFile: str = "./build/test_coverage_report.html",
):
    html = f"""
<!DOCTYPE html>
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
    h1 {{ font-size: 20px; }}
    table {{
        border-collapse: collapse;
        width: 100%;
    }}
    th, td {{
        border: 1px solid #ccc;
        padding: 6px 10px;
        text-align: left;
    }}
    th {{ background-color: #eee; }}
    tr.failed {{ background-color: #f8d7da; cursor: pointer; }}
    tr.passed {{ background-color: #d4edda; cursor: pointer; }}
    tr.details {{ display: none; background-color: #fff3cd; }}
</style>
<script>
function toggleRow(id) {{
    var row = document.getElementById(id);
    row.style.display = (row.style.display === 'table-row') ? 'none' : 'table-row';
}}
</script>
</head>
<body>

<h1>Test-Coverage Report</h1>
<p>Total classes analyzed: {len(sourceMethods)}</p>

<table>
<tr>
    <th>Class</th>
    <th>Classpath</th>
    <th>Missing Methods</th>
</tr>
"""

    # Sort first by amount of missing unit-test-methods, then by the classpath.
    sortedClasses = sorted(
        sourceMethods.keys(),
        key=lambda key: (
            key not in missingTests,
            key[0],  # classPath
            key[1],  # className
        ),
    )

    for index, (classPath, className) in enumerate(sortedClasses):
        missingTestEntry = missingTests.get(
            (classPath, className),
            {MISSING_CLASS_KEY: False, MISSING_METHODS_KEY: []},
        )

        missingCount = len(missingTestEntry[MISSING_METHODS_KEY])
        rowClass = "failed" if missingCount > 0 else "passed"
        detailsId = f"details_{index}"

        html += f"""
<tr class="{rowClass}" onclick="toggleRow('{detailsId}')">
    <td>{className}</td>
    <td>{classPath}.{className}</td>
    <td>{missingCount}</td>
</tr>
<tr id="{detailsId}" class="details">
    <td colspan="3">
"""

        if missingCount > 0:
            html += "<b>Unit-Test-Methods missing in the Test-Class:</b><ul>"
            for method in missingTestEntry[MISSING_METHODS_KEY]:
                html += f"<li>{method}</li>"
            html += "</ul>"
        else:
            html += "<b>No unit-test-methods missing in the Test-Class.</b><br>"

        html += "<b>Methods present in Original-Class:</b><ul>"
        for method in sorted(sourceMethods[(classPath, className)]):
            html += f"<li>{method}</li>"
        html += "</ul></td></tr>"

    html += "</table></body></html>"

    Path(outputFile).parent.mkdir(parents=True, exist_ok=True)
    with open(outputFile, "w", encoding="utf-8") as file:
        file.write(html)

    info(f"HTML-Report generated '{outputFile}'.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        error("Usage: python test_coverage.py <sourceDir> <testDir>.")
        sys.exit(1)

    sourceDir = Path(sys.argv[1])
    testDir = Path(sys.argv[2])

    testDirPath(sourceDir)
    testDirPath(testDir)

    sourceOutput = runCheckstyleMethodInventoryCheck(sourceDir)
    testOutput = runCheckstyleMethodInventoryCheck(testDir)

    sourceMethods = collectMethods(sourceOutput)
    testMethods = collectMethods(testOutput)

    missingTests = {}

    for (classPath, className), methods in sourceMethods.items():
        testClassKey = (classPath, f"{className}Test")

        if testClassKey not in testMethods:
            missingTests[(classPath, className)] = {
                MISSING_CLASS_KEY: True,
                MISSING_METHODS_KEY: sorted(methods),
            }
            continue

        expectedTests = {f"test{m[0].upper()}{m[1:]}" for m in methods}
        actualTests = {
            f"test{method[0].upper()}{method[1:]}"
            for method in methods
            for testMethod in testMethods[testClassKey]
            if testMethod.startswith(f"test{method[0].upper()}{method[1:]}")
        }

        missing = sorted(expectedTests - actualTests)
        if missing:
            missingTests[(classPath, className)] = {
                MISSING_CLASS_KEY: False,
                MISSING_METHODS_KEY: missing,
            }

    if not missingTests:
        info("No unit-test missing in any of the classes.")
    else:
        info("Missing unit tests:")
        for (classPath, className), missingTestEntry in missingTests.items():
            info(f"- {className}")

    generateHtmlReport(missingTests, sourceMethods)
