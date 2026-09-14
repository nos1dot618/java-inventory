"""Maven dependency inventory commands."""

# pylint: disable=missing-function-docstring

import csv
import json
from pathlib import Path

from common.inventory_common import (
    InventoryError,
    UnsupportedBuildToolError,
    info,
    read_pom_coordinates,
    require_command,
    require_directory,
    require_file,
    run,
    success,
)

RESOLVER_JAR = None


# pylint: disable=global-statement
def configure(root: Path):
    global RESOLVER_JAR
    artifact_id, version = read_pom_coordinates(root / "maven" / "pom.xml")
    RESOLVER_JAR = root / "maven" / "target" / f"{artifact_id}-{version}.jar"


def detect_build_tool(project_dir: Path):
    if (project_dir / "pom.xml").is_file():
        return "maven"
    if (project_dir / "build.gradle").is_file() or (
        project_dir / "build.gradle.kts"
    ).is_file():
        raise UnsupportedBuildToolError("Gradle projects are not supported")
    raise UnsupportedBuildToolError(
        f"unsupported or unrecognized build tool: {project_dir}"
    )


def build_resolver(root: Path):
    require_command("mvn")
    run(["mvn", "package", "-q"], cwd=root / "maven")
    require_file(RESOLVER_JAR, "Maven resolver JAR")
    success(f"generated '{RESOLVER_JAR}'")


def resolve(project_dir: Path, root: Path):
    require_directory(project_dir, "Maven project directory")
    detect_build_tool(project_dir)
    if not RESOLVER_JAR.is_file():
        info("Maven resolver JAR not found; building it")
        build_resolver(root)
    result = run(
        ["java", "-jar", str(RESOLVER_JAR), str(project_dir)], capture_output=True
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InventoryError("Maven resolver returned invalid JSON") from exc


def records(data):
    result = []
    for module in data.get("modules", []):
        module_name = module.get("path") or module.get("artifactId") or ""
        for dependency in module.get("dependencies", []):
            result.append(
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
    return result


def print_records(rows):
    print(
        "module\tgroupId:artifactId\tdeclared\tresolved\tscope\tdirect/transitive\toptional"
    )
    for row in rows:
        relation = "direct" if row["direct"] else "transitive"
        coordinate = f"{row['group_id']}:{row['artifact_id']}"
        print(
            "\t".join(
                [
                    str(row["module"] or ""),
                    coordinate,
                    str(row["declared_version"] or ""),
                    str(row["resolved_version"] or ""),
                    str(row["scope"] or ""),
                    relation,
                    str(row["optional"]),
                ]
            )
        )


def write_output(rows, output_file: Path, output_format: str):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        output_file.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    else:
        with output_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "module",
                    "group_id",
                    "artifact_id",
                    "declared_version",
                    "resolved_version",
                    "scope",
                    "direct",
                    "optional",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
    success(f"{output_format.upper()} report generated '{output_file}'")


def inventory(
    project_dir: Path, output_file: Path | None, output_format: str, root: Path
):
    data = resolve(project_dir, root)
    rows = records(data)
    if output_file:
        write_output(rows, output_file, output_format)
    else:
        print_records(rows)
    info(f"dependencies found: {len(rows)}")


def subcommand_setup(_args, root: Path):
    require_command("mvn")
    build_resolver(root)


def register_commands(subparsers, root: Path, setup_handlers):
    configure(root)
    setup_handlers.append(lambda args: subcommand_setup(args, root))

    parser = subparsers.add_parser("inventory-dependency", help="inventory Maven dependencies")
    parser.add_argument("project_dir", type=Path, help="Maven project directory")
    parser.add_argument("-o", "--output", type=Path, help="output CSV or JSON file")
    parser.add_argument(
        "--format", choices=("csv", "json"), default="csv", help="output format"
    )
    parser.set_defaults(
        handler=lambda args: inventory(
            args.project_dir.resolve(),
            args.output.resolve() if args.output else None,
            args.format,
            root,
        )
    )
