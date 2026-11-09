export async function stopOwnedProcess(child,{graceMs=5000,killMs=2000}={}) {
  if(!child)return {owned:false,confirmed:true};
  const exited=()=>child.exitCode!==null||child.signalCode!==null;
  if(exited())return {owned:true,pid:child.pid,confirmed:true,already_exited:true};
  async function wait(ms){
    if(exited())return true;
    let timer,listener;
    try{return await new Promise(resolve=>{listener=()=>resolve(true);child.once('exit',listener);timer=setTimeout(()=>resolve(exited()),ms);if(exited())resolve(true);});}
    finally{clearTimeout(timer);child.off('exit',listener);}
  }
  child.kill('SIGTERM');
  if(await wait(graceMs))return {owned:true,pid:child.pid,confirmed:true,signal:'SIGTERM'};
  child.kill('SIGKILL');
  const confirmed=await wait(killMs);
  return {owned:true,pid:child.pid,confirmed,signal:'SIGKILL',deadline_exceeded:!confirmed};
}
