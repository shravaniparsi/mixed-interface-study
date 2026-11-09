export class PhaseClock {
  constructor(now=()=>performance.now()/1000){this.now=now;this.origin=now();this.at=this.origin;this.phase='adapter_initialization';this.spans=[];this.closed=false;}
  switch(phase){if(this.closed)throw new Error('Closed clock');const end=this.now();if(!Number.isFinite(end)||end<this.at)throw new Error('Non-monotonic clock');this.spans.push({phase:this.phase,start_s:this.at-this.origin,end_s:end-this.origin});this.at=end;this.phase=phase;}
  async during(phase,work){const previous=this.phase;this.switch(phase);try{return await work();}finally{this.switch(previous);}}
  finish(){this.switch('finished');this.closed=true;const totals={};for(const s of this.spans)totals[s.phase]=(totals[s.phase]??0)+s.end_s-s.start_s;return {clock:'process_local_performance_monotonic_seconds',scope:'Exclusive adapter spans; process startup and final serialization remain in parent adapter_process interval.',total_s:this.at-this.origin,spans:this.spans,totals_s:totals};}
}
