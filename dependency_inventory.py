#!/usr/bin/env python3

"""Maven dependency inventory."""

import argparse
import csv
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

LOG = logging.getLogger("dependency_inventory")
FIELDS = (
    "module",
    "group_id",
    "artifact_id",
    "declared_version",
    "resolved_version",
    "scope",
    "direct",
    "optional",
)


class UnsupportedBuildToolError(RuntimeError):
    pass


def detect_build_tool(project_dir: Path) -> str:
    if (project_dir / "pom.xml").is_file():
        return "maven"
    if (project_dir / "build.gradle").is_file() or (project_dir / "build.gradle.kts").is_file():
        raise UnsupportedBuildToolError("Gradle is not supported yet")
    raise UnsupportedBuildToolError("no supported build tool found")


def resolve(project_dir: Path, resolver_jar: Path) -> dict:
    if shutil.which("java") is None:
        raise RuntimeError("required command not found: java")

    command = ["java", "-jar", str(resolver_jar), str(project_dir)]
    LOG.info("running: %s", " ".join(command))
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        if result.stderr:
            LOG.error(result.stderr.rstrip())
        raise RuntimeError(f"Maven resolver failed with exit code {result.returncode}")
    return json.loads(result.stdout)


def flatten(data: dict) -> list[dict]:
    rows = []
    for module in data.get("modules", []):
        module_name = module.get("path", ".")
        for dependency in module.get("dependencies", []):
            rows.append(
                {
                    "module": module_name,
                    "group_id": dependency.get("groupId"),
                    "artifact_id": dependency.get("artifactId"),
                    "declared_version": dependency.get("declaredVersion"),
                    "resolved_version": dependency.get("resolvedVersion"),
                    "scope": dependency.get("scope"),
                    "direct": dependency.get("direct", False),
                    "optional": dependency.get("optional", False),
                }
            )
    return rows


def write_output(rows: list[dict], output: Path | None, fmt: str) -> None:
    if fmt == "json":
        text = json.dumps(rows, indent=2)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return

    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)


def print_cli(rows: list[dict]) -> None:
    print("module    dependency                         declared    resolved    scope      type")
    for row in rows:
        name = f"{row['group_id']}:{row['artifact_id']}"
        kind = "direct" if row["direct"] else "transitive"
        print(
            f"{row['module']:<9} {name:<34} "
            f"{str(row['declared_version']):<11} {str(row['resolved_version']):<11} "
            f"{row['scope']:<10} {kind}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Maven dependency inventory")
    parser.add_argument("--debug", action="store_true", help="show debug logs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="inventory project dependencies")
    inventory.add_argument("project_dir", type=Path)
    inventory.add_argument("-o", "--output", type=Path)
    inventory.add_argument("--format", choices=("csv", "json"), default="csv")
    inventory.add_argument(
        "--resolver-jar",
        type=Path,
        default=Path(__file__).parent / "maven-resolver" / "target" / "maven-resolver-0.1.0-SNAPSHOT.jar",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(levelname)s: %(message)s")

    if args.command == "inventory":
        project_dir = args.project_dir.resolve()
        detect_build_tool(project_dir)
        data = resolve(project_dir, args.resolver_jar.resolve())
        rows = flatten(data)
        print_cli(rows)
        if args.output:
            write_output(rows, args.output.resolve(), args.format)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
