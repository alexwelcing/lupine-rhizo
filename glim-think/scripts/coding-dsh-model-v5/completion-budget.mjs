// Local policy is additional to the immutable broker's shared sixteen-call cap.
// A known local role refusal never creates an ordinal or changes provider history.
import assert from 'node:assert/strict';

export const COMPLETION_BUDGET = Object.freeze({ total:16, master:6, worker:10, masterBeforeReady:3, explorationThrough:8 });
export function createBudgetStopMonitor(now=Date.now) {
  let idleSince=null;
  return ({blocked,queued,allIdle})=>{
    if(!blocked||queued||!allIdle){idleSince=null;return false}
    idleSince??=now();return now()-idleSince>=1000;
  };
}
export function createCompletionBudget({ isReady=()=>false, now=Date.now, deadlineAtMs }) {
  const roles=new Map(), used={master:0,worker:0}, pending={master:0,worker:0};
  const blocked=[]; let count=0;
  const role=id=>{assert(roles.has(id),'Unregistered coding session');return roles.get(id)};
  const feedback=id=>{
    const r=role(id), ready=isReady();
    return {schema:'lupine.coding-budget.v1',role:r,counterMeaning:'nonrefunded local turn reservations; actual dispatch is recorded separately',used:count,remaining:16-count,
      roleUsed:used[r],roleRemaining:COMPLETION_BUDGET[r]-used[r],queued:pending.master+pending.worker,
      explorationAllowed:count<=8,phase:count<=8?'explore':'finalize',
      masterReserved:6-used.master,workerReady:ready,deadlineRemainingMs:Math.max(0,deadlineAtMs-now()),
      instruction:count<=8?'Batch bounded source reads. Write the concise assessment by global turn 9, then report ready only if complete.':
        r==='worker'?'Exploration is closed. Use assessment_write, then orchestrator_report; report blocked if coverage is insufficient.':
        'Read the stored report and close the genuine ready result. Do not reopen exploration.'};
  };
  function refusal(id,code) {
    const value={sessionId:id,code,admittedRequests:count,automaticReplay:false};
    if(!blocked.some(x=>x.sessionId===id&&x.code===code))blocked.push(value);
    return Object.assign(new Error(code),{code,codingLocalBudgetRefusal:true});
  }
  return {
    register(id,r){assert(['master','worker'].includes(r));assert(!roles.has(id));assert(![...roles.values()].includes(r),'Only one session per trusted role');roles.set(id,r)},
    // Called synchronously before transport queues. Reservation is never refunded;
    // unknown/cancelled work must not become an implicit retry allocation.
    reserve(id){
      const r=role(id);
      if(now()>=deadlineAtMs)throw refusal(id,'CODING_ORIGINAL_DEADLINE');
      if(used[r]>=COMPLETION_BUDGET[r])throw refusal(id,'CODING_ROLE_BUDGET_EXHAUSTED');
      if(r==='master'&&!isReady()&&used.master>=3)throw refusal(id,'CODING_MASTER_FINALIZATION_RESERVED');
      if(count>=16)throw refusal(id,'CODING_GLOBAL_BUDGET_EXHAUSTED');
      used[r]++;pending[r]++;count++;let finished=false;
      return {started(){assert(!finished);finished=true;pending[r]--}};
    },
    feedback,
    guard(id,name,args,artifactsReady){
      const r=role(id);
      if(now()>=deadlineAtMs)return 'Original coding task deadline reached';
      if(name==='orchestrator_report'&&args?.state==='ready'&&!artifactsReady())
        return 'A ready report requires both validated assessment artifacts with complete source coverage; use assessment_write or report blocked.';
      // The definitions remain fixed. Only execution admission changes.
      if(count>8 && (r==='worker'?!['assessment_write','orchestrator_report'].includes(name):!['orchestrator_read','orchestrator_reply'].includes(name)))
        return 'Exploration is closed. '+JSON.stringify(feedback(id));
      return undefined;
    },
    snapshot(){return {policy:COMPLETION_BUDGET,counterMeaning:'nonrefunded local turn reservations, not provider invocations',used:count,perRole:{...used},pending:{...pending},blocked:structuredClone(blocked)}}
  };
}
