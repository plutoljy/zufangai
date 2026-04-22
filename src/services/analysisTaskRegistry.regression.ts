import assert from 'node:assert/strict';

import {
  clearQueuedTaskRegistry,
  getOrCreateQueuedTask,
} from './analysisTaskRegistry.ts';

async function main() {
  clearQueuedTaskRegistry();

  let callCount = 0;
  const createTask = async () => {
    callCount += 1;
    return {
      task_id: 'task-1',
      contract_id: 'contract-1',
      status: 'pending',
    };
  };

  const first = getOrCreateQueuedTask('contract-1', createTask);
  const second = getOrCreateQueuedTask('contract-1', createTask);

  assert.strictEqual(first, second);

  const task = await second;
  assert.equal(task.task_id, 'task-1');
  assert.equal(callCount, 1);

  clearQueuedTaskRegistry();
}

main();
