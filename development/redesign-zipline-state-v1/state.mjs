/** Independent PostgreSQL logical state observer; no application code is imported. */
import {createRequire} from 'node:module';
import {readFileSync,readdirSync,lstatSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
export const canonical=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
export const sha=x=>createHash('sha256').update(x).digest('hex');
const qi=x=>'"'+x.replaceAll('"','""')+'"';
export function files(root){
 const rows=[];
 function walk(p){for(const name of readdirSync(p).sort()){const f=path.join(p,name),s=lstatSync(f),rel=path.relative(root,f);if(s.isSymbolicLink())throw new Error('state symlink unsupported: '+rel);if(s.isDirectory()){rows.push({path:rel,type:'directory',mode:s.mode&0o777});walk(f);}else if(s.isFile()){rows.push({path:rel,type:'file',mode:s.mode&0o777,bytes:s.size,sha256:sha(readFileSync(f))});}else throw new Error('unsupported state file: '+rel);}}
 walk(root);return rows;
}
export async function snapshot({runtime,databaseUrl,fileRoot}){
 const {Client}=createRequire(path.join(runtime,'package.json'))('pg');const c=new Client({connectionString:databaseUrl});await c.connect();
 try{
  await c.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');await c.query("SET LOCAL TIME ZONE 'UTC'");
  const metadata={};
  metadata.schemas=(await c.query("SELECT nspname,pg_get_userbyid(nspowner) owner,nspacl::text acl FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema' ORDER BY nspname")).rows;
  metadata.relations=(await c.query("SELECT n.nspname AS schema,c.relname AS name,c.relkind AS kind,pg_get_userbyid(c.relowner) owner,c.relacl::text acl,c.relrowsecurity,c.relforcerowsecurity,c.relpersistence FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND c.relkind IN ('r','p','v','m','S','f') ORDER BY n.nspname,c.relname")).rows;
  if(metadata.relations.some(r=>!['r','S'].includes(r.kind)))throw new Error('unsupported relation kind in state scope');
  metadata.columns=(await c.query("SELECT n.nspname AS schema,c.relname AS table,a.attnum,a.attname,format_type(a.atttypid,a.atttypmod) type,a.attnotnull,a.attacl::text acl,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid) default_expr FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attnum>0 AND NOT a.attisdropped AND c.relkind IN ('r','S') AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema' ORDER BY n.nspname,c.relname,a.attnum")).rows;
  metadata.constraints=(await c.query("SELECT n.nspname AS schema,c.relname AS table,k.conname,pg_get_constraintdef(k.oid,true) definition FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' ORDER BY n.nspname,c.relname,k.conname")).rows;
  metadata.indexes=(await c.query("SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes WHERE schemaname !~ '^pg_' AND schemaname<>'information_schema' ORDER BY schemaname,tablename,indexname")).rows;
  metadata.triggers=(await c.query("SELECT n.nspname AS schema,c.relname AS table,t.tgname,pg_get_triggerdef(t.oid,true) definition,t.tgenabled FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema' ORDER BY n.nspname,c.relname,t.tgname")).rows;
  metadata.extensions=(await c.query('SELECT extname,extversion FROM pg_extension ORDER BY extname')).rows;
  metadata.enums=(await c.query("SELECT n.nspname AS schema,t.typname,e.enumsortorder,e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname !~ '^pg_' ORDER BY n.nspname,t.typname,e.enumsortorder")).rows;
  metadata.sequence_parameters=(await c.query("SELECT n.nspname AS schema,c.relname AS name,format_type(s.seqtypid,NULL) type,s.seqstart::text,s.seqincrement::text,s.seqmax::text,s.seqmin::text,s.seqcache::text,s.seqcycle FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname !~ '^pg_' ORDER BY n.nspname,c.relname")).rows;
  metadata.policies=(await c.query("SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies WHERE schemaname !~ '^pg_' ORDER BY schemaname,tablename,policyname")).rows;
  metadata.routines=(await c.query("SELECT n.nspname AS schema,p.proname,pg_get_function_identity_arguments(p.oid) arguments,pg_get_functiondef(p.oid) definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND p.prokind IN ('f','p') AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e') ORDER BY n.nspname,p.proname,arguments")).rows;
  const unsupported=(await c.query("SELECT n.nspname,t.typname,t.typtype FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND t.typtype IN ('d','r','m') AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_type'::regclass AND d.objid=t.oid AND d.deptype='e')")).rows;if(unsupported.length)throw new Error('unsupported custom domain/range types');
  const tables={},sequences={};
  for(const r of metadata.relations){const key=r.schema+'.'+r.name,q=qi(r.schema)+'.'+qi(r.name);if(r.kind==='S')sequences[key]=(await c.query('SELECT last_value::text,is_called FROM '+q)).rows;else{const rows=(await c.query('SELECT to_jsonb(t) AS value FROM '+q+' t')).rows.map(x=>x.value).sort((a,b)=>canonical(a).localeCompare(canonical(b),'en'));tables[key]={rows,row_sha256:rows.map(x=>sha(canonical(x)))};}}
  await c.query('COMMIT');return {metadata,tables,sequences,files:files(fileRoot)};
 }catch(e){await c.query('ROLLBACK').catch(()=>{});throw e;}finally{await c.end();}
}
export function compareFrame(before,after,{table,id,destination}){
 const b=structuredClone(before),a=structuredClone(after);const rows=a.tables[table]?.rows,prior=b.tables[table]?.rows;
 if(!rows||!prior) return false;
 const target=rows.find(x=>x.id===id),old=prior.find(x=>x.id===id);
 if(!target||!old||target.destination!==destination||typeof target.updatedAt!=='string'||typeof old.updatedAt!=='string'||!Number.isFinite(Date.parse(target.updatedAt))||!Number.isFinite(Date.parse(old.updatedAt))||Date.parse(target.updatedAt)<Date.parse(old.updatedAt))return false;
 target.destination=old.destination;target.updatedAt=old.updatedAt;
 for(const state of [a,b]){state.tables[table].rows.sort((x,y)=>canonical(x).localeCompare(canonical(y),'en'));state.tables[table].row_sha256=state.tables[table].rows.map(x=>sha(canonical(x)));}
 return canonical(a)===canonical(b);
}
