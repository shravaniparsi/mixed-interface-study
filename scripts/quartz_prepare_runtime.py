#!/usr/bin/env python3
"""Download the locked official Quartz control runtime; never build application code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import tarfile
import urllib.request

PROJECT = Path(__file__).resolve().parent.parent
LOCK = PROJECT / "manifests/quartz-artifact-lock.json"
FLOOR = 400 * 1024**2


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024**2), b""):
            h.update(chunk)
    return h.hexdigest()


def within(path, root):
    return path.resolve() == root.resolve() or root.resolve() in path.resolve().parents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True,
                        help="Dedicated runtime directory; pre-existing matching artifacts are reused")
    parser.add_argument("--verify-only", action="store_true",
                        help="Check existing jar hashes and JRE executable without downloads")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    root = args.runtime.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not args.verify_only and (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise SystemExit("The locked JRE archive is macOS arm64. Supply a matching platform runtime separately; this downloader does not substitute versions.")
    artifacts = lock["artifacts"] + lock["additional_declared_dependencies"]
    java = root / lock["java_relative_path"]
    for item in artifacts:
        dest = root / item["name"]
        assert within(dest, root), "Artifact path must stay in the dedicated runtime directory"
        is_java = item["name"] == "jre21.tar.gz"
        if is_java and java.exists():
            print("JRE present:", java)
            continue
        if dest.exists():
            assert sha256(dest) == item["sha256"], f"Unexpected existing bytes: {dest}"
        elif args.verify_only:
            raise SystemExit(f"Missing pinned artifact: {dest}")
        else:
            assert shutil.disk_usage(root).free > FLOOR + item["size_bytes"], "Insufficient disk reserve"
            dest.parent.mkdir(parents=True, exist_ok=True)
            partial = dest.with_suffix(dest.suffix + ".partial")
            assert not partial.exists(), f"Review existing partial download first: {partial}"
            with urllib.request.urlopen(item["url"], timeout=60) as source, partial.open("xb") as target:
                shutil.copyfileobj(source, target)
            assert partial.stat().st_size == item["size_bytes"]
            assert sha256(partial) == item["sha256"], f"Checksum mismatch: {item['name']}"
            os.replace(partial, dest)
        if is_java:
            with tarfile.open(dest, "r:gz") as archive:
                members = archive.getmembers()
                required = sum(member.size for member in members if member.isfile())
                assert shutil.disk_usage(root).free > FLOOR + required, "Insufficient extraction reserve"
                for member in members:
                    target = root / member.name
                    assert within(target, root) and not member.isdev(), "Unsafe archive member"
                    if member.issym():
                        assert within(target.parent / member.linkname, root), "Unsafe archive symlink"
                    elif member.islnk():
                        assert within(root / member.linkname, root), "Unsafe archive hard link"
                archive.extractall(root, members=members)
            assert java.exists(), "JRE layout did not match the locked distribution"
            dest.unlink()  # Regenerable verified archive; retain extracted runtime and checksum lock.
        print("Verified:", item["name"])
    dependency_bytes = (PROJECT / "manifests/quartz-declared-dependencies.json").read_bytes()
    assert hashlib.sha256(dependency_bytes).hexdigest() == lock["dependency_lock_sha256"]
    if args.verify_only:
        assert (root / "declared-dependencies.json").read_bytes() == dependency_bytes
    else:
        (root / "declared-dependencies.json").write_bytes(dependency_bytes)
    print("JRE archive provenance is checksum-locked; an already-extracted JRE is checked for presence only.")
    print("Ready. This script does not launch a server, browser, job or trigger.")


if __name__ == "__main__":
    main()
