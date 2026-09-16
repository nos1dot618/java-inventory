# Packaging

`java-inventory` can be packaged as a standalone executable with PyInstaller.

## Local build

```shell
python package.py
```

The build:

1. Creates `.venv` when needed.
2. Installs PyInstaller in the build environment.
3. Runs `python java_inventory.py setup`.
4. Verifies the required Java artifacts.
5. Packages the application and resources.

Output:

```shell
dist/java-inventory
```

On Windows:

```powershell
dist\java-inventory.exe
```

Run the packaged binary with:

```shell
./dist/java-inventory --help
```

Windows:

```powershell
dist\java-inventory.exe --help
```

## Options

Skip cleanup:

```shell
python package.py --no-cleanup
```

Use another PyInstaller spec:

```shell
python package.py --spec path/to/custom.spec
```

Enable debug output:

```shell
python package.py --debug
```

## Platform builds

PyInstaller produces a native executable for the platform where it runs. Build separately on each target platform.

Official releases use GitHub Actions to build platform-specific binaries and attach them to GitHub Releases.

The packaging environment requires Python, a JDK, and Maven because `setup` builds the Java components used by the application.
