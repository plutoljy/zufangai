export type AnalysisAgent = 'owl' | 'dog' | 'beaver' | 'cat';

type CheckpointPhase = 'started' | 'completed';

type LiveActionEvent = {
  type: string;
  agent?: string;
  message?: string;
  elapsed_ms?: number;
};

const CHECKPOINTS: Record<CheckpointPhase, Record<AnalysisAgent, number>> = {
  started: {
    owl: 18,
    dog: 42,
    beaver: 65,
    cat: 82,
  },
  completed: {
    owl: 30,
    dog: 58,
    beaver: 78,
    cat: 94,
  },
};

const AGENT_LABELS: Record<AnalysisAgent, string> = {
  owl: '猫头鹰分析师',
  dog: '猎犬检索师',
  beaver: '海狸计算师',
  cat: '橘猫报告师',
};

export function getAgentCheckpoint(
  agent: string,
  phase: CheckpointPhase
): number {
  return CHECKPOINTS[phase][agent as AnalysisAgent] ?? 0;
}

export function getLiveActionText(event: LiveActionEvent): string {
  if (event.type === 'analysis_started') {
    return '正在准备分析任务...';
  }

  if (event.type === 'progress' || event.type === 'agent_progress' || event.type === 'heartbeat') {
    return event.message ?? '分析进行中...';
  }

  if (event.type === 'agent_completed' && event.agent && isAnalysisAgent(event.agent)) {
    return `${AGENT_LABELS[event.agent]}已完成`;
  }

  return event.message ?? '分析进行中...';
}

function isAnalysisAgent(value: string): value is AnalysisAgent {
  return value === 'owl' || value === 'dog' || value === 'beaver' || value === 'cat';
}
