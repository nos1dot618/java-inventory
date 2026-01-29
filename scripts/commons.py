import subprocess
import sys
import os
from pathlib import Path


def error(message):
    print(f"[\033[31mERROR\033[0m] {message}")


def info(message):
    print(f"[\033[34mINFO\033[0m] {message}")


def testDirPath(path: Path):
    if not path.exists():
        error(f"'{path}' does not exist.")
        sys.exit(1)
    if not path.is_dir():
        error(f"'{path}' is not a directory.")
        sys.exit(1)


def runCheckstyleCheck(configName: str, targetDir: Path) -> str:
    ROOT = Path(__file__).parent.parent
    CHECKSTYLE_JAR_PATH = ROOT / "resources" / "checkstyle-12.3.0-all.jar"
    CHECKS_JAR_PATH = ROOT / "build" / "CheckstyleChecks.jar"
    CONFIG_FILE_PATH = ROOT / "resources" / "configs" / f"{configName}.xml"
    classpath = os.pathsep.join([str(CHECKSTYLE_JAR_PATH), str(CHECKS_JAR_PATH)])
    cmd = [
        "java",
        "-cp",
        classpath,
        "com.puppycrawl.tools.checkstyle.Main",
        "-c",
        str(CONFIG_FILE_PATH),
        str(targetDir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout
