import { useEffect, useRef, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

import {
  getAnalysisTask,
  getReport,
  queueAnalysisTask,
  streamAnalysisTask,
} from '../services/api.ts';
import {
  getAgentCheckpoint,
  getLiveActionText,
} from '../services/analysisProgress';
import type { AnalysisEvent, AnalysisReport, AnalysisTask } from '../services/api.ts';
import {
  getOrCreateQueuedTask,
  releaseQueuedTask,
} from '../services/analysisTaskRegistry';

type Props = {
  contractId: string | null;
  fileName: string | null;
  onComplete: (report: AnalysisReport) => void;
  onRetry: () => void;
  theme: string;
};

const AGENT_LABELS: Record<'owl' | 'dog' | 'beaver' | 'cat', string> = {
  owl: '猫头鹰分析师',
  dog: '猎犬检索师',
  beaver: '海狸计算师',
  cat: '橘猫报告师',
};

const AGENT_EMOJI: Record<'owl' | 'dog' | 'beaver' | 'cat', string> = {
  owl: '🦉',
  dog: '🐶',
  beaver: '🦫',
  cat: '🐱',
};

function isAgent(value: string | undefined): value is 'owl' | 'dog' | 'beaver' | 'cat' {
  return value === 'owl' || value === 'dog' || value === 'beaver' || value === 'cat';
}

export default function LiveAnalysisStage({
  contractId,
  fileName,
  onComplete,
  onRetry,
}: Props) {
  const [progress, setProgress] = useState(5);
  const [currentAgent, setCurrentAgent] = useState<'owl' | 'dog' | 'beaver' | 'cat'>('owl');
  const [actionText, setActionText] = useState('正在准备分析任务...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reportParagraphCount, setReportParagraphCount] = useState(0);
  const [taskMeta, setTaskMeta] = useState<AnalysisTask | null>(null);
  const beaverVisibleUntilRef = useRef(0);
  const delayedCatTransitionRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!contractId) {
      setErrorMessage('缺少合同信息，请重新上传文件。');
      return;
    }

    let isCancelled = false;
    let completionTimer: ReturnType<typeof setTimeout> | null = null;

    const setAgentIfKnown = (agent?: string) => {
      if (isAgent(agent)) {
        setCurrentAgent(agent);
      }
    };

    const scheduleCatTransition = (callback: () => void) => {
      const remaining = beaverVisibleUntilRef.current - Date.now();
      if (remaining <= 0) {
        callback();
        return;
      }
      if (delayedCatTransitionRef.current) {
        clearTimeout(delayedCatTransitionRef.current);
      }
      delayedCatTransitionRef.current = setTimeout(() => {
        delayedCatTransitionRef.current = null;
        callback();
      }, remaining);
    };

    let eventSource: EventSource | null = null;

    const handleEvent = async (event: AnalysisEvent) => {
        if (isCancelled) {
          return;
        }

        if (event.type === 'error') {
          setErrorMessage(event.message ?? '合同分析失败，请稍后重试。');
          releaseQueuedTask(contractId);
          eventSource?.close();
          return;
        }

        if (event.type === 'analysis_started') {
          setProgress(8);
          setCurrentAgent('owl');
          setActionText(getLiveActionText(event));
        } else if (event.type === 'progress') {
          setActionText(getLiveActionText(event));
        } else if (event.type === 'template_detected') {
          setCurrentAgent('cat');
          setProgress((prev) => Math.max(prev, 35));
          setActionText(event.message ?? '检测到模板合同，改走模板分析流程...');
        } else if (event.type === 'agent_started') {
          if (event.agent === 'cat') {
            scheduleCatTransition(() => setCurrentAgent('cat'));
          } else {
            setAgentIfKnown(event.agent);
          }
          if (event.agent && isAgent(event.agent)) {
            setProgress((prev) =>
              Math.max(prev, getAgentCheckpoint(event.agent, 'started'))
            );
          }
          setActionText(getLiveActionText(event));
        } else if (event.type === 'agent_progress' || event.type === 'heartbeat') {
          if (event.agent === 'cat') {
            scheduleCatTransition(() => setCurrentAgent('cat'));
          } else {
            setAgentIfKnown(event.agent);
          }
          setActionText(getLiveActionText(event));
        } else if (event.type === 'agent_completed') {
          if (event.agent === 'cat') {
            scheduleCatTransition(() => setCurrentAgent('cat'));
          } else {
            setAgentIfKnown(event.agent);
          }
          if (event.agent && isAgent(event.agent)) {
            setProgress((prev) =>
              Math.max(prev, getAgentCheckpoint(event.agent, 'completed'))
            );
          }
          setActionText(getLiveActionText(event));
        } else if (event.type === 'agent_failed') {
          const label = isAgent(event.agent) ? AGENT_LABELS[event.agent] : '分析代理';
          setErrorMessage(`${label}失败：${event.message || '执行失败'}`);
          releaseQueuedTask(contractId);
          eventSource.close();
          return;
        } else if (event.type === 'owl_analysis') {
          setCurrentAgent('owl');
          setProgress((prev) => Math.max(prev, 32));
          setActionText('猫头鹰已完成条款解析。');
        } else if (event.type === 'dog_retrieval') {
          setCurrentAgent('dog');
          setProgress((prev) => Math.max(prev, 60));
          setActionText('猎犬已完成法律检索。');
        } else if (event.type === 'beaver_calculation') {
          setCurrentAgent('beaver');
          setProgress((prev) => Math.max(prev, 80));
          beaverVisibleUntilRef.current = Date.now() + 1500;
          const beaverMeta = event.data?.data ?? {};
          if (beaverMeta.llm_success && beaverMeta.mode === 'llm_full_text') {
            setActionText('海狸已完成全文费用分析。');
          } else if (beaverMeta.llm_success) {
            setActionText('海狸已完成模型复核。');
          } else if (beaverMeta.llm_attempted) {
            setActionText('海狸已完成基础核算，模型复核失败后已回退。');
          } else {
            setActionText('海狸已完成费用核算。');
          }
        } else if (event.type === 'report_paragraph') {
          scheduleCatTransition(() => setCurrentAgent('cat'));
          setProgress((prev) => Math.max(prev, 88));
          setReportParagraphCount((prev) => Math.max(prev, (event.index ?? 0) + 1));
          setActionText(
            `橘猫正在整理报告段落 ${
              typeof event.index === 'number' && typeof event.total === 'number'
                ? `${event.index + 1}/${event.total}`
                : ''
            }`.trim()
          );
        } else if (event.type === 'cat_report') {
          scheduleCatTransition(() => setCurrentAgent('cat'));
          setProgress((prev) => Math.max(prev, 95));
          setActionText('橘猫已整理完最终报告。');
        } else if (event.type === 'analysis_complete') {
          setProgress(100);
          scheduleCatTransition(() => setCurrentAgent('cat'));
          setActionText('分析完成，正在打开结果...');
        }

        if (event.type === 'analysis_complete') {
          try {
            const report = await getReport(contractId);
            if (isCancelled) {
              return;
            }
            completionTimer = setTimeout(() => {
              onComplete(report);
            }, 400);
          } catch (error) {
            setErrorMessage(
              error instanceof Error ? error.message : '获取分析报告失败，请稍后重试。'
            );
          } finally {
            releaseQueuedTask(contractId);
            eventSource?.close();
          }
        }
    };

    const handleError = (error: Error) => {
        if (isCancelled) {
          return;
        }
        releaseQueuedTask(contractId);
        setErrorMessage(error.message || '合同分析失败，请稍后重试。');
    };

    (async () => {
      try {
        const task = await getOrCreateQueuedTask(contractId, () =>
          queueAnalysisTask(contractId)
        );
        if (isCancelled) {
          return;
        }

        let streamTask = task;
        if (!streamTask.stream_token) {
          console.warn(
            '[LiveAnalysisStage] stream_token missing from queued task; refreshing task status'
          );
          streamTask = await getAnalysisTask(task.task_id);
        }

        setTaskMeta(streamTask);
        setActionText(
          streamTask.queue_position && streamTask.queue_position > 1
            ? `任务已进入队列，前方还有 ${streamTask.queue_position - 1} 个任务...`
            : '任务已创建，准备开始分析...'
        );
        if (!streamTask.stream_token) {
          console.warn(
            '[LiveAnalysisStage] stream_token missing; using legacy stream mode'
          );
        }
        eventSource = streamAnalysisTask(
          streamTask.task_id,
          streamTask.stream_token,
          handleEvent,
          handleError,
          {
            idleTimeoutMs: 600000,
          }
        );
      } catch (error) {
        handleError(
          error instanceof Error ? error : new Error('创建分析任务失败')
        );
      }
    })();

    return () => {
      isCancelled = true;
      if (completionTimer) {
        clearTimeout(completionTimer);
      }
      if (delayedCatTransitionRef.current) {
        clearTimeout(delayedCatTransitionRef.current);
      }
      eventSource?.close();
    };
  }, [contractId]);

  if (errorMessage) {
    return (
      <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
        <div className="m-auto w-full max-w-md flex flex-col items-center justify-center shrink-0 py-4 text-center">
          <div className="mb-6">
            <AlertTriangle size={56} className="text-accent" strokeWidth={2.5} />
          </div>
          <h2 className="text-2xl font-black mb-3 text-ink">分析中断了</h2>
          <p className="text-sm font-bold text-gray-custom mb-6">{errorMessage}</p>
          <button
            onClick={onRetry}
            className="px-6 py-3 rounded-2xl border-4 border-ink bg-primary font-black text-ink shadow-[4px_4px_0px_var(--color-ink)] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all"
          >
            返回重新上传
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
      <div className="m-auto w-full max-w-md flex flex-col items-center justify-center shrink-0 py-4">
        <div className="text-6xl mb-6 animate-bounce">{AGENT_EMOJI[currentAgent]}</div>
        <h2 className="text-2xl font-black mb-2 text-ink">{AGENT_LABELS[currentAgent]}</h2>
        <p className="text-sm font-bold text-accent mb-2">{actionText}</p>
        {fileName && (
          <p className="text-xs font-bold text-gray-custom mb-2">当前文件：{fileName}</p>
        )}
        {taskMeta && (
          <p className="text-xs font-bold text-gray-custom mb-2">
            当前任务：{taskMeta.task_id.slice(0, 8)} · 状态 {taskMeta.status}
          </p>
        )}
        {reportParagraphCount > 0 && (
          <p className="text-xs font-bold text-gray-custom mb-6">
            已生成报告段落：{reportParagraphCount} 段
          </p>
        )}

        <div className="w-full h-6 bg-surface border-4 border-ink rounded-full overflow-hidden shadow-[4px_4px_0px_var(--color-ink)]">
          <div
            className="h-full bg-primary transition-all duration-300 relative"
            style={{ width: `${progress}%` }}
          >
            <div
              className="absolute inset-0 bg-surface/20 w-full"
              style={{
                backgroundImage:
                  'linear-gradient(45deg, rgba(255,255,255,0.2) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.2) 75%, transparent 75%, transparent)',
                backgroundSize: '1rem 1rem',
              }}
            ></div>
          </div>
        </div>
        <div className="w-full flex justify-between mt-4 text-sm font-black text-ink">
          <span>进度 {progress}%</span>
          <span>真实分析进行中</span>
        </div>
      </div>
    </div>
  );
}
