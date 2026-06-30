# Dev-Tools for Java Projects

A collection of development tools for Java projects, including Checkstyle-based static analysis, unit-test coverage analysis, REST API inventory generation, and a Git pre-commit hook.

---

## Setup

Clone the repository and initialize its dependencies and Git submodules:

```sh
python toolchain.py setup
```

Build the custom Checkstyle checks:

```sh
python toolchain.py build
```

The `build` command compiles the custom Checkstyle checks and generates:

```text
build/
└── CheckstyleChecks.jar
```

Run `setup` once after cloning the repository. Run `build` whenever the custom Checkstyle checks change.

### Requirements

The following tools must be available on `PATH`:

* Python 3
* Git
* Java Development Kit (JDK)

  * `java`
  * `javac`
  * `jar`

---

## 1. Static Analyzer for Unit-Test Coverage

Analyzes Java source classes and their corresponding test classes to identify missing unit tests.

### Usage

```sh
python toolchain.py test-coverage \
    dev-test/src/main \
    dev-test/src/test
```

The report is generated at:

```text
build/test_coverage_report.html
```

Open the generated report with your system's default browser:

```sh
xdg-open build/test_coverage_report.html
```

On macOS:

```sh
open build/test_coverage_report.html
```

The report shows:

* Total classes analyzed
* Classes missing a corresponding test class
* Missing test methods
* Methods found in the original source class

---

## 2. Git Pre-Commit Hook

The pre-commit hook checks Java files changed in a commit for formatting and compilation issues.

It uses [Checkstyle](https://github.com/checkstyle/checkstyle/) for Java linting.

See [`pre-commit/`](./pre-commit) for more information.

### Getting Started

Initialize the pre-commit hook for your repository:

```sh
./pre-commit/Initialize.ps1 -Path <path/to/your/repository>
```

---

## 3. Static Analyzer for REST APIs

Scans Java source code for REST API endpoints built using `javax.ws.rs` and generates a CSV inventory.

### Usage

```sh
python toolchain.py inventory-rest-api dev-test/src/main
```

The report is generated at:

```text
build/rest_apis.csv
```

The CSV contains:

| Column        | Description                          |
| ------------- | ------------------------------------ |
| `method`      | HTTP method, such as `GET` or `POST` |
| `endpoint`    | REST API endpoint                    |
| `description` | Endpoint description                 |

A custom output path can be specified with `-o`:

```sh
python toolchain.py inventory-rest-api \
    dev-test/src/main \
    -o build/my-rest-apis.csv
```

---

## Other Commands

Generate a method inventory for a Java source tree:

```sh
python toolchain.py inventory-method dev-test/src/main
```

Write the method inventory to a file:

```sh
python toolchain.py inventory-method \
    dev-test/src/main \
    -o build/methods.txt
```

Display available commands:

```sh
python toolchain.py --help
```

Command-specific help:

```sh
python toolchain.py test-coverage --help
python toolchain.py inventory-rest-api --help
python toolchain.py inventory-method --help
```

---

## References

1. [Checkstyle Documentation](https://checkstyle.org/index.html)
2. [Checkstyle GitHub Repository](https://github.com/checkstyle/checkstyle/)
