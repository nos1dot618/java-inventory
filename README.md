# Dev-Tools for Java Projects

Development tooling for Java projects, including Checkstyle linting, method inventory, REST API inventory, and test-coverage analysis.

## Requirements

* Python 3
* Git
* JDK (`java`, `javac`, and `jar`)

## Setup

Initialize the project dependencies and Git submodules:

```sh
python java_inventory.py setup
```

Build the custom Checkstyle checks:

```sh
python java_inventory.py build
```

You should run `setup` and `build` before using the analysis and linting commands.

---

## 1. Changed-Line Java Linter

The `lint` command runs Checkstyle against Java code changed in Git.

For modified files, only violations on changed lines are reported. Newly added files are checked as a whole.

### Basic usage

Check unstaged working-tree changes:

```sh
python java_inventory.py lint .
```

Check staged changes:

```sh
python java_inventory.py lint . --cached
```

Include untracked Java files:

```sh
python java_inventory.py lint . --include-untracked
```

Show the changed Java files and lines without running Checkstyle:

```sh
python java_inventory.py lint . --no-checkstyle
```

Enable debug logging:

```sh
python java_inventory.py --debug lint .
```

### How changes are handled

| Change                                         | Lint behavior                          |
| ---------------------------------------------- | -------------------------------------- |
| Modified Java file                             | Check only violations on changed lines |
| Added Java file                                | Check the entire file                  |
| Untracked Java file with `--include-untracked` | Check the entire file                  |
| Non-Java file                                  | Ignored                                |

For example:

```text
warning: src/main/java/example/Foo.java:15:5: Missing a Javadoc comment. [MissingJavadocMethod]
warning: src/main/java/example/Foo.java:17:5: 'isValid' has incorrect indentation level 4, expected level should be 12. [Indentation]
error: src/main/java/example/Bar.java:8:48: java.lang.IllegalStateException: mismatched input '{' expecting ')'

info: checkstyle summary: 1 error(s), 2 warning(s).
```

### Lint options

| Option                | Description                                                     |
| --------------------- | --------------------------------------------------------------- |
| `--cached`            | Analyze staged changes instead of unstaged working-tree changes |
| `--include-untracked` | Include untracked Java files and check them as whole files      |
| `--no-checkstyle`     | Print changed Java files and lines without running Checkstyle   |
| `--debug`             | Show internal commands and debug logging                        |

`--debug` is a global option and must appear **before** the subcommand:

```sh
python java_inventory.py --debug lint .
```

### Using lint as a Git pre-commit hook

For a normal Git hook, lint the staged snapshot:

Create `.git/hooks/pre-commit`:

```sh
#!/bin/sh
python java_inventory.py lint . --cached
```

Make it executable:

```sh
chmod +x .git/hooks/pre-commit
```

The `--cached` flag is important because a commit contains the staged version of the files, not arbitrary unstaged working-tree changes.

To bypass the hook for a commit:

```sh
git commit --no-verify
```

---

## 2. Using `pre-commit`

The same `lint` command can be integrated with the Python [`pre-commit`](https://pre-commit.com/) framework.

Install `pre-commit`:

```sh
python -m pip install pre-commit
```

Add the following to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: java-inventory-lint
        name: Java Inventory Checkstyle
        entry: python java_inventory.py lint . --cached
        language: unsupported
        pass_filenames: false
        always_run: true
```

Install the Git hook:

```sh
pre-commit install
```

Or install the hook and its environments:

```sh
pre-commit install --install-hooks
```

Run the lint hook manually:

```sh
pre-commit run java-inventory-lint
```

Run it against all files known to `pre-commit`:

```sh
pre-commit run java-inventory-lint --all-files
```

The hook uses `pass_filenames: false` because `java_inventory.py` determines the changed files itself from Git.

---

## 3. Java Method Inventory

Generate an inventory of Java methods:

```sh
python java_inventory.py inventory-method dev-test/src/main
```

Write the inventory to a specific file:

```sh
python java_inventory.py inventory-method dev-test/src/main \
    --output build/methods.csv
```

---

## 4. REST API Inventory

Generate a CSV inventory of REST APIs:

```sh
python java_inventory.py inventory-rest-api dev-test/src/main
```

By default, the report is written to:

```text
build/rest_apis.csv
```

Specify a different output file:

```sh
python java_inventory.py inventory-rest-api dev-test/src/main \
    --output build/rest_apis.csv
```

---

## 5. Test Coverage Analysis

Generate the test-coverage report:

```sh
python java_inventory.py test-coverage \
    dev-test/src/main \
    dev-test/src/test
```

By default, the report is written to:

```text
build/test_coverage_report.html
```

Specify a different output file:

```sh
python java_inventory.py test-coverage \
    dev-test/src/main \
    dev-test/src/test \
    --output build/coverage.html
```

---

## Command Reference

```text
python tool.py [--debug] <command>
```

### Commands

| Command              | Purpose                                         |
| -------------------- | ----------------------------------------------- |
| `setup`              | Initialize submodules and validate dependencies |
| `build`              | Build the custom Checkstyle checks              |
| `lint`               | Run Checkstyle on changed Java code             |
| `inventory-method`   | Generate a Java method inventory                |
| `inventory-rest-api` | Generate a REST API inventory CSV               |
| `test-coverage`      | Generate the test-coverage report               |

Show command help:

```sh
python java_inventory.py --help
```

Show help for a specific command:

```sh
python java_inventory.py lint --help
```

```sh
python java_inventory.py inventory-method --help
```

```sh
python java_inventory.py inventory-rest-api --help
```

```sh
python java_inventory.py test-coverage --help
```

## Checkstyle

The linter uses the project's Checkstyle configuration and custom Checkstyle checks:

```text
resources/style_guide.xml
resources/checkstyle-12.3.0-all.jar
build/java-inventory-checkstyle-checks.jar
```

Run `setup` and `build` first if the Checkstyle dependencies or custom checks have not been built.
