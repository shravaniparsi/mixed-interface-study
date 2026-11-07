#!/usr/bin/env python3
"""Record a small, allowlisted CI resource inventory; never dump the environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]


def version(command):
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=10, check=False)
        return {"exit_code": result.returncode, "output": result.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"error_type": type(error).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        memory_bytes = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError):
        memory_bytes = None
    report = {"platform": platform.platform(), "architecture": platform.machine(),
              "logical_cpus": os.cpu_count(), "physical_memory_bytes": memory_bytes, "python": sys.version,
              "node": version(["node", "--version"]), "java": version(["java", "-version"]),
              "git_commit": version(["git", "-C", str(PROJECT), "rev-parse", "HEAD"]),
              "runner": {key: os.environ.get(key) for key in
                         ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA")},
              "free_disk_bytes": shutil.disk_usage(PROJECT).free,
              "pins_sha256": {}}
    paths = list((PROJECT / ".github/workflows").glob("*.yml")) + [
        PROJECT / "manifests/quartz-artifact-lock.json", PROJECT / "manifests/realworld-python-lock.txt",
        PROJECT / "scripts/ci/package.json"]
    for path in paths:
        report["pins_sha256"][str(path.relative_to(PROJECT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
