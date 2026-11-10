"""Independent Python reconstruction of the Node monotonic cost record."""
import hashlib,json,math
from mixed_interface.repetition import require
SCOPE='petclinic_branch_reset_through_raw_validation_and_owned_cleanup_v1'
FIELDS={'schema_version','scope','candidate_id','oracle','started_monotonic_s','finished_monotonic_s',
        'observed_elapsed_s','branch_total_s','raw_sha256','measurement_status','incomplete_reason'}
def finite(v):return type(v) in (int,float) and math.isfinite(v) and v>=0

def validate_cost(record,raw_bytes=None):
    require(set(record)==FIELDS and type(record['schema_version']) is int and record['schema_version']==1 and record['scope']==SCOPE,'Timing schema differs')
    require(isinstance(record['candidate_id'],str) and bool(record['candidate_id']) and record['oracle'] in ('api_semantic','fresh_ui'),'Timing identity differs')
    start=record['started_monotonic_s'];end=record['finished_monotonic_s'];require(finite(start),'Invalid start clock')
    if end is None:
        require(record['measurement_status']=='incomplete_interval' and record['incomplete_reason']=='end_not_observed' and
                all(record[k] is None for k in ('observed_elapsed_s','branch_total_s','raw_sha256')),'Missing end promoted')
        return record
    require(finite(end) and end>=start and type(record['observed_elapsed_s']) in (int,float) and record['observed_elapsed_s']==end-start,'Invalid interval')
    require(raw_bytes is not None,'Final interval lacks raw evidence');raw=json.loads(raw_bytes)
    require(record['raw_sha256']==hashlib.sha256(raw_bytes).hexdigest() and raw['candidate_id']==record['candidate_id'] and raw['oracle']==record['oracle'],'Cost/raw binding differs')
    require(isinstance(raw.get('status'),str) and raw['status'] and raw['status']!='running','Raw branch unfinished')
    cleanup=raw.get('backend_cleanup',{}).get('confirmed') is True and raw.get('context_cleanup_confirmed') is True
    if record['measurement_status']=='complete_interval':
        require(cleanup and record['incomplete_reason'] is None and type(record['branch_total_s']) in (int,float) and record['branch_total_s']==end-start,'Complete interval lacks cleanup or duration')
    else:
        require(record['measurement_status']=='incomplete_interval' and not cleanup and record['incomplete_reason']=='owned_cleanup_unconfirmed' and record['branch_total_s'] is None,'Incomplete cost promoted')
    return record
