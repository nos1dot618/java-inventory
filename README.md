> Dev-Tools for Java-Projects.
---

## 1. Static-Analyzer for unit-test-coverage

### Getting Started

```powershell
.\Setup.ps1
python .\scripts\test_coverage.py .\dev-test\src\main\ .\dev-test\src\test\
start .\build\test_coverage_report.html
```

## 2. Git-Pre-Commit-Hook

List format and compilation issues in changes made in java-files,
utilizes [checkstyle](https://github.com/checkstyle/checkstyle/) for linting. Refer [pre-commit/](./pre-commit) for more
information.

### Getting Started

```powershell
.\pre-commit\Setup.ps1 -SetupPath <path/to/your/repository>
```

## 3. Static-Analyzer for listing REST-APIs

List REST-API endpoints (built using `javax.ws.rs`) present inside project.

```powershell
.\Setup.ps1
python .\scripts\list_rest_api.py .\dev-test\src\main\
start .\build\rest_apis.csv
```

## References

1. CheckStyle Documentation: <https://checkstyle.org/index.html>