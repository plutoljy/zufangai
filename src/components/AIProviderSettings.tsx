import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, CircleDashed, PlugZap, Save } from 'lucide-react';

import {
  diagnoseAgentConnections,
  getAgentModelConfigs,
  saveAgentModelConfigs,
  type AgentConnectionDiagnostic,
  type AgentModelConfig,
  type AgentModelConfigPayload,
  type AgentName,
  type APIProtocol,
  type ProviderName,
} from '../services/aiProviderAPI';

type AccessMode = 'openai' | 'anthropic' | 'custom';

const ACCESS_MODES: Array<{
  key: AccessMode;
  label: string;
  hint: string;
  defaultBaseUrl: string;
  defaultModel: string;
  protocol: APIProtocol;
}> = [
  {
    key: 'openai',
    label: 'OpenAI 兼容协议',
    hint: '适合官方 OpenAI，按 Chat Completions 格式调用。',
    defaultBaseUrl: 'https://api.openai.com/v1',
    defaultModel: 'gpt-4o',
    protocol: 'openai',
  },
  {
    key: 'anthropic',
    label: 'Anthropic 兼容协议',
    hint: '适合官方 Anthropic，按 /v1/messages 格式调用。',
    defaultBaseUrl: 'https://api.anthropic.com',
    defaultModel: 'claude-sonnet-4-6',
    protocol: 'anthropic',
  },
  {
    key: 'custom',
    label: '自定义中转 request',
    hint: 'Base URL 作为完整请求地址，后端直接用 requests.post 调用。',
    defaultBaseUrl: '',
    defaultModel: '',
    protocol: 'request',
  },
];

const AGENTS: Array<{ key: AgentName; label: string; job: string }> = [
  { key: 'owl', label: 'Owl', job: '条款和风险识别' },
  { key: 'dog', label: 'Dog', job: '法律依据整理' },
  { key: 'beaver', label: 'Beaver', job: '费用核算复核' },
  { key: 'cat', label: 'Cat', job: '最终报告生成' },
];

type AgentDraft = {
  accessMode: AccessMode;
  apiProtocol: APIProtocol;
  apiKey: string;
  baseUrl: string;
  modelName: string;
  hasApiKey: boolean;
  apiKeyMasked?: string | null;
};

function blankDraft(mode: AccessMode = 'openai'): AgentDraft {
  const meta = ACCESS_MODES.find((item) => item.key === mode) ?? ACCESS_MODES[0];
  return {
    accessMode: meta.key,
    apiProtocol: meta.protocol,
    apiKey: '',
    baseUrl: meta.defaultBaseUrl,
    modelName: meta.defaultModel,
    hasApiKey: false,
    apiKeyMasked: null,
  };
}

function accessModeToProviderName(mode: AccessMode): ProviderName {
  if (mode === 'anthropic') {
    return 'claude';
  }
  return mode;
}

function configToDraft(config?: AgentModelConfig): AgentDraft {
  if (!config) {
    return blankDraft();
  }
  const apiProtocol =
    config.provider_name === 'custom'
      ? 'request'
      : config.api_protocol ?? (config.provider_name === 'claude' ? 'anthropic' : 'openai');
  const accessMode: AccessMode =
    config.provider_name === 'custom'
      ? 'custom'
      : apiProtocol === 'request'
        ? 'custom'
        : apiProtocol === 'anthropic'
        ? 'anthropic'
        : 'openai';
  const fallback = blankDraft(accessMode);
  return {
    accessMode,
    apiProtocol,
    apiKey: '',
    baseUrl: config.base_url ?? fallback.baseUrl,
    modelName: config.model_name || fallback.modelName,
    hasApiKey: Boolean(config.has_api_key),
    apiKeyMasked: config.api_key_masked,
  };
}

function draftToPayload(agentName: AgentName, draft: AgentDraft): AgentModelConfigPayload {
  const apiKey = draft.apiKey.trim();
  const apiProtocol = draft.accessMode === 'custom' ? 'request' : draft.apiProtocol;
  return {
    agent_name: agentName,
    provider_name: accessModeToProviderName(draft.accessMode),
    api_protocol: apiProtocol,
    api_key: apiKey || null,
    base_url: draft.baseUrl.trim() || null,
    model_name: draft.modelName.trim(),
  };
}

export function AIProviderSettings() {
  const [mode, setMode] = useState<'batch' | 'individual'>('batch');
  const [selectedAgent, setSelectedAgent] = useState<AgentName>('owl');
  const [batchDraft, setBatchDraft] = useState<AgentDraft>(() => blankDraft());
  const [agentDrafts, setAgentDrafts] = useState<Record<AgentName, AgentDraft>>(
    () =>
      Object.fromEntries(
        AGENTS.map((agent) => [agent.key, blankDraft()])
      ) as Record<AgentName, AgentDraft>
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<AgentConnectionDiagnostic[]>([]);

  const selectedDraft = agentDrafts[selectedAgent];

  async function loadSettings() {
    setBusy(true);
    setMessage(null);
    try {
      const configs = await getAgentModelConfigs();
      setAgentDrafts(
        Object.fromEntries(
          AGENTS.map((agent) => [agent.key, configToDraft(configs[agent.key])])
        ) as Record<AgentName, AgentDraft>
      );
      const firstConfig = AGENTS.map((agent) => configs[agent.key]).find(Boolean);
      if (firstConfig) {
        setBatchDraft(configToDraft(firstConfig));
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '加载 AI 设置失败');
    } finally {
      setBusy(false);
    }
  }

  async function refreshDiagnostics() {
    const results = await diagnoseAgentConnections();
    setDiagnostics(results);
    return results;
  }

  useEffect(() => {
    void loadSettings();
  }, []);

  function applyAccessMode(nextMode: AccessMode) {
    const meta = ACCESS_MODES.find((item) => item.key === nextMode) ?? ACCESS_MODES[0];
    const apply = (draft: AgentDraft): AgentDraft => ({
      ...draft,
      accessMode: nextMode,
      apiProtocol: meta.protocol,
      apiKey: '',
      baseUrl: meta.defaultBaseUrl || draft.baseUrl,
      modelName: meta.defaultModel || draft.modelName,
      hasApiKey: false,
      apiKeyMasked: null,
    });

    if (mode === 'batch') {
      setBatchDraft((current) => apply(current));
      return;
    }
    setAgentDrafts((current) => ({
      ...current,
      [selectedAgent]: apply(current[selectedAgent]),
    }));
  }

  function updateActiveDraft(patch: Partial<AgentDraft>) {
    if (mode === 'batch') {
      setBatchDraft((current) => ({ ...current, ...patch }));
      return;
    }
    setAgentDrafts((current) => ({
      ...current,
      [selectedAgent]: { ...current[selectedAgent], ...patch },
    }));
  }

  async function handleConfirm() {
    const activeDraft = mode === 'batch' ? batchDraft : selectedDraft;
    if (!activeDraft.apiKey.trim() && !activeDraft.hasApiKey) {
      setMessage('请先填写 API Key');
      return;
    }
    if (!activeDraft.modelName.trim()) {
      setMessage('请先填写模型名');
      return;
    }
    if (!activeDraft.baseUrl.trim()) {
      setMessage('请先填写 Base URL');
      return;
    }

    const payloads =
      mode === 'batch'
        ? AGENTS.map((agent) => draftToPayload(agent.key, batchDraft))
        : [draftToPayload(selectedAgent, selectedDraft)];

    setBusy(true);
    setMessage(null);
    try {
      const saved = await saveAgentModelConfigs(payloads);
      setAgentDrafts((current) => {
        const next = { ...current };
        for (const config of saved) {
          next[config.agent_name] = configToDraft(config);
        }
        return next;
      });
      const results = await refreshDiagnostics();
      const failedAgents = results.filter((item) => !item.success);
      setMessage(
        failedAgents.length
          ? `AI 接入配置已保存，但 ${failedAgents.map((item) => item.agent_name).join('、')} 校验失败`
          : mode === 'batch'
            ? '四个 agent 的 AI 接入配置已保存，模型连通性校验通过'
            : `${AGENTS.find((agent) => agent.key === selectedAgent)?.label} 的 AI 接入配置已保存，模型连通性校验通过`
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '保存 AI 配置失败');
    } finally {
      setBusy(false);
    }
  }

  const activeDraft = mode === 'batch' ? batchDraft : selectedDraft;
  const activeAccessMode =
    ACCESS_MODES.find((item) => item.key === activeDraft.accessMode) ?? ACCESS_MODES[0];

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border-4 border-ink bg-surface p-4 shadow-[4px_4px_0px_var(--color-ink)]">
        <div className="mb-3 flex items-center gap-2 font-black text-ink">
          <PlugZap size={20} className="text-primary" />
          AI 服务厂商选择
        </div>
        <p className="mb-4 text-xs font-bold text-gray-custom">
          这里配置的是 LLM 调用协议和每个 agent 的接入信息。RAG embedding 继续由后端统一使用千问配置。
        </p>

        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex rounded-xl border-2 border-ink bg-paper p-1 text-xs font-black">
            <button
              type="button"
              onClick={() => setMode('batch')}
              className={`rounded-lg px-3 py-1 ${mode === 'batch' ? 'bg-primary' : ''}`}
            >
              一次配置
            </button>
            <button
              type="button"
              onClick={() => setMode('individual')}
              className={`rounded-lg px-3 py-1 ${mode === 'individual' ? 'bg-primary' : ''}`}
            >
              分别配置
            </button>
          </div>

          {mode === 'individual' && (
            <select
              value={selectedAgent}
              onChange={(event) => setSelectedAgent(event.target.value as AgentName)}
              className="min-w-[180px] rounded-xl border-2 border-ink bg-paper px-3 py-2 text-sm font-black outline-none"
            >
              {AGENTS.map((agent) => (
                <option key={agent.key} value={agent.key}>
                  {agent.label} - {agent.job}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="mb-4 rounded-xl border-2 border-ink bg-paper p-3">
          <label className="mb-2 flex items-center gap-2 text-xs font-black text-gray-custom">
            <PlugZap size={15} className="text-primary" />
            协议类型
          </label>
          <select
            value={activeDraft.accessMode}
            onChange={(event) => applyAccessMode(event.target.value as AccessMode)}
            className="w-full rounded-xl border-2 border-ink bg-surface px-3 py-3 text-sm font-black text-ink outline-none focus:ring-4 focus:ring-secondary/50"
          >
            {ACCESS_MODES.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs font-bold text-gray-custom">
            当前协议说明：{activeAccessMode.hint}
          </p>
        </div>

        <div className="rounded-xl border-2 border-ink bg-paper p-4">
          {mode === 'individual' && (
            <div className="mb-3 text-sm font-black text-ink">
              正在配置：{AGENTS.find((agent) => agent.key === selectedAgent)?.label}
              <span className="ml-2 text-xs text-gray-custom">
                {activeDraft.apiKeyMasked
                  ? `已保存密钥 ${activeDraft.apiKeyMasked}`
                  : '还没有保存密钥'}
              </span>
            </div>
          )}

          <div className="grid gap-3">
            <input
              type="password"
              value={activeDraft.apiKey}
              onChange={(event) => updateActiveDraft({ apiKey: event.target.value })}
              placeholder={activeDraft.hasApiKey ? '留空则沿用已保存密钥' : 'API Key'}
              className="w-full rounded-xl border-2 border-ink bg-surface p-3 text-sm font-bold outline-none focus:ring-4 focus:ring-secondary/50"
            />
            <input
              value={activeDraft.baseUrl}
              onChange={(event) => updateActiveDraft({ baseUrl: event.target.value })}
              placeholder="Base URL"
              className="w-full rounded-xl border-2 border-ink bg-surface p-3 text-sm font-bold outline-none focus:ring-4 focus:ring-secondary/50"
            />
            <input
              value={activeDraft.modelName}
              onChange={(event) => updateActiveDraft({ modelName: event.target.value })}
              placeholder={mode === 'batch' ? '四个 agent 使用的模型名' : '当前 agent 使用的模型名'}
              className="w-full rounded-xl border-2 border-ink bg-surface p-3 text-sm font-bold outline-none focus:ring-4 focus:ring-secondary/50"
            />
          </div>

          <button
            type="button"
            onClick={() => void handleConfirm()}
            disabled={busy}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-ink bg-secondary px-4 py-3 text-sm font-black text-ink shadow-[3px_3px_0px_var(--color-ink)] disabled:opacity-60"
          >
            <Save size={16} />
            {mode === 'batch' ? '确认四个 agent 配置' : '确认当前 agent 配置'}
          </button>
        </div>
      </div>

      {diagnostics.length > 0 && (
        <div className="rounded-2xl border-4 border-ink bg-paper p-4 shadow-[4px_4px_0px_var(--color-ink)]">
          <div className="mb-3 flex items-center gap-2 text-sm font-black text-ink">
            <CircleDashed size={18} className="text-primary" />
            Agent 模型加载状态
          </div>
          <div className="grid gap-2">
            {diagnostics.map((item) => {
              const agent = AGENTS.find((entry) => entry.key === item.agent_name);
              return (
                <div
                  key={item.agent_name}
                  className="rounded-xl border-2 border-ink bg-surface px-3 py-2 text-xs font-bold text-ink"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-black">
                      {agent?.label ?? item.agent_name} · {item.model_name ?? '未配置模型'}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-lg border-2 border-ink px-2 py-1 font-black ${
                        item.success ? 'bg-primary' : 'bg-secondary'
                      }`}
                    >
                      {item.success ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                      {item.success ? '加载成功' : '调用失败'}
                    </span>
                  </div>
                  <div className="mt-1 text-gray-custom">
                    {item.api_protocol ?? '未配置协议'} · {item.base_url ?? '未配置 Base URL'}
                  </div>
                  {!item.success && (
                    <div className="mt-1 text-gray-custom">
                      {item.message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {message && (
        <div className="flex items-start gap-2 rounded-2xl border-4 border-ink bg-paper p-3 text-xs font-black text-ink">
          <CheckCircle2 size={16} className="shrink-0 text-primary" />
          {message}
        </div>
      )}
    </div>
  );
}
