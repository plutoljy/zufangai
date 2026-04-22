export type WorkspaceAgentKey = 'owl' | 'dog' | 'beaver';

export interface AgentChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ContractHistoryItem {
  contract_id: string;
  filename: string;
  location: string | null;
  status: string;
  created_at?: number | null;
  completed_at?: number | null;
  last_accessed_at?: number | null;
  burn_after_reading: boolean;
  risk_summary: {
    high: number;
    medium: number;
    low: number;
    total: number;
  };
}

export type WorkspaceChatThreads = Record<
  string,
  Partial<Record<WorkspaceAgentKey, AgentChatMessage[]>>
>;

export function getAgentMessages(
  threads: WorkspaceChatThreads,
  contractId: string,
  agent: WorkspaceAgentKey
): AgentChatMessage[] {
  return threads[contractId]?.[agent] ?? [];
}

export function appendAgentMessage(
  threads: WorkspaceChatThreads,
  contractId: string,
  agent: WorkspaceAgentKey,
  message: AgentChatMessage
): WorkspaceChatThreads {
  const currentMessages = getAgentMessages(threads, contractId, agent);
  return {
    ...threads,
    [contractId]: {
      ...(threads[contractId] ?? {}),
      [agent]: [...currentMessages, message],
    },
  };
}

export function sortHistoryEntries(
  entries: ContractHistoryItem[]
): ContractHistoryItem[] {
  return [...entries].sort((left, right) => {
    const rightTime = right.completed_at ?? right.created_at ?? 0;
    const leftTime = left.completed_at ?? left.created_at ?? 0;
    return rightTime - leftTime;
  });
}
