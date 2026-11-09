#!/usr/bin/env python3
"""Shallow pinned RealWorld checkouts and declared dependency build, without app patches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]
BACKEND = ("https://github.com/c4ffein/realworld-django-ninja.git", "87dd078c883a046f5ff20269df2fb004d8b5f83f")
FRONTEND = ("https://github.com/mutoe/vue3-realworld-example-app.git", "b14ba5011cf9cc97babfcd7ca99dcfbb058862e7")


def run(command, cwd, env=None, timeout=180):
    subprocess.run([str(item) for item in command], cwd=cwd, env=env, check=True, timeout=timeout)


def checkout(path, source):
    path.mkdir(parents=True, exist_ok=True)
    if (path / ".git").exists():
        raise ValueError("Use a fresh CI runtime checkout")
    run(["git", "init", "--quiet"], path, timeout=30)
    run(["git", "remote", "add", "origin", source[0]], path, timeout=30)
    run(["git", "fetch", "--depth=1", "--no-tags", "origin", source[1]], path, timeout=60)
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], path, timeout=30)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    if actual != source[1]:
        raise ValueError("Unexpected source revision")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--node-tools", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = args.runtime.resolve()
    root.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    subject = root / "realworld-django-ninja"
    frontend = subject / "fronts/vue3-realworld-example-app"
    python = root / "venv/bin/python"
    node = shutil.which("node")
    lock = PROJECT / "manifests/realworld-python-lock.txt"
    report = {"status": "preparing", "backend_commit": BACKEND[1], "frontend_commit": FRONTEND[1],
              "python_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
              "dependency_substitution": "The existing study lock uses psycopg2-binary 2.9.10; SQLite only.",
              "application_source_modified": False, "commands_completed": []}
    try:
        if not node or sys.version_info[:2] != (3, 12):
            raise RuntimeError("CI preparation requires configured Python 3.12 and Node 20")
        if not subprocess.check_output([node, "--version"], text=True).startswith("v20."):
            raise RuntimeError("Node 20 is required")
        checkout(subject, BACKEND)
        checkout(frontend, FRONTEND)
        report["commands_completed"].append("pinned_shallow_checkouts")
        run([sys.executable, "-m", "venv", root / "venv"], root, timeout=60)
        install_report = args.report.resolve().with_name("realworld-pip-install.json")
        run([python, "-m", "pip", "install", "--no-cache-dir", "--report", install_report, "-r", lock], root)
        report["python_install_report"] = install_report.name
        report["commands_completed"].append("locked_python_environment")
        env = dict(os.environ, CYPRESS_INSTALL_BINARY="0", VITE_API_HOST="http://127.0.0.1:18765", TZ="UTC")
        pnpm = args.node_tools.resolve() / "node_modules/pnpm/bin/pnpm.cjs"
        run([node, pnpm, "install", "--frozen-lockfile", "--ignore-scripts", "--store-dir", root / "pnpm-store"], frontend, env)
        run([node, frontend / "node_modules/vite/bin/vite.js", "build"], frontend, env, timeout=120)
        for path in (subject, frontend):
            run(["git", "diff", "--exit-code", "HEAD", "--"], path, timeout=30)
        report["commands_completed"].append("frozen_frontend_install_and_build")
        report["resolved_python_packages"] = subprocess.check_output([python, "-m", "pip", "freeze", "--all"], text=True).splitlines()
        report["frontend_lock_sha256"] = hashlib.sha256((frontend / "pnpm-lock.yaml").read_bytes()).hexdigest()
        report.update(status="prepared_not_started", subject=str(subject), python=str(python), node=node)
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        args.report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
