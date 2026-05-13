from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from zipfile import BadZipFile, ZipFile


DEFAULT_IMAGE = "neo4j:5.20-community"
DEFAULT_AUTH = "neo4j/temp12345"
DEFAULT_PLUGINS_JSON = '["apoc", "graph-data-science"]'
DEFAULT_TIMEOUT_SECONDS = 240


def _run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        capture_output=capture,
    )


def _cleanup_container(container_name: str) -> None:
    subprocess.run(["docker", "rm", "-f", container_name], check=False, capture_output=True, text=True)


def _plugin_ready(plugin_dir: Path) -> bool:
    jar_names = {path.name.lower() for path in plugin_dir.glob("*.jar")}
    has_apoc = any("apoc" in name for name in jar_names)
    has_gds = any("graph-data-science" in name or "neo4j-graph-data-science" in name for name in jar_names)
    return has_apoc and has_gds


def _plugin_archives_valid(plugin_dir: Path) -> bool:
    jar_paths = list(plugin_dir.glob("*.jar"))
    if not jar_paths:
        return False
    for jar_path in jar_paths:
        try:
            with ZipFile(jar_path, "r") as archive:
                archive.namelist()
        except (BadZipFile, OSError):
            return False
    return _plugin_ready(plugin_dir)


def _container_plugin_paths(container_name: str) -> list[str]:
    result = _run(
        [
            "docker",
            "exec",
            container_name,
            "sh",
            "-lc",
            "find /plugins /var/lib/neo4j/plugins -maxdepth 1 -type f -name '*.jar' 2>/dev/null | sort",
        ],
        capture=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _copy_plugins_from_container(container_name: str, plugin_dir: Path) -> list[str]:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source_path in _container_plugin_paths(container_name):
        _run(["docker", "cp", f"{container_name}:{source_path}", str(plugin_dir / Path(source_path).name)])
        copied.append(Path(source_path).name)
    return copied


def preload_plugins(plugin_dir: Path, *, image: str, auth: str, timeout_seconds: int) -> list[str]:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    if _plugin_archives_valid(plugin_dir):
        return sorted(path.name for path in plugin_dir.glob("*.jar"))

    container_name = "neo4j-plugin-preload"
    _cleanup_container(container_name)
    try:
        _run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-e",
                f"NEO4J_AUTH={auth}",
                "-e",
                f"NEO4J_PLUGINS={DEFAULT_PLUGINS_JSON}",
                image,
            ]
        )

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            copied = _copy_plugins_from_container(container_name, plugin_dir)
            if copied and _plugin_archives_valid(plugin_dir):
                return sorted(path.name for path in plugin_dir.glob("*.jar"))
            time.sleep(3)

        logs = _run(["docker", "logs", container_name], capture=True).stdout.strip()
        raise RuntimeError(f"plugin preload timed out after {timeout_seconds}s\n{logs}")
    finally:
        _cleanup_container(container_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preload APOC and GDS jars into a host plugin directory.")
    parser.add_argument("--plugin-dir", default="runtime/neo4j/plugins", help="Host directory to store plugin jars.")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Neo4j image used for plugin preloading.")
    parser.add_argument("--auth", default=DEFAULT_AUTH, help="Temporary NEO4J_AUTH value for the preload container.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Max wait time in seconds.")
    parser.add_argument("--clean", action="store_true", help="Delete the plugin directory before preloading.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plugin_dir = Path(args.plugin_dir)
    if args.clean and plugin_dir.exists():
        shutil.rmtree(plugin_dir, ignore_errors=True)

    try:
        jar_names = preload_plugins(
            plugin_dir,
            image=args.image,
            auth=args.auth,
            timeout_seconds=max(30, int(args.timeout or DEFAULT_TIMEOUT_SECONDS)),
        )
    except Exception as exc:
        print(f"[FAIL] neo4j plugin preload: {exc}")
        return 1

    print(f"[OK] neo4j plugin preload: {plugin_dir.resolve()}")
    for jar_name in jar_names:
        print(f"  - {jar_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())