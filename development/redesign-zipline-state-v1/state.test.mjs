import assert from 'node:assert/strict';
import {canonical,sha,compareFrame} from './state.mjs';
const row={id:'target',destination:'https://example.com/api',updatedAt:'2026-01-01T00:00:00Z',vanity:null};
const base={metadata:{schema:'original'},tables:{'public.urls':{rows:[row],row_sha256:[sha(canonical(row))]},'public.users':{rows:[{id:'actor',role:'admin'}],row_sha256:['original']}},sequences:{},files:[]};
const after=structuredClone(base);Object.assign(after.tables['public.urls'].rows[0],{destination:'https://example.com/edited',updatedAt:'2026-01-01T00:00:01Z'});
const options={table:'public.urls',id:'target',destination:'https://example.com/edited'};
assert(compareFrame(base,after,options));
for(const change of [x=>x.tables['public.users'].rows[0].role='user',x=>delete x.tables['public.urls'].rows[0].vanity,x=>x.files.push({path:'unexpected'}),x=>x.sequences.counter=2,x=>x.metadata.schema='changed',x=>x.tables['public.urls'].rows[0].updatedAt='2025-01-01T00:00:00Z',x=>x.tables['public.urls'].rows[0].updatedAt='invalid',x=>x.tables['public.urls'].rows[0].destination='wrong']){const x=structuredClone(after);change(x);assert(!compareFrame(base,x,options));}
console.log('frame tests passed: intended edit, actor/field/file/sequence/schema changes, timestamp regression, wrong destination');
