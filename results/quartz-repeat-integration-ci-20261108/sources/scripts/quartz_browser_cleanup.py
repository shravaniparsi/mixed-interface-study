#!/usr/bin/env python3
"""Reuse the shared identity-verified cleanup after the Quartz launcher exits."""
import argparse
import json
from realworld_case_worker import cleanup_browser

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', required=True)
    args = parser.parse_args()
    result = cleanup_browser(args.metadata)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['ok'] else 1)
