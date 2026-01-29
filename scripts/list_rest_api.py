import csv
import re

from commons import *

REST_API_RE = re.compile(
    r"\[DEBUG]\s+\[REST-API Inventory Check]\s+"
    r"(GET|POST|PUT|DELETE|PATCH)\s+(\S+)\s+\"([^\"]+)\""
)

CONFIG_NAME = "rest_api_inventory_check_config"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        error("Usage: python test_coverage.py <sourceDir>.")
        sys.exit(1)

    sourceDir = Path(sys.argv[1])
    testDirPath(sourceDir)
    sourceOutput = runCheckstyleCheck(CONFIG_NAME, sourceDir)
    outputFile = "./build/rest_apis.csv"

    rows = []
    for line in sourceOutput.splitlines():
        match = REST_API_RE.search(line)
        if match:
            method, endpoint, description = match.groups()
            rows.append([method, endpoint, description])

    Path(outputFile).parent.mkdir(parents=True, exist_ok=True)
    with open(outputFile, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["method", "endpoint", "description"])
        writer.writerows(rows)
    info(f"CSV-Report generated '{outputFile}'.")
