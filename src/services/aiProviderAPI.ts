import { buildAuthenticatedHeaders } from './authHeaders';
import { resolveApiBaseUrl } from './apiConfig';
import { buildApiUrl } from './apiUrl';

const API_BASE_URL = resolveApiBaseUrl();

export type ProviderName = 'openai' | 'claude' | 'qwen' | 'custom';
export type AgentName = 'owl' | 'dog' | 'beaver' | 'cat';
export type APIProtocol = 'openai' | 'anthropic' | 'qwen' | 'request';

export interface AIProviderPublic {
  provider_name: ProviderName;
  base_url?: string | null;
  model_name: string;
  is_active: boolean;
  has_api_key: boolean;
  api_key_masked?: string | null;
}

export interface AIProviderSavePayload {
  provider_name: ProviderName;
  api_key?: string | null;
  base_url?: string | null;
  model_name: string;
  is_active?: boolean;
}

export interface AgentModelConfig {
  agent_name: AgentName;
  provider_name: ProviderName;
  api_protocol?: APIProtocol | null;
  api_key?: string | null;
  base_url?: string | null;
  model_name: string;
  has_api_key?: boolean;
  api_key_masked?: string | null;
}

export interface AgentConnectionDiagnostic {
  agent_name: AgentName;
  provider_name?: ProviderName | null;
  api_protocol?: APIProtocol | null;
  base_url?: string | null;
  model_name?: string | null;
  endpoint?: string | null;
  success: boolean;
  message: string;
}

export type AgentModelConfigPayload = Pick<
  AgentModelConfig,
  'agent_name' | 'provider_name' | 'api_protocol' | 'api_key' | 'base_url' | 'model_name'
>;

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      data && typeof data.detail === 'string'
        ? data.detail
        : `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return data as T;
}

export async function listAIProviders(): Promise<AIProviderPublic[]> {
  const response = await fetch(buildApiUrl(API_BASE_URL, '/ai-providers/providers'), {
    headers: await buildAuthenticatedHeaders(),
  });
  return parseResponse<AIProviderPublic[]>(response);
}

export async function saveAIProvider(
  payload: AIProviderSavePayload
): Promise<AIProviderPublic> {
  const response = await fetch(buildApiUrl(API_BASE_URL, '/ai-providers/providers'), {
    method: 'POST',
    headers: await buildAuthenticatedHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ ...payload, is_active: payload.is_active ?? true }),
  });
  return parseResponse<AIProviderPublic>(response);
}

export async function updateAIProvider(
  providerName: ProviderName,
  payload: Omit<AIProviderSavePayload, 'provider_name'>
): Promise<AIProviderPublic> {
  const response = await fetch(
    buildApiUrl(API_BASE_URL, `/ai-providers/providers/${providerName}`),
    {
      method: 'PUT',
      headers: await buildAuthenticatedHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ ...payload, is_active: payload.is_active ?? true }),
    }
  );
  return parseResponse<AIProviderPublic>(response);
}

export async function deleteAIProvider(providerName: ProviderName): Promise<void> {
  const response = await fetch(
    buildApiUrl(API_BASE_URL, `/ai-providers/providers/${providerName}`),
    {
      method: 'DELETE',
      headers: await buildAuthenticatedHeaders(),
    }
  );
  await parseResponse(response);
}

export async function getAgentModelConfigs(): Promise<
  Record<string, AgentModelConfig>
> {
  const response = await fetch(
    buildApiUrl(API_BASE_URL, '/ai-providers/agents/config'),
    {
      headers: await buildAuthenticatedHeaders(),
    }
  );
  return parseResponse<Record<string, AgentModelConfig>>(response);
}

export async function saveAgentModelConfigs(
  configs: AgentModelConfigPayload[]
): Promise<AgentModelConfig[]> {
  const response = await fetch(
    buildApiUrl(API_BASE_URL, '/ai-providers/agents/config/batch'),
    {
      method: 'POST',
      headers: await buildAuthenticatedHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(configs),
    }
  );
  return parseResponse<AgentModelConfig[]>(response);
}

export async function diagnoseAgentConnections(): Promise<AgentConnectionDiagnostic[]> {
  const response = await fetch(
    buildApiUrl(API_BASE_URL, '/ai-providers/agents/diagnostics'),
    {
      method: 'POST',
      headers: await buildAuthenticatedHeaders(),
    }
  );
  return parseResponse<AgentConnectionDiagnostic[]>(response);
}
