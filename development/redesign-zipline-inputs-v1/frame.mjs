import {canonical,sha} from '../redesign-zipline-state-v2/state.mjs';
import {put} from './actions.mjs';
export function frame(before,after,id,changes){
 const expected=structuredClone(before),actual=structuredClone(after);
 const old=before.tables['public.Url'].rows.find(r=>r.id===id),row=actual.tables['public.Url'].rows.find(r=>r.id===id),want=expected.tables['public.Url'].rows.find(r=>r.id===id);
 if(!old||!row||typeof row.updatedAt!=='string'||typeof old.updatedAt!=='string'||!Number.isFinite(Date.parse(row.updatedAt))||!Number.isFinite(Date.parse(old.updatedAt))||Date.parse(row.updatedAt)<Date.parse(old.updatedAt))return false;
 for(const [pointer,value] of Object.entries(changes))put(want,pointer,value);
 row.updatedAt=old.updatedAt;
 for(const s of [expected,actual]){const t=s.tables['public.Url'];t.rows.sort((a,b)=>canonical(a).localeCompare(canonical(b),'en'));t.row_sha256=t.rows.map(r=>sha(canonical(r)));}
 return canonical(expected)===canonical(actual);
}
