# Contributing

Thanks for contributing to Java Inventory.

## Development setup

Install the required tools listed in the [README](README.md#requirements), then initialize the project:

```shell
python java_inventory.py setup
````

Install `pre-commit` for the development hooks:

```shell
pip install pre-commit
pre-commit install
```

Use the CLI directly while developing:

```shell
python java_inventory.py --help
```

## Before submitting changes

Run the linter against your staged changes:

```shell
python java_inventory.py lint . --cached
```

For changes to inventory or coverage behavior, also run the relevant command against the development test project.

For example:

```shell
python java_inventory.py test-coverage \
    dev-test/src/main \
    dev-test/src/test
```

If packaging code changes, verify a local build:

```shell
python build.py
```

## Pull requests

Keep changes focused and describe:

- what changed;
- why it changed;
- how it was tested.

Include generated reports or build artifacts only when they are specifically useful for reviewing the change.
