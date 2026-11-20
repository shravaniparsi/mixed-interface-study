/** Bounded response-body observation. Timeouts mean unavailable capture, never UI blocking. */
export function createCapture({bodyTimeoutMs=2000,flushTimeoutMs=2500,write,now=()=>Date.now()}={}) {
 if(typeof write!=='function')throw new TypeError('write callback required');
 for(const value of [bodyTimeoutMs,flushTimeoutMs])if(!Number.isFinite(value)||value<1)throw new RangeError('positive finite timeout required');
 const rows=[],pending=new Set(),finishers=new Set();let closed=false,writeError;
 function checkpoint(){write(structuredClone(rows));}
 function observe(metadata,readBody){
  if(closed)throw new Error('capture closed');
  const row={...structuredClone(metadata),capture:{status:'pending',startedAt:now()}};rows.push(row);checkpoint();
  let timer,settled=false;
  const task=new Promise(resolve=>{
   const finish=(status,value)=>{
    if(settled)return;settled=true;clearTimeout(timer);finishers.delete(finish);
    row.capture={...row.capture,status,completedAt:now(),...(status==='complete'?{body:value}:status==='error'?{error:String(value)}:{})};
    try{checkpoint();}catch(e){writeError=e;}resolve();
   };
   finishers.add(finish);
   timer=setTimeout(()=>finish('body_timeout'),bodyTimeoutMs);
   Promise.resolve().then(readBody).then(value=>finish('complete',value),error=>finish('error',error));
  });
  pending.add(task);task.then(()=>pending.delete(task));return row;
 }
 async function close(){
  closed=true;checkpoint();let timer;
  await Promise.race([Promise.allSettled([...pending]),new Promise(resolve=>{timer=setTimeout(resolve,flushTimeoutMs);})]);clearTimeout(timer);
  for(const finish of [...finishers])finish('flush_timeout');
  if(writeError)throw writeError;
  checkpoint();return structuredClone(rows);
 }
 return {observe,checkpoint,close,snapshot:()=>structuredClone(rows)};
}
