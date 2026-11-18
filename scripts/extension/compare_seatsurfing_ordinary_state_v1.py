#!/usr/bin/env python3
"""Pure operation-specific comparison; retains rather than erases audit values."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json


def epoch_microseconds(value):
    if not isinstance(value,str): raise ValueError('Timestamp must be retained text')
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=timezone.utc)
    delta=parsed.astimezone(timezone.utc)-datetime(1970,1,1,tzinfo=timezone.utc)
    return (delta.days*86400+delta.seconds)*1000000+delta.microseconds


def bind_rows(snapshot):
    if snapshot.get('status')!='paused_comparison_state_captured' or snapshot.get('field_exclusions')!=[]:
        raise ValueError('Require complete unfiltered paused snapshot')
    required={'tables','sequences','schema_sha256','roles_sha256','memberships_sha256','role_database_settings_sha256','database_configuration_sha256','tablespaces_sha256','settings_sha256'}
    if set(snapshot['state'])!=required: raise ValueError('Incomplete database metadata fingerprint')
    rows={}
    for table in snapshot['row_data']:
        key=(table['schema_name'],table['relation_name'])
        if key in rows: raise ValueError('Duplicate table evidence')
        rows[key]=table['rows']
    expected={}
    for table in snapshot['state']['tables']:
        key=(table['schema_name'],table['relation_name'])
        if key in expected: raise ValueError('Duplicate table fingerprint')
        expected[key]=table
    if set(rows)!=set(expected): raise ValueError('Incomplete table row evidence')
    for key,lines in rows.items():
        table=expected[key]
        raw=('\n'.join(sorted(lines))+ ('\n' if lines else '')).encode()
        if len(lines)!=table['rows'] or hashlib.sha256(raw).hexdigest()!=table['sha256']:
            raise ValueError('Row evidence does not bind full fingerprint')
    return rows


def selected_row(lines, identity):
    matched=[];others=[]
    for raw in lines:
        row=json.loads(raw,parse_float=Decimal)
        if row.get('id')==identity: matched.append(row)
        else: others.append(raw)
    if len(matched)!=1: raise ValueError('Require exactly one selected original row')
    return matched[0],Counter(others)


def compare_ordinary_state(before, after, *, session_id, location_id, window_start_us, window_end_us, edit=None):
    if not all(isinstance(x,int) for x in (window_start_us,window_end_us)) or window_start_us>window_end_us:
        raise ValueError('Require ordered recorded operation window')
    if window_end_us-window_start_us>180*1000000:
        raise ValueError('Ordinary operation window exceeds three-minute bound')
    left,right=bind_rows(before),bind_rows(after)
    if set(left)!=set(right): raise ValueError('Database table set changed')
    meta_left={k:v for k,v in before['state'].items() if k!='tables'}
    meta_right={k:v for k,v in after['state'].items() if k!='tables'}
    if meta_left!=meta_right: raise ValueError('Schema/sequence/role/database configuration changed')
    descriptors=lambda s: sorted((t['schema_name'],t['relation_name'],t['relkind'],t['rows']) for t in s['state']['tables'])
    if descriptors(before)!=descriptors(after): raise ValueError('Relation kind or row count changed')
    special={('public','sessions'),('public','locations')}
    if not special.issubset(left): raise ValueError('Original session/location relations missing')
    for table in set(left)-special:
        if Counter(left[table])!=Counter(right[table]): raise ValueError('Unrelated table changed: '+'.'.join(table))
    old_session,other_old=selected_row(left[('public','sessions')],session_id)
    new_session,other_new=selected_row(right[('public','sessions')],session_id)
    if other_old!=other_new: raise ValueError('Another session changed')
    old_activity=old_session.pop('last_activity');new_activity=new_session.pop('last_activity')
    if old_session!=new_session: raise ValueError('Session identity/lifetime or other session fields changed')
    previous,current=epoch_microseconds(old_activity),epoch_microseconds(new_activity)
    if not(previous<=current and window_start_us<=current<=window_end_us):
        raise ValueError('Session activity is not monotonic within the recorded operation window')
    old_location,other_old=selected_row(left[('public','locations')],location_id)
    new_location,other_new=selected_row(right[('public','locations')],location_id)
    if other_old!=other_new: raise ValueError('Another location changed')
    target_change=None
    if edit is not None:
        edits=[{'path':'/description','value':'Edit description'},{'path':'/announcement','value':'Edit notice'}]
        if edit not in edits: raise ValueError('Edit not in frozen ordinary schedule')
        field=edit['path'][1:]
        prior=old_location[field]
        if prior==edit['value']: raise ValueError('Ordinary edit must change the original value')
        old_location[field]=edit['value']
        target_change={'field':field,'before':prior,'after':edit['value']}
    if old_location!=new_location: raise ValueError('Location changed outside the prescribed ordinary scalar edit')
    return {'status':'ordinary_operation_state_matches','mode':'edit' if edit else 'restart_and_load',
            'session_activity':{'session_id':session_id,'before':old_activity,'after':new_activity,
                'window_start_us':window_start_us,'window_end_us':window_end_us},
            'target_change':target_change,'all_other_rows_and_metadata_unchanged':True,
            'native_request_equality_verified':False,'runtime_qualified':False}
