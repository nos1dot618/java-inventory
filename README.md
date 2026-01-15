> Java Dev-Tools
---

## 1. Static-Analyzer for finding missing unit-tests in java-module

### Getting Started

```powershell
.\SETUP.ps1
python missing_unit_tests.py
start .\build\missing_unit_test_report.html
```

## 2. Git-Pre-Commit-Hook

List format and compilation issues in changes made in java-files, utilizes [checkstyle](https://github.com/checkstyle/checkstyle/) for linting. Refer [pre-commit/](./pre-commit) for more information.

### Getting Started

```powershell
.\pre-commit\SETUP.ps1 -SetupPath <path/to/your/repository>
```

## References

1. CheckStyle Documentation: <https://checkstyle.org/index.html>