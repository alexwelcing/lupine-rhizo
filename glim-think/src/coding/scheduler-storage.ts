import { CodingScheduler, type CodingSchedulerDependencies, type CodingSchedulerStore } from './scheduler-state';

/** Uses the DO's real storage transaction and alarm, without starting work at construction. */
export function codingSchedulerStorage(storage:DurableObjectStorage):CodingSchedulerStore {
  const wrap=(value:DurableObjectStorage|DurableObjectTransaction,transaction:(fn:(tx:CodingSchedulerStore)=>Promise<unknown>)=>Promise<unknown>):CodingSchedulerStore=>({
    get:<T>(key:string)=>value.get<T>(key),
    put:async<T>(key:string,item:T)=>{await value.put(key,item);},
    setAlarm:async(at:number)=>{await value.setAlarm(at);},
    deleteAlarm:async()=>{await value.deleteAlarm();},
    transaction:<T>(fn:(tx:CodingSchedulerStore)=>Promise<T>)=>transaction(fn) as Promise<T>,
  });
  return wrap(storage,fn=>storage.transaction(async tx=>{
    let adapter:CodingSchedulerStore;adapter=wrap(tx,nested=>nested(adapter));return fn(adapter);
  }));
}
export function createDurableCodingScheduler(storage:DurableObjectStorage,deps:CodingSchedulerDependencies){
  return new CodingScheduler(codingSchedulerStorage(storage),deps);
}
