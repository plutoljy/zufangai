/**
 * 租房避坑局 - API 类型定义
 */

// ============ 上传相关 ============

export interface UploadResponse {
  contract_id: string;
  status: string;
}

// ============ SSE 事件类型 ============

export type SSEEventType =
  | 'analysis_started'
  | 'owl_complete'
  | 'dog_complete'
  | 'beaver_complete'
  | 'cat_complete'
  | 'analysis_complete'
  | 'error';

export interface BaseSSEEvent {
  type: SSEEventType;
}

export interface AnalysisStartedEvent extends BaseSSEEvent {
  type: 'analysis_started';
}

export interface OwlCompleteEvent extends BaseSSEEvent {
  type: 'owl_complete';
  data: {
    entities: Record<string, any>;
    risk_count: number;
  };
}

export interface DogCompleteEvent extends BaseSSEEvent {
  type: 'dog_complete';
  data: {
    legal_docs: number;
    cases: number;
  };
}

export interface BeaverCompleteEvent extends BaseSSEEvent {
  type: 'beaver_complete';
  data: {
    compliant: boolean;
  };
}

export interface CatCompleteEvent extends BaseSSEEvent {
  type: 'cat_complete';
  data: {
    overall_risk: string;
    key_issues: string[];
    recommendations: string[];
  };
}

export interface AnalysisCompleteEvent extends BaseSSEEvent {
  type: 'analysis_complete';
  contract_id: string;
}

export interface ErrorEvent extends BaseSSEEvent {
  type: 'error';
  message: string;
}

export type SSEEvent =
  | AnalysisStartedEvent
  | OwlCompleteEvent
  | DogCompleteEvent
  | BeaverCompleteEvent
  | CatCompleteEvent
  | AnalysisCompleteEvent
  | ErrorEvent;

// ============ 报告相关 ============

export interface RiskItem {
  category: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  suggestion: string;
}

export interface LegalReference {
  law_name: string;
  article: string;
  content: string;
  relevance: string;
}

export interface CaseReference {
  case_name: string;
  court: string;
  year: string;
  summary: string;
  relevance: string;
}

export interface DepositCheck {
  compliant: boolean;
  deposit_amount: number;
  monthly_rent: number;
  ratio: number;
  issue?: string;
}

export interface Calculations {
  deposit_check: DepositCheck;
  total_cost: number;
  monthly_breakdown: Record<string, number>;
}

export interface ReportSummary {
  overall_risk: string;
  key_issues: string[];
  recommendations: string[];
}

export interface AnalysisReport {
  contract_id: string;
  entities: Record<string, any>;
  risk_items: RiskItem[];
  legal_references: LegalReference[];
  calculations: Calculations;
  report_markdown: string;
  summary: ReportSummary;
}

// ============ API 错误 ============

export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}
