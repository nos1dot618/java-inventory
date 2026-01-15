> Java Dev-Tools
---

## 1. Static-Analyzer for unit-test-coverage

### Getting Started

```powershell
.\SETUP.ps1
python test_coverage.py
start .\build\test_coverage_report.html
```

## 2. Git-Pre-Commit-Hook

List format and compilation issues in changes made in java-files, utilizes [checkstyle](https://github.com/checkstyle/checkstyle/) for linting. Refer [pre-commit/](./pre-commit) for more information.

### Getting Started

```powershell
.\pre-commit\SETUP.ps1 -SetupPath <path/to/your/repository>
```

## References

1. CheckStyle Documentation: <https://checkstyle.org/index.html>