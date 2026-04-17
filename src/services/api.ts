/**
 * 租房合同分析系统 - 前端API客户端
 * 负责与后端FastAPI服务通信
 */

const API_BASE_URL = 'http://localhost:8000/api';

/**
 * 上传合同文件
 * @param file 合同文件（PDF/Word/Image）
 * @param location 城市位置（用于水电费查询）
 * @returns contract_id 合同ID
 */
export async function uploadContract(
  file: File,
  location: string
): Promise<string> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('location', location);

    const response = await fetch(`${API_BASE_URL}/contracts/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '上传失败');
    }

    const data = await response.json();
    return data.contract_id;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('上传合同时发生未知错误');
  }
}

/**
 * 分析合同（SSE流式接收）
 * @param contractId 合同ID
 * @param onEvent 事件回调函数
 * @param onError 错误回调函数
 * @param timeout 超时时间（毫秒），默认60秒
 * @returns EventSource 实例（可用于关闭连接）
 */
export function analyzeContract(
  contractId: string,
  onEvent: (event: AnalysisEvent) => void,
  onError: (error: Error) => void,
  timeout: number = 60000
): EventSource {
  const eventSource = new EventSource(
    `${API_BASE_URL}/contracts/${contractId}/analyze`
  );

  // 设置超时定时器
  const timeoutId = setTimeout(() => {
    eventSource.close();
    onError(new Error('分析超时，请重试'));
  }, timeout);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // 收到消息时清除超时定时器
      if (data.type === 'analysis_complete') {
        clearTimeout(timeoutId);
      }

      onEvent(data);
    } catch (error) {
      clearTimeout(timeoutId);
      onError(new Error('解析SSE事件失败'));
    }
  };

  eventSource.onerror = (error) => {
    clearTimeout(timeoutId);
    console.error('SSE连接错误:', error);
    onError(new Error('分析连接断开，请重试'));
    eventSource.close();
  };

  return eventSource;
}

/**
 * 获取完整分析报告
 * @param contractId 合同ID
 * @returns 分析报告数据
 */
export async function getReport(contractId: string): Promise<AnalysisReport> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/contracts/${contractId}/report`
    );

    if (!response.ok) {
      throw new Error('获取报告失败');
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('获取报告时发生未知错误');
  }
}

// ========== TypeScript 类型定义 ==========

/**
 * SSE分析事件
 */
export interface AnalysisEvent {
  type: 'owl_analysis' | 'dog_retrieval' | 'beaver_calculation' | 'cat_report' | 'analysis_complete' | 'error';
  data?: any;
  message?: string;
}

/**
 * 分析报告
 */
export interface AnalysisReport {
  contract_id: string;
  entities: ContractEntities;
  risk_items: RiskItem[];
  legal_references: LegalReference[];
  calculations: Calculations;
  report_markdown: string;
  summary: string;
}

/**
 * 合同实体信息
 */
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

/**
 * 风险条款
 */
export interface RiskItem {
  clause: string;
  risk_level: 'high' | 'medium' | 'low';
  issue: string;
  legal_basis: string;
  suggestion: string;
}

/**
 * 法律依据
 */
export interface LegalReference {
  law_id: string;
  title: string;
  content: string;
  relevance: string;
  application: string;
}

/**
 * 费用计算结果
 */
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
  total_cost_analysis: {
    monthly_base: number;
    estimated_utilities: number;
    monthly_total: number;
    yearly_total: number;
    market_comparison: string;
  };
}

/**
 * 水电费检查
 */
export interface UtilityCheck {
  charged: number;
  official: number;
  overcharge_rate: number;
  overcharged: boolean;
  issue: string | null;
  suggestion: string | null;
}
