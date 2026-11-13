import { canonical, sha256, type CodingTask } from './runner-contract';

/** The operator-authenticated enqueue is the authority to create this exact agenda
 * task. Insert+claim in one D1 batch prevents the older generic scheduler taking it. */
export async function claimScheduledAgenda(db:D1Database, task:CodingTask, hash:string, ownerId:string) {
  const payload=canonical({codingInputSha256:hash,codingAuthorization:'operator-scheduler-v1'});
  const result=await db.batch([
    db.prepare(`INSERT OR IGNORE INTO intelligence_tasks
      (task_id,title,domain,specialty,horizon,payload,status,claimed_by,claimed_at)
      VALUES (?1,?2,'coding','coding','now',?3,'claimed',?4,datetime('now'))`)
      .bind(task.taskId,`Cloud coding: ${task.repository.owner}/${task.repository.name} at ${task.repository.commit.slice(0,12)}`,payload,ownerId),
    db.prepare(`UPDATE intelligence_tasks SET status='claimed',claimed_by=?3,claimed_at=datetime('now'),updated_at=datetime('now')
      WHERE task_id=?1 AND domain='coding' AND json_extract(payload,'$.codingInputSha256')=?2
      AND status='queued' AND claimed_by IS NULL AND NOT EXISTS(SELECT 1 FROM coding_attempts WHERE task_id=?1)`)
      .bind(task.taskId,hash,ownerId),
  ]);
  if(result.some(r=>!r.success))throw Error('Agenda claim acknowledgement unavailable');
  const row=await db.prepare(`SELECT task_id,status,claimed_by,payload FROM intelligence_tasks WHERE task_id=?1 AND domain='coding' AND NOT EXISTS(SELECT 1 FROM coding_attempts WHERE task_id=?1)`).bind(task.taskId).first<{task_id:string;status:string;claimed_by:string;payload:string}>();
  if(!row||row.status!=='claimed'||row.claimed_by!==ownerId||JSON.parse(row.payload).codingInputSha256!==hash)return {authorized:false as const};
  return {authorized:true as const,receiptSha256:await sha256(canonical({schema:'lupine.coding-agenda-claim.v1',taskId:task.taskId,attemptId:task.attemptId,inputSha256:hash,ownerId,status:'claimed'}))};
}

