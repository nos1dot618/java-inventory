"""PyInstaller spec for java_inventory."""

from pathlib import Path

BLOCK_CIPHER = None

PROJECT_ROOT = Path.cwd()

CHECKSTYLE_TARGET = PROJECT_ROOT / "checkstyle" / "target"
MAVEN_TARGET = PROJECT_ROOT / "maven" / "target"

if not CHECKSTYLE_TARGET.is_dir():
    raise RuntimeError(
        f"Required directory not found: {CHECKSTYLE_TARGET}. "
        "Run `python java_inventory.py setup` before building."
    )

if not MAVEN_TARGET.is_dir():
    raise RuntimeError(
        f"Required directory not found: {MAVEN_TARGET}. "
        "Run `python java_inventory.py setup` before building."
    )


datas = [
    ("common", "common"),
    ("checkstyle/src", "checkstyle/src"),
    ("checkstyle/pom.xml", "checkstyle"),
    ("checkstyle/target", "checkstyle/target"),
    ("maven/src", "maven/src"),
    ("maven/pom.xml", "maven"),
    ("maven/target", "maven/target"),
    ("resources", "resources"),
    ("pyproject.toml", "."),
]


a = Analysis(
    [str(PROJECT_ROOT / "java_inventory.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "json",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=BLOCK_CIPHER,
    noarchive=False,
)


pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=BLOCK_CIPHER,
)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="java-inventory",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
