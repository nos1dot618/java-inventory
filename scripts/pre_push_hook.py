#!/usr/bin/env python3

"""Build the standalone executable and verify its version command."""

# pylint: disable=missing-function-docstring

import os
import subprocess
import sys


def main():
    subprocess.run([sys.executable, "package.py"], check=True)

    executable = "dist/java-inventory.exe" if os.name == "nt" else "dist/java-inventory"
    subprocess.run([executable, "version"], check=True)


if __name__ == "__main__":
    main()
