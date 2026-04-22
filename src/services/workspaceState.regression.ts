import assert from 'node:assert/strict';

import {
  appendAgentMessage,
  getAgentMessages,
  sortHistoryEntries,
  type ContractHistoryItem,
  type WorkspaceChatThreads,
} from './workspaceState.ts';

function testAgentThreadsStayScopedByContractAndAgent() {
  let threads: WorkspaceChatThreads = {};

  threads = appendAgentMessage(threads, 'contract-1', 'owl', {
    role: 'user',
    content: '第一句',
  });
  threads = appendAgentMessage(threads, 'contract-1', 'beaver', {
    role: 'assistant',
    content: '第二句',
  });
  threads = appendAgentMessage(threads, 'contract-2', 'owl', {
    role: 'user',
    content: '第三句',
  });

  assert.equal(getAgentMessages(threads, 'contract-1', 'owl').length, 1);
  assert.equal(getAgentMessages(threads, 'contract-1', 'beaver').length, 1);
  assert.equal(getAgentMessages(threads, 'contract-2', 'owl').length, 1);
  assert.equal(getAgentMessages(threads, 'missing', 'owl').length, 0);
}

function testHistoryEntriesSortByCompletionThenCreationTime() {
  const entries: ContractHistoryItem[] = [
    {
      contract_id: 'contract-1',
      filename: 'older.docx',
      location: 'beijing',
      status: 'completed',
      created_at: 100,
      completed_at: 120,
      last_accessed_at: 120,
      burn_after_reading: false,
      risk_summary: { high: 0, medium: 1, low: 0, total: 1 },
    },
    {
      contract_id: 'contract-2',
      filename: 'latest.docx',
      location: 'shanghai',
      status: 'completed',
      created_at: 200,
      completed_at: 260,
      last_accessed_at: 260,
      burn_after_reading: true,
      risk_summary: { high: 1, medium: 0, low: 0, total: 1 },
    },
  ];

  const sorted = sortHistoryEntries(entries);
  assert.equal(sorted[0].contract_id, 'contract-2');
  assert.equal(sorted[1].contract_id, 'contract-1');
}

testAgentThreadsStayScopedByContractAndAgent();
testHistoryEntriesSortByCompletionThenCreationTime();
