/**
 * Frontend API client for contract upload and analysis.
 */

import { createAnalysisTimeoutManager } from './analysisTimeouts.ts';
import { buildAuthenticatedHeaders } from './authHeaders.ts';
import { resolveApiBaseUrl } from './apiConfig.ts';
import { normalizeApiError } from './apiError.ts';
import { buildApiUrl } from './apiUrl.ts';

const API_BASE_URL = resolveApiBaseUrl();

function createManagedEventSource(
  url: string,
  onEvent: (event: AnalysisEvent) => void,
  onError: (error: Error) => void,
  options: {
    idleTimeoutMs?: number;
    hardTimeoutMs?: number | null;
  } = {}
): EventSource {
  const idleTimeoutMs = options.idleTimeoutMs ?? 600000;
  const hardTimeoutMs = options.hardTimeoutMs ?? null;
  let completed = false;
  let disconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const eventSource = new EventSource(url);
  const timeoutManager = createAnalysisTimeoutManager({
    idleTimeoutMs,
    hardTimeoutMs,
    onIdleTimeout: () => {
      eventSource.close();
      onError(new Error('分析连接长时间没有新进展，请重试'));
    },
    onHardTimeout: () => {
      eventSource.close();
      onError(new Error('分析总耗时超出上限，请重试'));
    },
  });

  const clearDisconnectTimer = () => {
    if (disconnectTimer) {
      clearTimeout(disconnectTimer);
      disconnectTimer = null;
    }
  };

  eventSource.onmessage = (event) => {
    try {
      clearDisconnectTimer();
      timeoutManager.touch();
      const data = JSON.parse(event.data);

      if (data.type === 'analysis_complete') {
        completed = true;
        timeoutManager.complete();
      }

      onEvent(data);
    } catch {
      timeoutManager.dispose();
      onError(new Error('解析分析事件失败'));
    }
  };

  eventSource.onerror = (error) => {
    clearDisconnectTimer();
    console.error('SSE connection error:', error);

    if (completed) {
      timeoutManager.dispose();
      eventSource.close();
      return;
    }

    disconnectTimer = setTimeout(() => {
      timeoutManager.dispose();
      eventSource.close();
      onError(new Error('分析连接断开，请重试'));
    }, 15000);
  };

  return eventSource;
}

