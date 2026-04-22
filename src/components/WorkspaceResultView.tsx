import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Edit2,
  FileCheck,
  FileText,
  History,
  LogOut,
  MapPin,
  MessageCircle,
  Plus,
  Send,
  Settings,
  User,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

import {
  chatWithAgent,
  getContractHistory,
  getReport,
  type AnalysisReport,
} from '../services/api';
import {
  downloadAnnotatedContractHtml,
  downloadCleanReportHtml,
} from '../services/exportHtml.ts';
import {
  appendAgentMessage,
  getAgentMessages,
  sortHistoryEntries,
  type AgentChatMessage,
  type ContractHistoryItem,
  type WorkspaceChatThreads,
} from '../services/workspaceState';
import {
  AGENT_META,
  buildWorkspaceData,
  getRiskTone,
  type DocumentAnnotation,
  type AgentKey,
} from './workspaceData';

type WorkspaceResultViewProps = {
  contractId: string | null;
  onLogout: () => void;
  location: string | null;
  onNewChat: () => void;
  settings: any;
  setSettings: any;
  uploadedFileName: string | null;
  analysisReport: AnalysisReport | null;
};

type ViewMode = 'document' | 'report';

export default function WorkspaceResultView({
  contractId,
  onLogout,
  location,
  onNewChat,
  settings,
  setSettings,
  uploadedFileName,
  analysisReport,
}: WorkspaceResultViewProps) {
  const [activeNav, setActiveNav] = useState<
    'chat' | 'history' | 'preferences' | 'settings'
  >('chat');
  const [activeAgent, setActiveAgent] = useState<AgentKey>('owl');
  const [viewMode, setViewMode] = useState<ViewMode>('document');
  const [chatInput, setChatInput] = useState('');
  const [docTitle, setDocTitle] = useState('analysis-report.md');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const [selectedLineIndex, setSelectedLineIndex] = useState<number | null>(null);
  const [activeContractId, setActiveContractId] = useState<string | null>(contractId);
  const [activeReport, setActiveReport] = useState<AnalysisReport | null>(analysisReport);
  const [activeFileName, setActiveFileName] = useState<string | null>(uploadedFileName);
  const [activeLocation, setActiveLocation] = useState<string | null>(location);
  const [historyContracts, setHistoryContracts] = useState<ContractHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [chatThreads, setChatThreads] = useState<WorkspaceChatThreads>({});
  const [chatBusyKey, setChatBusyKey] = useState<string | null>(null);
  const [chatErrors, setChatErrors] = useState<Record<string, string | null>>({});
  const lineRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    if (activeFileName) {
      setDocTitle(activeFileName);
    }
  }, [activeFileName]);

  useEffect(() => {
    setActiveContractId(contractId);
    setActiveReport(analysisReport);
    setActiveFileName(uploadedFileName);
    setActiveLocation(location);
  }, [contractId, analysisReport, uploadedFileName, location]);

  const workspace = useMemo(
    () => buildWorkspaceData(activeReport),
    [activeReport]
  );
  const isTemplateReport = Boolean(activeReport?.is_template);

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 25, 50));

  const activeAgentMeta =
    AGENT_META.find((agent) => agent.key === activeAgent) ?? AGENT_META[0];
  const activeAnnotations = workspace.annotationsByAgent[activeAgent];
  const annotationMap = new Map<number, DocumentAnnotation>(
    activeAnnotations.map((item) => [item.lineIndex, item])
  );

  useEffect(() => {
    if (viewMode !== 'document' || selectedLineIndex === null) {
      return;
    }

    const target = lineRefs.current[selectedLineIndex];
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [selectedLineIndex, viewMode, activeAgent, workspace.documentLines]);

  const focusDocumentLine = (lineIndex?: number) => {
    setViewMode('document');
    if (typeof lineIndex === 'number') {
      setSelectedLineIndex(lineIndex);
    }
  };

  const activeThreadKey =
    activeContractId !== null ? `${activeContractId}:${activeAgent}` : null;
  const activeChatMessages: AgentChatMessage[] =
    activeContractId !== null
      ? getAgentMessages(chatThreads, activeContractId, activeAgent)
      : [];
  const activeChatBusy =
    activeThreadKey !== null && chatBusyKey === activeThreadKey;
  const activeChatError =
    activeThreadKey !== null ? chatErrors[activeThreadKey] ?? null : null;

  useEffect(() => {
    let isMounted = true;

    const loadHistory = async () => {
      setHistoryLoading(true);
      setHistoryError(null);
      try {
        const contracts = sortHistoryEntries(await getContractHistory());
        if (!isMounted) {
          return;
        }
        setHistoryContracts(contracts);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setHistoryError(error instanceof Error ? error.message : '获取审查历史失败');
      } finally {
        if (isMounted) {
          setHistoryLoading(false);
        }
      }
    };

    void loadHistory();

    return () => {
      isMounted = false;
    };
  }, [contractId, analysisReport?.contract_id]);

  const handleSelectHistory = async (historyItem: ContractHistoryItem) => {
    try {
      setHistoryLoading(true);
      setHistoryError(null);
      const report = await getReport(historyItem.contract_id);
      setActiveContractId(historyItem.contract_id);
      setActiveReport(report);
      setActiveFileName(historyItem.filename);
      setActiveLocation(historyItem.location);
      setExpandedCard(null);
      setSelectedLineIndex(null);
      setViewMode('document');
      setActiveNav('chat');
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : '加载历史报告失败');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSendChat = async () => {
    if (!activeContractId) {
      return;
    }

    const question = chatInput.trim();
    if (!question) {
      return;
    }

    const userMessage: AgentChatMessage = {
      role: 'user',
      content: question,
    };
    const threadKey = `${activeContractId}:${activeAgent}`;

    setChatThreads((prev) =>
      appendAgentMessage(prev, activeContractId, activeAgent, userMessage)
    );
    setChatErrors((prev) => ({ ...prev, [threadKey]: null }));
    setChatBusyKey(threadKey);
    setChatInput('');

    try {
      const response = await chatWithAgent(activeContractId, activeAgent, {
        question,
        messages: activeChatMessages,
      });
      setChatThreads((prev) =>
        appendAgentMessage(prev, activeContractId, activeAgent, {
          role: 'assistant',
          content: response.reply,
        })
      );
    } catch (error) {
      setChatErrors((prev) => ({
        ...prev,
        [threadKey]: error instanceof Error ? error.message : '发送追问失败',
      }));
    } finally {
      setChatBusyKey((current) => (current === threadKey ? null : current));
    }
  };

  const handleDownloadClean = () => {
    if (!activeReport) {
      setShowDownloadMenu(false);
      return;
    }

    downloadCleanReportHtml({
      report: activeReport,
      fileName: docTitle || activeFileName,
      location: activeLocation,
    });
    setShowDownloadMenu(false);
  };

  const handleDownloadAnnotated = () => {
    if (!activeReport) {
      setShowDownloadMenu(false);
      return;
    }

    downloadAnnotatedContractHtml({
      report: activeReport,
      fileName: docTitle || activeFileName,
      location: activeLocation,
    });
    setShowDownloadMenu(false);
  };

  const renderAgentCards = () => {
    if (activeAgent === 'owl') {
      if (workspace.owlCards.length === 0) {
        return (
          <EmptyPanel
            emoji="🦉"
            text="当前报告没有返回条款风险，可能是空白模板或后端还没给出有效结论。"
          />
        );
      }

      return workspace.owlCards.map((card, index) => {
        const tone = getRiskTone(card.badge);
        const cardId = `owl-${index}`;
        const open = expandedCard === cardId;
        return (
          <div
            key={cardId}
            className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] relative overflow-hidden"
          >
            <div className={`absolute top-0 left-0 w-full h-2 ${tone.stripe}`}></div>
            <div className="flex justify-between items-start mb-2 mt-1 gap-3">
              <h3 className="font-black text-ink text-lg">{card.title}</h3>
              <span
                className={`${tone.badge} px-2 py-1 rounded-lg text-xs font-black border-2 border-ink`}
              >
                {tone.label}
              </span>
            </div>
            <p className="text-sm font-bold text-gray-custom mb-3">{card.body}</p>
            <div className="flex gap-2">
              <button className="flex-1 bg-secondary border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-secondary/80 transition-colors">
                自动修正
              </button>
              <button
                onClick={() => {
                  focusDocumentLine(card.lineIndex);
                  setExpandedCard(open ? null : cardId);
                }}
                className="flex-1 bg-surface border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-ink/5 transition-colors"
              >
                {open ? '收起法律意见' : '查看法律意见'}
              </button>
            </div>
            {open && (
              <div className="mt-3 rounded-xl border-2 border-ink/10 bg-paper p-3 space-y-2">
                {card.legalBasis && (
                  <p className="text-xs font-black text-primary">
                    法律依据：{card.legalBasis}
                  </p>
                )}
                {card.suggestion && (
                  <p className="text-xs font-bold text-ink/80">
                    建议：{card.suggestion}
                  </p>
                )}
              </div>
            )}
          </div>
        );
      });
    }

    if (activeAgent === 'dog') {
      if (workspace.dogCards.length === 0) {
        return (
          <EmptyPanel
            emoji="🐶"
            text="当前没有法律依据返回。模板合同通常会只输出条款风险，不一定触发完整检索流程。"
          />
        );
      }

      return workspace.dogCards.map((card, index) => {
        const cardId = `dog-${index}`;
        const open = expandedCard === cardId;
        return (
          <div
            key={cardId}
            className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] relative overflow-hidden"
          >
            <div className="absolute top-0 left-0 w-full h-2 bg-primary"></div>
            <div className="font-black text-ink text-lg mb-2 mt-1">{card.title}</div>
            <p className="text-sm font-bold text-gray-custom mb-3">{card.note}</p>
            <button
              onClick={() => {
                focusDocumentLine(card.lineIndex);
                setExpandedCard(open ? null : cardId);
              }}
              className="w-full bg-surface border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-ink/5 transition-colors"
            >
              {open ? '收起法条内容' : '查看明确法条'}
            </button>
            {open && (
              <div className="mt-3 rounded-xl border-2 border-ink/10 bg-paper p-3">
                <p className="text-xs font-bold text-ink/80 whitespace-pre-wrap">
                  {card.body}
                </p>
              </div>
            )}
          </div>
        );
      });
    }

    if (workspace.beaverCards.length === 0) {
      return (
        <EmptyPanel
          emoji="🦫"
          text={
            isTemplateReport
              ? '当前没有费用核算结果。模板合同通常不会走到费用核算这一步。'
              : '当前没有费用核算结果。'
          }
        />
      );
    }

    return workspace.beaverCards.map((card, index) => {
      const tone = getRiskTone(card.badge);
      const cardId = `beaver-${index}`;
      const open = expandedCard === cardId;
      return (
        <div
          key={cardId}
          className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] relative overflow-hidden"
        >
          <div className={`absolute top-0 left-0 w-full h-2 ${tone.stripe}`}></div>
          <div className="flex justify-between items-start mb-2 mt-1 gap-3">
            <h3 className="font-black text-ink text-lg">{card.title}</h3>
            <span
              className={`${tone.badge} px-2 py-1 rounded-lg text-xs font-black border-2 border-ink`}
            >
              {tone.label}
            </span>
          </div>
          <p className="text-sm font-bold text-gray-custom mb-3">{card.body}</p>
          <div className="flex gap-2">
            <button className="flex-1 bg-primary border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-primary/80 transition-colors">
              重新核算
            </button>
            <button
              onClick={() => {
                focusDocumentLine(card.lineIndex);
                setExpandedCard(open ? null : cardId);
              }}
              className="flex-1 bg-surface border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-ink/5 transition-colors"
            >
              {open ? '收起说明' : '查看计算说明'}
            </button>
          </div>
          {open && (
            <div className="mt-3 rounded-xl border-2 border-ink/10 bg-paper p-3">
              <p className="text-xs font-bold text-ink/80">{card.footnote}</p>
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div className="flex-1 flex overflow-hidden border-4 border-ink rounded-3xl shadow-[8px_8px_0px_var(--color-ink)] bg-surface m-4 sm:m-8 mt-0">
      <aside className="w-20 sm:w-24 border-r-4 border-ink bg-paper flex flex-col items-center py-6 shrink-0 z-10">
        <div className="w-12 h-12 bg-secondary border-4 border-ink rounded-2xl flex items-center justify-center text-2xl mb-8 shadow-[2px_2px_0px_var(--color-ink)] transform -rotate-6">
          🐾
        </div>

        <nav className="flex-1 flex flex-col gap-6 w-full px-2 sm:px-4">
          <NavButton
            active={activeNav === 'chat'}
            icon={<MessageCircle size={24} strokeWidth={2.5} />}
            label="实时对话"
            onClick={() => setActiveNav('chat')}
          />
          <NavButton
            active={activeNav === 'history'}
            icon={<History size={24} strokeWidth={2.5} />}
            label="审查历史"
            onClick={() => setActiveNav('history')}
          />
          <NavButton
            active={activeNav === 'preferences'}
            icon={<User size={24} strokeWidth={2.5} />}
            label="个人偏好"
            onClick={() => setActiveNav('preferences')}
          />
          <NavButton
            active={activeNav === 'settings'}
            icon={<Settings size={24} strokeWidth={2.5} />}
            label="系统设置"
            onClick={() => setActiveNav('settings')}
          />
        </nav>

        <button
          onClick={onLogout}
          className="mt-auto flex flex-col items-center gap-1 p-2 text-accent hover:bg-accent/10 rounded-xl transition-colors w-full"
        >
          <LogOut size={24} strokeWidth={2.5} />
          <span className="text-[10px] font-black">退出登录</span>
        </button>
      </aside>

      <section className="w-80 sm:w-96 border-r-4 border-ink bg-surface flex flex-col shrink-0 z-0 relative">
        {activeNav === 'chat' ? (
          <>
            <div className="p-4 border-b-4 border-ink bg-paper shrink-0">
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                {AGENT_META.map((agent) => (
                  <button
                    key={agent.key}
                    onClick={() => {
                      setActiveAgent(agent.key);
                      setExpandedCard(null);
                    }}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl border-2 border-ink font-black text-sm whitespace-nowrap transition-all ${
                      activeAgent === agent.key
                        ? `${agent.colorClass} shadow-[2px_2px_0px_var(--color-ink)] scale-105 text-[#2D3142]`
                        : 'bg-surface text-gray-custom hover:bg-ink/5'
                    }`}
                  >
                    <AgentIcon emoji={agent.emoji} />
                    {agent.name}
                  </button>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-2 text-xs font-bold text-ink/70">
                <CheckCircle2 size={14} className="text-primary" /> 审查完成 ·{' '}
                {activeAgentMeta.role}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface-alt">
              {activeChatMessages.length > 0 ? (
                <div className="space-y-3">
                  {activeChatMessages.map((message, index) => (
                    <div
                      key={`${message.role}-${index}-${message.content}`}
                      className={`rounded-2xl border-4 border-ink p-3 shadow-[4px_4px_0px_var(--color-ink)] ${
                        message.role === 'user'
                          ? 'bg-secondary/30'
                          : 'bg-paper'
                      }`}
                    >
                      <div className="text-[11px] font-black text-gray-custom mb-1">
                        {message.role === 'user' ? '你' : activeAgentMeta.name}
                      </div>
                      <p className="text-sm font-bold text-ink whitespace-pre-wrap">
                        {message.content}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border-4 border-dashed border-ink/40 bg-paper p-4 text-sm font-bold text-gray-custom">
                  这里可以继续追问当前这份合同。比如问“这条风险具体是什么意思？”或“如果房东不改，我该怎么谈？”
                </div>
              )}

              {activeChatBusy && (
                <div className="rounded-2xl border-4 border-ink bg-primary/20 p-3 text-sm font-black text-ink">
                  {activeAgentMeta.name} 正在结合当前合同继续分析...
                </div>
              )}

              {activeChatError && (
                <div className="rounded-2xl border-4 border-accent bg-accent/10 p-3 text-sm font-black text-accent">
                  {activeChatError}
                </div>
              )}

              <div className="pt-2">
                <div className="text-xs font-black text-gray-custom mb-3">
                  当前合同分析卡片
                </div>
                {renderAgentCards()}
              </div>
            </div>

            <div className="p-4 border-t-4 border-ink bg-surface shrink-0">
              <div className="relative">
                <textarea
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder={`告诉 ${activeAgentMeta.name} 你的情况...`}
                  className="w-full border-4 border-ink rounded-2xl p-3 pr-12 text-sm font-bold focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all resize-none h-24 bg-paper"
                ></textarea>
                <button
                  onClick={handleSendChat}
                  disabled={!activeContractId || !chatInput.trim() || activeChatBusy}
                  className={`absolute right-3 bottom-3 p-2 rounded-xl transition-colors ${
                    !activeContractId || !chatInput.trim() || activeChatBusy
                      ? 'bg-ink/40 text-surface cursor-not-allowed'
                      : 'bg-ink text-surface hover:bg-ink/80'
                  }`}
                >
                  <Send size={16} strokeWidth={3} />
                </button>
              </div>
            </div>
          </>
        ) : activeNav === 'history' ? (
          <SimplePanel title="审查历史">
            {historyLoading ? (
              <div className="rounded-2xl border-4 border-ink bg-paper p-4 text-sm font-black text-gray-custom">
                正在加载历史记录...
              </div>
            ) : historyContracts.length === 0 ? (
              <EmptyPanel
                emoji="🗂️"
                text="当前登录期内还没有可切换的审查历史。"
              />
            ) : (
              historyContracts.map((item) => {
                const active = item.contract_id === activeContractId;
                return (
                  <button
                    key={item.contract_id}
                    onClick={() => void handleSelectHistory(item)}
                    className={`w-full text-left border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] transition-all ${
                      active ? 'bg-secondary/40' : 'bg-surface hover:bg-paper'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="font-black text-ink truncate">
                          {item.filename}
                        </h3>
                        <p className="text-xs font-bold text-gray-custom mt-1">
                          {item.location || '未标注城市'} · {item.status}
                        </p>
                      </div>
                      {item.burn_after_reading && (
                        <span className="shrink-0 rounded-lg border-2 border-accent/30 bg-accent/10 px-2 py-1 text-[10px] font-black text-accent">
                          阅后即焚
                        </span>
                      )}
                    </div>
                    <div className="mt-3 flex gap-2 flex-wrap">
                      <span className="bg-accent/20 text-accent px-2 py-1 rounded-lg text-[10px] font-black border-2 border-accent/30">
                        {item.risk_summary.high} 高风险
                      </span>
                      <span className="bg-primary/20 text-primary px-2 py-1 rounded-lg text-[10px] font-black border-2 border-primary/30">
                        {item.risk_summary.medium} 提示
                      </span>
                      <span className="bg-secondary/20 text-ink px-2 py-1 rounded-lg text-[10px] font-black border-2 border-ink/20">
                        {item.risk_summary.total} 总项
                      </span>
                    </div>
                  </button>
                );
              })
            )}

            {historyError && (
              <div className="rounded-2xl border-4 border-accent bg-accent/10 p-3 text-sm font-black text-accent">
                {historyError}
              </div>
            )}
          </SimplePanel>
        ) : activeNav === 'preferences' ? (
          <SimplePanel title="个人偏好">
            <div className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] space-y-3 text-sm font-bold text-ink">
              <div>身份标签：{settings.identity || '未填写'}</div>
              <div>心理预期：{settings.budget || '未填写'}</div>
              <div>核心底线：{settings.dealbreakers || '未填写'}</div>
            </div>
          </SimplePanel>
        ) : (
          <SimplePanel title="系统设置">
            <div className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] space-y-6 text-sm font-bold text-ink">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-black text-ink">隐私消除</div>
                  <div className="text-xs font-bold text-gray-custom mt-1">
                    新上传的合同会先自动脱敏，再进入分析流程。
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={Boolean(settings.privacyRedaction)}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        privacyRedaction: event.target.checked,
                      })
                    }
                  />
                  <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                </label>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-black text-ink">桌面通知</div>
                  <div className="text-xs font-bold text-gray-custom mt-1">
                    小动物们分析完成后，第一时间通知你。
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={Boolean(settings.notifications)}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        notifications: event.target.checked,
                      })
                    }
                  />
                  <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                </label>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-black text-ink">阅后即焚</div>
                  <div className="text-xs font-bold text-gray-custom mt-1">
                    退出登录后自动清除当前合同记录，只保留偏好设置。
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={Boolean(settings.burnAfterReading)}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        burnAfterReading: event.target.checked,
                      })
                    }
                  />
                  <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                </label>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-black text-ink">界面主题</div>
                  <div className="text-xs font-bold text-gray-custom mt-1">
                    选择你喜欢的界面风格。
                  </div>
                </div>
                <select
                  className="border-4 border-ink rounded-xl p-2 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all text-sm text-ink shrink-0"
                  value={settings.theme}
                  onChange={(event) =>
                    setSettings({ ...settings, theme: event.target.value })
                  }
                >
                  <option value="light">浅色模式</option>
                  <option value="dark">深色模式</option>
                </select>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-black text-ink">字体大小</div>
                  <div className="text-xs font-bold text-gray-custom mt-1">
                    调整合同阅读区和报告区的文字大小。
                  </div>
                </div>
                <select
                  className="border-4 border-ink rounded-xl p-2 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all text-sm text-ink shrink-0"
                  value={settings.fontSize}
                  onChange={(event) =>
                    setSettings({ ...settings, fontSize: event.target.value })
                  }
                >
                  <option value="standard">标准</option>
                  <option value="large">偏大</option>
                  <option value="xlarge">特大</option>
                </select>
              </div>

              {activeLocation && (
                <div className="rounded-xl border-2 border-ink/10 bg-paper px-3 py-2 text-xs font-bold text-gray-custom">
                  当前定位：{activeLocation}
                </div>
              )}
            </div>
          </SimplePanel>
        )}
      </section>

      <section className="flex-1 flex flex-col bg-surface overflow-hidden relative">
        <div className="h-16 border-b-4 border-ink bg-paper flex items-center justify-between px-6 shrink-0 gap-3">
          <div className="flex items-center gap-2 max-w-[200px] sm:max-w-md w-full">
            {isEditingTitle ? (
              <input
                type="text"
                value={docTitle}
                onChange={(event) => setDocTitle(event.target.value)}
                onBlur={() => setIsEditingTitle(false)}
                onKeyDown={(event) =>
                  event.key === 'Enter' && setIsEditingTitle(false)
                }
                autoFocus
                className="font-black text-ink text-sm sm:text-base border-b-2 border-ink bg-transparent focus:outline-none w-full"
              />
            ) : (
              <>
                <span
                  className="font-black text-ink text-sm sm:text-base truncate"
                  title={docTitle}
                >
                  {docTitle}
                </span>
                <button
                  onClick={() => setIsEditingTitle(true)}
                  className="text-gray-custom hover:text-ink transition-colors shrink-0"
                >
                  <Edit2 size={14} strokeWidth={3} />
                </button>
              </>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {activeLocation && (
              <div className="hidden sm:flex items-center gap-1 bg-primary/20 text-ink border-2 border-ink px-3 py-1.5 rounded-xl text-xs font-black shadow-[2px_2px_0px_var(--color-ink)]">
                <MapPin size={14} strokeWidth={3} /> {activeLocation}
              </div>
            )}
            <div className="flex items-center border-2 border-ink rounded-xl bg-surface overflow-hidden shadow-[2px_2px_0px_var(--color-ink)]">
              <button
                onClick={() => setViewMode('document')}
                className={`px-3 py-1.5 text-xs font-black transition-colors ${
                  viewMode === 'document'
                    ? 'bg-secondary text-ink'
                    : 'hover:bg-ink/10 text-gray-custom'
                }`}
              >
                原文视图
              </button>
              <button
                onClick={() => setViewMode('report')}
                className={`px-3 py-1.5 text-xs font-black transition-colors border-l-2 border-ink ${
                  viewMode === 'report'
                    ? 'bg-primary text-ink'
                    : 'hover:bg-ink/10 text-gray-custom'
                }`}
              >
                报告视图
              </button>
            </div>
            <button
              onClick={() => setShowNewChatModal(true)}
              className="hidden sm:flex items-center gap-2 bg-surface border-2 border-ink px-3 py-1.5 rounded-xl text-xs font-black shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 transition-all"
            >
              <Plus size={14} strokeWidth={3} /> 新建对话
            </button>
            <div className="flex items-center border-2 border-ink rounded-xl bg-surface overflow-hidden shadow-[2px_2px_0px_var(--color-ink)]">
              <button
                onClick={handleZoomOut}
                className="px-2 py-1.5 hover:bg-ink/10 transition-colors border-r-2 border-ink"
              >
                <ZoomOut size={14} strokeWidth={3} />
              </button>
              <span className="px-3 py-1.5 text-xs font-black w-14 text-center">
                {zoomLevel}%
              </span>
              <button
                onClick={handleZoomIn}
                className="px-2 py-1.5 hover:bg-ink/10 transition-colors border-l-2 border-ink"
              >
                <ZoomIn size={14} strokeWidth={3} />
              </button>
            </div>
            <div className="relative">
              <button
                onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                className="bg-primary text-ink border-2 border-ink p-1.5 rounded-xl shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 transition-all flex items-center gap-1"
              >
                <Download size={16} strokeWidth={3} />
              </button>

              <AnimatePresence>
                {showDownloadMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-full mt-2 w-44 bg-surface border-4 border-ink rounded-2xl shadow-[4px_4px_0px_var(--color-ink)] overflow-hidden z-50 flex flex-col"
                  >
                    <button
                      onClick={handleDownloadClean}
                      className="flex items-center gap-2 px-4 py-3 text-sm font-black text-ink hover:bg-secondary/20 border-b-2 border-ink/10 transition-colors text-left"
                    >
                      <FileCheck size={16} className="shrink-0" /> 导出清洁版
                    </button>
                    <button
                      onClick={handleDownloadAnnotated}
                      className="flex items-center gap-2 px-4 py-3 text-sm font-black text-ink hover:bg-accent/20 transition-colors text-left"
                    >
                      <FileText size={16} className="shrink-0" /> 导出标注版
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-8 sm:p-12 bg-surface-alt flex justify-center">
          <div className="min-w-max min-h-max">
            <div
              className="w-[800px] bg-surface border-2 border-ink/20 shadow-lg p-10 transition-transform duration-300 origin-top"
              style={{ transform: `scale(${zoomLevel / 100})` }}
            >
              <h2 className="text-2xl font-black mb-8 text-center text-ink">
                {viewMode === 'document' ? '原版合同' : workspace.heading}
              </h2>
              {viewMode === 'document' ? (
                <div
                  className={`space-y-5 leading-loose text-ink/80 font-bold ${
                    settings.fontSize === 'xlarge'
                      ? 'text-lg'
                      : settings.fontSize === 'large'
                        ? 'text-base'
                        : 'text-sm'
                  }`}
                >
                  {workspace.documentLines.map((line, index) => {
                    const annotation = annotationMap.get(index);
                    const tone = annotation
                      ? getRiskTone(annotation.level)
                      : null;
                    const isSelected = selectedLineIndex === index;

                    return (
                      <div
                        key={`${index}-${line}`}
                        className="space-y-2 scroll-mt-24"
                        ref={(element) => {
                          lineRefs.current[index] = element;
                        }}
                      >
                        <p
                          className={
                            annotation
                              ? `${tone?.highlight} px-1 rounded-md inline-block ${
                                  isSelected ? 'ring-4 ring-secondary/60' : ''
                                }`
                              : isSelected
                                ? 'px-1 rounded-md inline-block ring-4 ring-secondary/60'
                                : undefined
                          }
                        >
                          {line}
                        </p>
                        {annotation && (
                          <div className="rounded-xl border-2 border-ink/10 bg-paper px-3 py-2">
                            <div className="text-xs font-black text-ink mb-1">
                              {annotation.title}
                            </div>
                            <div className="text-xs font-bold text-gray-custom">
                              {annotation.note}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div
                  className={`space-y-3 leading-loose text-ink/80 font-bold ${
                    settings.fontSize === 'xlarge'
                      ? 'text-lg'
                      : settings.fontSize === 'large'
                        ? 'text-base'
                        : 'text-sm'
                  }`}
                >
                  {workspace.reportLines.map((line, index) => (
                    <div key={`${index}-${line}`}>
                      <ReportLine line={line} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="h-10 border-t-4 border-ink bg-paper flex items-center justify-between px-6 shrink-0 text-xs font-black text-gray-custom z-10">
          <div className="flex gap-4">
            <span>字数: {workspace.wordCount}</span>
            <span className="text-accent flex items-center gap-1">
              <AlertTriangle size={12} strokeWidth={3} />{' '}
              {workspace.highRiskCount} 处高风险
            </span>
            <span className="text-primary flex items-center gap-1">
              <AlertTriangle size={12} strokeWidth={3} />{' '}
              {workspace.mediumRiskCount} 处提示
            </span>
          </div>
          <div className="flex items-center gap-2 text-primary">
            <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
            {workspace.statusText}
          </div>
        </div>

        <AnimatePresence>
          {showNewChatModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4"
            >
              <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="bg-surface border-4 border-ink rounded-3xl p-8 max-w-sm w-full shadow-[8px_8px_0px_var(--color-ink)]"
              >
                <div className="text-4xl mb-4 text-center">✓</div>
                <h3 className="text-xl font-black text-ink mb-2 text-center">
                  开启新合同审查？
                </h3>
                <p className="text-sm font-bold text-gray-custom mb-8 text-center">
                  当前合同的分析记录会保留在当前会话中，确认后将返回上传页。
                </p>
                <div className="flex gap-4">
                  <button
                    onClick={() => setShowNewChatModal(false)}
                    className="flex-1 py-3 rounded-xl border-4 border-ink font-black text-ink hover:bg-surface-alt transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={() => {
                      setShowNewChatModal(false);
                      onNewChat();
                    }}
                    className="flex-1 py-3 rounded-xl border-4 border-ink bg-primary font-black text-ink shadow-[4px_4px_0px_var(--color-ink)] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all"
                  >
                    确认新建
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  );
}

function AgentIcon({
  emoji,
  className = '',
}: {
  emoji: string;
  className?: string;
}) {
  return <span className={className}>{emoji}</span>;
}

function NavButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${
        active
          ? 'bg-ink text-surface shadow-[2px_2px_0px_var(--color-ink)] translate-x-1'
          : 'text-gray-custom hover:bg-ink/10'
      }`}
    >
      {icon}
      <span className="text-[10px] font-black">{label}</span>
    </button>
  );
}

function EmptyPanel({ emoji, text }: { emoji: string; text: string }) {
  return (
    <div className="text-center p-8 text-gray-custom font-bold">
      <div className="text-4xl mb-2">{emoji}</div>
      <p>{text}</p>
    </div>
  );
}

function SimplePanel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="flex-1 flex flex-col bg-surface-alt min-h-0">
      <div className="p-4 border-b-4 border-ink bg-paper shrink-0">
        <h2 className="text-xl font-black text-ink">{title}</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">{children}</div>
    </div>
  );
}

function ReportLine({ line }: { line: string }) {
  if (!line.trim()) {
    return <div className="h-3" />;
  }

  if (line.startsWith('### ')) {
    return (
      <h3 className="text-lg font-black text-ink">
        {line.replace(/^###\s*/, '')}
      </h3>
    );
  }

  if (line.startsWith('## ')) {
    return (
      <h2 className="text-xl font-black text-ink">
        {line.replace(/^##\s*/, '')}
      </h2>
    );
  }

  if (line.startsWith('# ')) {
    return (
      <h1 className="text-2xl font-black text-ink">
        {line.replace(/^#\s*/, '')}
      </h1>
    );
  }

  if (line.startsWith('- ')) {
    return <p className="pl-4 text-ink/80">• {line.replace(/^- /, '')}</p>;
  }

  if (line.startsWith('> ')) {
    return (
      <blockquote className="border-l-4 border-secondary pl-4 text-ink/70 italic">
        {line.replace(/^> /, '')}
      </blockquote>
    );
  }

  return <p>{line}</p>;
}
