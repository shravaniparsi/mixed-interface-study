#!/usr/bin/env python3
"""Capture one immutable committed-state backup for an adapter-owned checkpoint."""
import argparse
import json
from pathlib import Path
from realworld_identity_db_state_v1 import backup


def capture(database, directory, stage):
    if stage not in ('before_prefix', 'after_prefix', 'after_continuation'):
        raise ValueError('Unregistered database checkpoint')
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('Snapshot directory must be precreated for this branch')
    return backup(database, directory / (stage + '.sqlite3'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    print(json.dumps(capture(args.database, args.directory, args.stage)))


if __name__ == '__main__': main()
