#!/usr/bin/env python3
"""Prepare locked Quartz jars using supplied Java 21; no platform JRE download."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlparse
from urllib.request import urlopen

PROJECT = Path(__file__).resolve().parents[2]


def artifact_path(root, name):
    target = (root / name).resolve()
    if root.resolve() not in target.parents or target.suffix != ".jar":
        raise ValueError("Jar destination must be within the dedicated runtime")
    return target


def verify_artifact(path, item):
    if path.stat().st_size != item["size_bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
        raise ValueError("Pinned artifact size or SHA256 mismatch: " + item["name"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = args.runtime.resolve()
    root.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    lock_bytes = (PROJECT / "manifests/quartz-artifact-lock.json").read_bytes()
    lock = json.loads(lock_bytes)
    report = {"status": "preparing", "artifact_lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
              "jre_source": "actions/setup-java; macOS archive deliberately not downloaded",
              "application_source_modified": False, "verified_jars": []}
    try:
        java = subprocess.run([str(args.java), "-version"], capture_output=True, text=True, check=True, timeout=10)
        report["java_version"] = (java.stdout + java.stderr).strip()
        if not re.search(r'version "21(?:\.|\")', report["java_version"]):
            raise ValueError("Supplied Java must be version 21")
        artifacts = [item for item in lock["artifacts"] + lock["additional_declared_dependencies"] if item["name"].endswith(".jar")]
        for item in artifacts:
            if urlparse(item["url"]).scheme != "https" or urlparse(item["url"]).hostname != "repo.maven.apache.org":
                raise ValueError("Unexpected artifact source")
            dest = artifact_path(root, item["name"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                if shutil.disk_usage(root).free < 400 * 1024**2 + item["size_bytes"]:
                    raise RuntimeError("Insufficient runtime disk reserve")
                partial = dest.with_suffix(dest.suffix + ".partial")
                with urlopen(item["url"], timeout=60) as source, partial.open("xb") as target:
                    total = 0
                    for chunk in iter(lambda: source.read(1024**2), b""):
                        total += len(chunk)
                        if total > item["size_bytes"]:
                            raise ValueError("Artifact exceeds pinned size")
                        target.write(chunk)
                verify_artifact(partial, item)
                partial.replace(dest)
            verify_artifact(dest, item)
            report["verified_jars"].append({"name": item["name"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]})
        dependencies = (PROJECT / "manifests/quartz-declared-dependencies.json").read_bytes()
        if hashlib.sha256(dependencies).hexdigest() != lock["dependency_lock_sha256"]:
            raise ValueError("Dependency manifest SHA256 mismatch")
        (root / "declared-dependencies.json").write_bytes(dependencies)
        report["status"] = "prepared_not_started"
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        args.report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
