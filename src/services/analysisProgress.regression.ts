import assert from 'node:assert/strict';

import { getAgentCheckpoint, getLiveActionText } from './analysisProgress.ts';

function testAgentCheckpointsMatchConfiguredStages() {
  assert.equal(getAgentCheckpoint('owl', 'started'), 18);
  assert.equal(getAgentCheckpoint('beaver', 'completed'), 78);
  assert.equal(getAgentCheckpoint('cat', 'completed'), 94);
}

function testProgressMessagesDoNotAppendElapsedSeconds() {
  const actionText = getLiveActionText({
    type: 'agent_progress',
    agent: 'beaver',
    message: '正在用模型复核费用结论...',
    elapsed_ms: 18500,
  });

  assert.equal(actionText, '正在用模型复核费用结论...');
}

testAgentCheckpointsMatchConfiguredStages();
testProgressMessagesDoNotAppendElapsedSeconds();
