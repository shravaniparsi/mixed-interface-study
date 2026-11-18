"""Verify ordinary access-file credentials before permitting salt differences.

Input database state and passwords are PRIVATE. The caller supplies the hash
function executed by the verified application image's OpenSSL, not a substitute
algorithm. This component covers one-item ordinary lists only.
"""
import hashlib
import json
import re
import unicodedata


def ordinary_credential(state, list_id):
    if type(list_id) is not int or list_id <= 0:
        raise ValueError('Positive stable list ID required')
    tables = [t for t in state['tables'] if t['name'] == 'access_list_auth']
    if len(tables) != 1:
        raise ValueError('Original auth table missing or ambiguous')
    table = tables[0]
    names = []
    for column in table['columns']:
        if column[1][0] != 'text':
            raise ValueError('Malformed original-driver column name')
        names.append(column[1][1])
    if len(set(names)) != len(names) or not {'access_list_id', 'username', 'password'} <= set(names):
        raise ValueError('Original auth columns missing or ambiguous')
    credentials = []
    for raw in table['rows']:
        cells = json.loads(raw)
        if len(cells) != len(names):
            raise ValueError('Original-driver row shape differs')
        row = dict(zip(names, cells))
        if row['access_list_id'] != ['integer', str(list_id)]:
            continue
        if any(len(row[k]) != 2 or row[k][0] != 'text' or not isinstance(row[k][1], str) for k in ('username', 'password')):
            raise ValueError('Ordinary credential is not stored text')
        username, password = row['username'][1], row['password'][1]
        if not username or ':' in username or any(unicodedata.category(c) == 'Cc' for c in username):
            raise ValueError('Ordinary username is not an access-file line value')
        if not password or '\n' in password or '\r' in password or '\0' in password:
            raise ValueError('Ordinary password unsupported by stdin verification')
        credentials.append((username, password))
    if len(credentials) != 1:
        raise ValueError('Ordinary comparison requires exactly one stored auth row')
    return credentials[0]


def verify_access_file(raw, credential, derive_hash):
    if not isinstance(raw, bytes) or len(raw) > 4096:
        raise ValueError('Access-file byte bound/type')
    username, password = credential
    prefix = (username + ':').encode('utf8')
    if not raw.startswith(prefix) or not raw.endswith(b'\n'):
        raise ValueError('Access file does not contain the expected username/line ending')
    encoded = raw[len(prefix):-1].decode('ascii')
    match = re.fullmatch(r'\$apr1\$([./0-9A-Za-z]{8})\$[./0-9A-Za-z]{22}', encoded)
    if not match:
        raise ValueError('Unexpected APR1 representation, extra line or extra credential')
    expected = derive_hash(password, match.group(1))
    if not isinstance(expected, str) or expected != encoded:
        raise ValueError('Generated file does not authenticate the persisted credential')
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'verified_rows': 1}


def compare_ordinary_access_files(left, right, left_database, right_database, list_id, derive_hash):
    left_credential = ordinary_credential(left_database, list_id)
    right_credential = ordinary_credential(right_database, list_id)
    if left_credential != right_credential:
        raise ValueError('Persisted credentials differ; salt equivalence does not apply')
    return {'status': 'ordinary_credentials_verified_other_state_unqualified',
            'left': verify_access_file(left, left_credential, derive_hash),
            'right': verify_access_file(right, right_credential, derive_hash),
            'raw_bytes_equal': left == right}
