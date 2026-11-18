#!/usr/bin/env python3
"""Run only in the original pinned Viseron environment in a registered job.

Uses the actual route's Voluptuous object; no translated/invented JSON Schema.
Does not instantiate the application, call the mutation or persist user records.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Refuse schema report overwrite')
    raw = args.request_file.read_bytes()
    request = json.loads(raw)
    result = {'status': 'unavailable', 'baseline': 'original_executable_api_schema',
              'dialect': 'Voluptuous', 'route': '/auth/create', 'method': 'POST',
              'request_sha256': hashlib.sha256(raw).hexdigest(),
              'mutation_called': False}
    try:
        version = importlib.metadata.version('voluptuous')
        result['validator_version'] = version
        if version != '0.16.0':
            raise RuntimeError('Unqualified validator version')
        import voluptuous as vol
        from viseron.components.webserver.api.v1 import auth as auth_module
        source_hash = hashlib.sha256(Path(auth_module.__file__).read_bytes()).hexdigest()
        result['original_auth_source_sha256'] = source_hash
        if source_hash != '0c019600f23ed4483817663b0159e0dfa15735f93f6482a08213738c41eb8dad':
            raise RuntimeError('Original auth source mismatch')
        AuthAPIHandler = auth_module.AuthAPIHandler
        routes = [route for route in AuthAPIHandler.routes
                  if route.get('path_pattern') == '/auth/create'
                  and route.get('supported_methods') == ['POST']]
        if len(routes) != 1:
            raise RuntimeError('Original route mapping mismatch')
        schema = routes[0]['json_body_schema']
        try:
            validated = schema(request)
        except vol.Invalid as error:
            # Retain structural paths/classes without exposing rejected values.
            result.update(status='evaluated', accepted=False,
                          errors=[{'type': type(item).__name__,
                                   'path': [str(value) for value in item.path]}
                                  for item in getattr(error, 'errors', [error])])
        else:
            result.update(status='evaluated', accepted=True,
                          validated_body_equals_input=(validated == request))
    except Exception as error:
        result.update(error_type=type(error).__name__)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'evaluated':
        raise RuntimeError('Original schema baseline unavailable; see report')


if __name__ == '__main__':
    main()