export async function uploadContract(
  file: File,
  location?: string,
  options: {
    privacyRedaction?: boolean;
    burnAfterReading?: boolean;
  } = {}
): Promise<string> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (location) {
      formData.append('location', location);
    }
    if (options.privacyRedaction) {
      formData.append('privacy_mode', 'true');
    }
    if (options.burnAfterReading) {
      formData.append('burn_after_reading', 'true');
    }

    const response = await fetch(buildApiUrl(API_BASE_URL, '/contracts/upload'), {
      method: 'POST',
      body: formData,
      headers: await buildAuthenticatedHeaders(),
    });

    if (!response.ok) {
      let errorMessage = '上传失败';
      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    return data.contract_id;
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export function analyzeContract(
  contractId: string,
  onEvent: (event: AnalysisEvent) => void,
  onError: (error: Error) => void,
  options: {
    idleTimeoutMs?: number;
    hardTimeoutMs?: number | null;
  } = {}
): EventSource {
  return createManagedEventSource(
    buildApiUrl(API_BASE_URL, `/contracts/${contractId}/analyze`),
    onEvent,
    onError,
    options
  );
}

export async function queueAnalysisTask(contractId: string): Promise<AnalysisTask> {
  try {
    const response = await fetch(
      buildApiUrl(API_BASE_URL, `/contracts/${contractId}/analyze/queue`),
      {
        method: 'POST',
        headers: await buildAuthenticatedHeaders(),
      }
    );

    if (!response.ok) {
      let errorMessage = '创建分析任务失败';
      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export function streamAnalysisTask(
  taskId: string,
  streamToken: string | undefined,
  onEvent: (event: AnalysisEvent) => void,
  onError: (error: Error) => void,
  options: {
    idleTimeoutMs?: number;
    hardTimeoutMs?: number | null;
  } = {}
): EventSource {
  const streamUrl = new URL(
    buildApiUrl(API_BASE_URL, `/analysis/tasks/${taskId}/stream`),
    window.location.origin
  );
  if (streamToken) {
    streamUrl.searchParams.set('stream_token', streamToken);
  }

  return createManagedEventSource(
    streamUrl.toString(),
    onEvent,
    onError,
    options
  );
}

export async function getAnalysisTask(taskId: string): Promise<AnalysisTask> {
  try {
    const response = await fetch(
      buildApiUrl(API_BASE_URL, `/analysis/tasks/${taskId}`),
      {
        headers: await buildAuthenticatedHeaders(),
      }
    );
    if (!response.ok) {
      throw new Error('获取分析任务状态失败');
    }
    return await response.json();
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function getReport(contractId: string): Promise<AnalysisReport> {
  try {
    const response = await fetch(
      buildApiUrl(API_BASE_URL, `/contracts/${contractId}/report`),
      {
        headers: await buildAuthenticatedHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('获取报告失败');
    }

    return await response.json();
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function getContractHistory(): Promise<ContractHistoryItem[]> {
  try {
    const response = await fetch(buildApiUrl(API_BASE_URL, '/contracts/history'), {
      headers: await buildAuthenticatedHeaders(),
    });

    if (!response.ok) {
      throw new Error('获取审查历史失败');
    }

    const data = await response.json();
    return data.contracts ?? [];
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function chatWithAgent(
  contractId: string,
  agent: 'owl' | 'dog' | 'beaver',
  payload: AgentChatRequest
): Promise<AgentChatResponse> {
  try {
    const response = await fetch(
      buildApiUrl(API_BASE_URL, `/contracts/${contractId}/agents/${agent}/chat`),
      {
        method: 'POST',
        headers: await buildAuthenticatedHeaders({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      let errorMessage = '发送追问失败';
      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function cleanupBurnAfterReading(
  contractId?: string
): Promise<{ deleted_contract_ids: string[]; scheduled_contract_ids: string[] }> {
  try {
    const response = await fetch(
      buildApiUrl(API_BASE_URL, '/contracts/burn-after-reading/cleanup'),
      {
        method: 'POST',
        headers: await buildAuthenticatedHeaders({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({ contract_id: contractId ?? null }),
      }
    );

    if (!response.ok) {
      let errorMessage = '清理阅后即焚合同失败';
      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export interface AnalysisEvent {
  type:
    | 'analysis_started'
    | 'owl_analysis'
    | 'dog_retrieval'
    | 'beaver_calculation'
    | 'cat_report'
    | 'progress'
    | 'heartbeat'
    | 'agent_started'
    | 'agent_progress'
    | 'agent_completed'
    | 'agent_failed'
    | 'report_paragraph'
    | 'template_detected'
    | 'analysis_complete'
    | 'error';
  data?: any;
  message?: string;
  agent?: string;
  step?: string;
  elapsed_ms?: number;
  error_code?: string;
  index?: number;
  total?: number;
  paragraph?: string;
  reason?: string | null;
  contract_id?: string;
}

export interface AnalysisTask {
  task_id: string;
  contract_id: string;
  status: string;
  queue_position?: number;
  stream_token?: string;
  error?: string;
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

export interface AgentChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AgentChatRequest {
  question: string;
  messages: AgentChatMessage[];
}

export interface AgentChatResponse {
  contract_id: string;
  agent: string;
  reply: string;
}

export interface AnalysisReport {
  contract_id: string;
  contract_text?: string;
  entities: ContractEntities;
  risk_items: RiskItem[];
  legal_references: LegalReference[];
  case_references: CaseReference[];
  suggestions: SuggestionItem[];  // 使用 SuggestionItem 类型
  negotiation_tips: NegotiationTip[];
  calculations: Calculations;
  report_markdown: string;
  summary: ReportSummary;
  is_template?: boolean;
  privacy_redacted?: boolean;
  redaction_count?: number;
}

export interface ContractEntities {
  lessor: string | null;
  lessee: string | null;
  monthly_rent: number | null;
  deposit: number | null;
  lease_term: string | null;
  property_address: string | null;
  start_date: string | null;
  end_date: string | null;
  utilities?: {
    water?: number;
    electricity?: number;
    gas?: number;
  };
}

export interface RiskItem {
  clause: string;
  risk_level: 'high' | 'medium' | 'low';
  issue: string;
  legal_basis: string;
  suggestion: string;
}

export interface LegalReference {
  law_id: string;
  title: string;
  content: string;
  relevance: string;
  application: string;
}

export interface CaseReference {
  case_id: string;
  title: string;
  summary?: string;  // 可选
  content?: string;  // 兼容后端返回的 content 字段
  relevance: string;
}

export interface Suggestion {
  category?: string;
  content?: string;
  priority?: 'high' | 'medium' | 'low';
}

// 兼容字符串格式
export type SuggestionItem = Suggestion | string;

export interface NegotiationTip {
  issue: string;        // 问题/场景
  strategy: string;     // 策略/技巧
  script?: string;      // 话术示例
  // 兼容旧字段
  scenario?: string;
  tip?: string;
  example?: string;
}

export interface HiddenCost {
  description: string;
  amount: number | null;
  risk_level: 'high' | 'medium' | 'low';
  inference?: string;
  location?: {
    page: number;
    paragraph: string;
    quote: string;
    confidence: string;
  };
}

export interface AmbiguousClauses {
  count: number;
  items: Array<{
    clause: string;
    issue: string;
    inference?: string;
    location?: {
      page: number;
      paragraph: string;
      quote: string;
      confidence: string;
    };
  }>;
}

export interface ExplicitValues {
  monthly_rent: number;
  deposit: number;
  payment_method: string;
  water_price: number;
  electricity_price: number;
  gas_price: number;
  lease_term: string;
}

export interface ImplicitValues {
  first_payment?: {
    amount: number;
    calculation: string;
    source: string;
    confidence: 'high' | 'medium' | 'low';
  };
  penalty_scenarios?: Array<{
    timing: string;
    loss_amount: number;
    calculation: string;
    source: string;
    confidence: 'high' | 'medium' | 'low';
  }>;
  hidden_fee_risks?: Array<{
    description: string;
    estimated_amount: number;
    source: string;
    confidence: 'high' | 'medium' | 'low';
  }>;
}

export interface Calculations {
  deposit_check: {
    amount: number;
    legal_limit: number;
    compliant: boolean;
    overcharge_amount: number;
    issue: string | null;
    suggestion: string | null;
  };
  utilities_check: {
    water: UtilityCheck;
    electricity: UtilityCheck;
    gas: UtilityCheck;
  };
  hidden_costs: HiddenCost[];
  ambiguous_clauses: AmbiguousClauses;
  explicit_values: ExplicitValues;
  implicit_values: ImplicitValues;
  total_cost_analysis: {
    monthly_base: number;
    estimated_utilities: number;
    monthly_total: number;
    yearly_total: number;
    market_comparison: string;
  };
}

export interface ReportSummary {
  total_risks: number;
  high_risks: number;
  medium_risks: number;
  low_risks: number;
  compliant: boolean;
}

export interface UtilityCheck {
  charged: number;
  official: number;
  overcharge_rate: number;
  overcharged: boolean;
  issue: string | null;
  suggestion: string | null;
}
