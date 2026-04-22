import type {
  AnalysisReport,
  LegalReference,
  RiskItem,
  UtilityCheck,
} from '../services/api.ts';
import { convertAllCards, type UnifiedCard } from './cardConverters.ts';

export type AgentKey = 'owl' | 'dog' | 'beaver';

export interface AgentMeta {
  key: AgentKey;
  emoji: string;
  name: string;
  role: string;
  colorClass: string;
}

export interface RiskCardViewModel {
  title: string;
  body: string;
  badge: 'high' | 'medium' | 'low';
  legalBasis?: string;
  suggestion?: string;
  lineIndex?: number;
}

export interface ReferenceCardViewModel {
  title: string;
  body: string;
  note: string;
  lineIndex?: number;
}

export interface CostCardViewModel {
  title: string;
  body: string;
  badge: 'high' | 'medium' | 'low';
  footnote: string;
  lineIndex?: number;
}

export interface DocumentAnnotation {
  lineIndex: number;
  level: 'high' | 'medium' | 'low';
  title: string;
  note: string;
}

export interface ExportDocumentAnnotation extends DocumentAnnotation {
  agent: AgentKey;
}

export interface WorkspaceData {
  heading: string;
  reportLines: string[];
  wordCount: number;
  highRiskCount: number;
  mediumRiskCount: number;
  statusText: string;

  // 统一卡片系统
  allCards: UnifiedCard[];

  // 按 Agent 分组（向后兼容）
  owlCards: RiskCardViewModel[];
  dogCards: ReferenceCardViewModel[];
  beaverCards: CostCardViewModel[];

  documentLines: string[];
  annotationsByAgent: Record<AgentKey, DocumentAnnotation[]>;
}

export const AGENT_META: AgentMeta[] = [
  {
    key: 'owl',
    emoji: '🦉',
    name: '猫头鹰解析师',
    role: '条款拆解与风险识别',
    colorClass: 'bg-accent',
  },
  {
    key: 'dog',
    emoji: '🐶',
    name: '猎犬检索师',
    role: '法律依据与案例线索',
    colorClass: 'bg-primary',
  },
  {
    key: 'beaver',
    emoji: '🦫',
    name: '海狸计算师',
    role: '押金、水电与总成本核算',
    colorClass: 'bg-secondary',
  },
];

export function buildWorkspaceData(
  report: AnalysisReport | null | undefined
): WorkspaceData {
  const markdown = report?.report_markdown?.trim() || '暂无分析报告。';
  const documentText = report?.contract_text?.trim() || '';
  const documentLines = splitDocumentLines(documentText);
  const normalizedCalculations = normalizeCalculations(report?.calculations);

  const annotationsByAgent: Record<AgentKey, DocumentAnnotation[]> = {
    owl: buildOwlAnnotations(documentLines, report?.risk_items ?? []),
    dog: buildDogAnnotations(
      documentLines,
      report?.risk_items ?? [],
      report?.legal_references ?? []
    ),
    beaver: buildBeaverAnnotations(documentLines, normalizedCalculations),
  };

  // 使用统一卡片系统
  const allCards = convertAllCards(report, annotationsByAgent);

  // 按 Agent 分组（向后兼容）
  const owlCards = allCards
    .filter((c) => c.agent === 'owl')
    .map((c) => ({
      title: c.title,
      body: c.body,
      badge: c.badge,
      legalBasis: c.metadata.legalBasis,
      suggestion: c.metadata.suggestion,
      lineIndex: c.lineIndex,
    }));

  const dogCards = allCards
    .filter((c) => c.agent === 'dog')
    .map((c) => ({
      title: c.title,
      body: c.body,
      note: c.metadata.footnote || '',
      lineIndex: c.lineIndex,
    }));

  const beaverCards = allCards
    .filter((c) => c.agent === 'beaver')
    .map((c) => ({
      title: c.title,
      body: c.body,
      badge: c.badge,
      footnote: c.metadata.footnote || '',
      lineIndex: c.lineIndex,
    }));

  return {
    heading:
      report?.is_template || markdown.includes('模板')
        ? '合同模板风险分析'
        : '合同分析报告',
    reportLines: splitReportLines(markdown),
    wordCount: markdown.replace(/\s+/g, '').length,
    highRiskCount: allCards.filter((c) => c.badge === 'high').length,
    mediumRiskCount: allCards.filter((c) => c.badge === 'medium').length,
    statusText: report ? '已加载真实分析结果' : '等待新的分析结果',

    allCards,
    owlCards,
    dogCards,
    beaverCards,

    documentLines,
    annotationsByAgent,
  };
}

export function mergeAnnotationsForExport(
  annotationsByAgent: Record<AgentKey, DocumentAnnotation[]>
): ExportDocumentAnnotation[] {
  return (Object.entries(annotationsByAgent) as Array<[AgentKey, DocumentAnnotation[]]>)
    .flatMap(([agent, annotations]) =>
      annotations.map((annotation) => ({
        ...annotation,
        agent,
      }))
    )
    .sort((left, right) => {
      if (left.lineIndex !== right.lineIndex) {
        return left.lineIndex - right.lineIndex;
      }

      const agentOrder = AGENT_META.findIndex((item) => item.key === left.agent) -
        AGENT_META.findIndex((item) => item.key === right.agent);
      if (agentOrder !== 0) {
        return agentOrder;
      }

      return left.title.localeCompare(right.title, 'zh-CN');
    });
}

function splitReportLines(markdown: string): string[] {
  const lines = markdown.split(/\r?\n/);
  return lines.length > 0 ? lines : ['暂无分析报告。'];
}

function splitDocumentLines(text: string): string[] {
  if (!text) {
    return ['暂无原文内容。'];
  }

  return text.split(/\r?\n/).filter((line, index, lines) => {
    if (line.trim()) {
      return true;
    }
    const prev = lines[index - 1];
    return Boolean(prev?.trim());
  });
}

function toRiskCard(
  item: RiskItem,
  annotation?: DocumentAnnotation
): RiskCardViewModel {
  return {
    title: item.issue,
    body: item.clause,
    badge: item.risk_level,
    legalBasis: item.legal_basis,
    suggestion: item.suggestion,
    lineIndex: annotation?.lineIndex,
  };
}

function toReferenceCard(
  item: LegalReference,
  annotation?: DocumentAnnotation
): ReferenceCardViewModel {
  return {
    title: item.title,
    body: item.content,
    note: item.application || item.relevance || '已纳入报告参考',
    lineIndex: annotation?.lineIndex,
  };
}

function buildCostCards(
  calculations: AnalysisReport['calculations'] | undefined,
  annotations: DocumentAnnotation[] = []
): CostCardViewModel[] {
  if (!calculations) {
    return [];
  }

  const cards: CostCardViewModel[] = [];
  const depositCheck = calculations.deposit_check;
  cards.push({
    title: '押金合规检查',
    body: depositCheck.compliant
      ? `押金 ${depositCheck.amount} 元，未超过法定上限 ${depositCheck.legal_limit} 元。`
      : depositCheck.issue || '押金存在合规风险。',
    badge: depositCheck.compliant ? 'low' : 'high',
    footnote:
      depositCheck.suggestion || `法定上限：${depositCheck.legal_limit} 元`,
    lineIndex: annotations[0]?.lineIndex,
  });

  pushUtilityCard(cards, '水费检查', calculations.utilities_check.water, annotations[1]);
  pushUtilityCard(
    cards,
    '电费检查',
    calculations.utilities_check.electricity,
    annotations[2]
  );
  pushUtilityCard(cards, '燃气费检查', calculations.utilities_check.gas, annotations[3]);

  cards.push({
    title: '总成本估算',
    body: `月度总成本约 ${calculations.total_cost_analysis.monthly_total} 元，年度总成本约 ${calculations.total_cost_analysis.yearly_total} 元。`,
    badge: 'low',
    footnote: calculations.total_cost_analysis.market_comparison,
    lineIndex: annotations[4]?.lineIndex,
  });

  return cards;
}

function normalizeCalculations(
  calculations: AnalysisReport['calculations'] | undefined
): AnalysisReport['calculations'] | undefined {
  if (!calculations) {
    return undefined;
  }

  if (
    !calculations.deposit_check ||
    !calculations.utilities_check ||
    !calculations.total_cost_analysis ||
    !calculations.utilities_check.water ||
    !calculations.utilities_check.electricity ||
    !calculations.utilities_check.gas
  ) {
    return undefined;
  }

  return calculations;
}

function pushUtilityCard(
  cards: CostCardViewModel[],
  title: string,
  utility: UtilityCheck,
  annotation?: DocumentAnnotation
) {
  cards.push({
    title,
    body: utility.overcharged
      ? utility.issue || `${title}存在加价风险。`
      : `当前单价 ${utility.charged}，官方参考 ${utility.official}。`,
    badge: utility.overcharged ? 'medium' : 'low',
    footnote:
      utility.suggestion || `加价幅度：${utility.overcharge_rate}%`,
    lineIndex: annotation?.lineIndex,
  });
}

function buildOwlAnnotations(
  documentLines: string[],
  riskItems: RiskItem[]
): DocumentAnnotation[] {
  return buildAnnotations(documentLines, riskItems, (item) => ({
    level: item.risk_level,
    title: item.issue,
    note: item.suggestion || item.legal_basis,
    keywords: [item.clause, item.issue],
  }));
}

function buildDogAnnotations(
  documentLines: string[],
  riskItems: RiskItem[],
  legalReferences: LegalReference[]
): DocumentAnnotation[] {
  return buildAnnotations(documentLines, riskItems, (item, index) => ({
    level: item.risk_level,
    title: `法律依据 ${index + 1}`,
    note:
      legalReferences[index]?.title ||
      legalReferences[index]?.application ||
      item.legal_basis,
    keywords: [item.clause, item.issue],
  }));
}

function buildBeaverAnnotations(
  documentLines: string[],
  calculations: AnalysisReport['calculations'] | undefined
): DocumentAnnotation[] {
  if (!calculations) {
    return [];
  }

  const cards = buildCostCards(calculations);
  const annotationSources = [
    { card: cards[0], keywords: ['押金', '保证金'] },
    { card: cards[1], keywords: ['水费', '水价'] },
    { card: cards[2], keywords: ['电费', '电价'] },
    { card: cards[3], keywords: ['燃气', '燃气费'] },
    { card: cards[4], keywords: ['押金', '水费', '电费', '燃气费'] },
  ].filter((item) => Boolean(item.card));

  return annotationSources.flatMap(({ card, keywords }) =>
    buildAnnotations(documentLines, [{ clause: keywords.join(' '), issue: card.title, legal_basis: '', suggestion: card.footnote, risk_level: card.badge } as RiskItem], () => ({
      level: card.badge,
      title: card.title,
      note: card.footnote,
      keywords,
    }))
  );
}

function buildAnnotations(
  documentLines: string[],
  sourceItems: RiskItem[],
  mapper: (
    item: RiskItem,
    index: number
  ) => {
    level: 'high' | 'medium' | 'low';
    title: string;
    note: string;
    keywords: Array<string | undefined>;
  }
): DocumentAnnotation[] {
  const annotations: DocumentAnnotation[] = [];

  sourceItems.forEach((item, index) => {
    const mapped = mapper(item, index);
    const lineIndex = findBestLineIndex(documentLines, mapped.keywords);
    if (lineIndex === -1) {
      return;
    }

    annotations.push({
      lineIndex,
      level: mapped.level,
      title: mapped.title,
      note: mapped.note,
    });
  });

  return dedupeAnnotations(annotations);
}

function findBestLineIndex(
  documentLines: string[],
  rawKeywords: Array<string | undefined>
): number {
  const keywords = rawKeywords
    .flatMap((value) => tokenize(value || ''))
    .filter((token) => token.length >= 2);

  let bestIndex = -1;
  let bestScore = 0;

  documentLines.forEach((line, index) => {
    const normalizedLine = normalizeText(line);
    if (!normalizedLine) {
      return;
    }

    const score = keywords.reduce((total, keyword) => {
      return total + (normalizedLine.includes(keyword) ? 1 : 0);
    }, 0);

    if (score > bestScore) {
      bestScore = score;
      bestIndex = index;
    }
  });

  return bestScore > 0 ? bestIndex : -1;
}

function tokenize(text: string): string[] {
  const normalized = normalizeText(text);
  if (!normalized) {
    return [];
  }

  return normalized
    .split(/[\s，。、《》；：、“”"（）()、,.!?]+/)
    .filter(Boolean);
}

function normalizeText(text: string): string {
  return text.replace(/\s+/g, '').toLowerCase();
}

function dedupeAnnotations(annotations: DocumentAnnotation[]): DocumentAnnotation[] {
  const seen = new Set<string>();
  return annotations.filter((item) => {
    const key = `${item.lineIndex}-${item.title}-${item.note}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function getRiskTone(level: 'high' | 'medium' | 'low') {
  if (level === 'high') {
    return {
      stripe: 'bg-accent',
      badge: 'bg-accent text-white',
      label: '高风险',
      highlight: 'bg-accent/20 border-b-4 border-accent text-accent',
    };
  }

  if (level === 'medium') {
    return {
      stripe: 'bg-secondary',
      badge: 'bg-secondary text-ink',
      label: '中风险',
      highlight: 'bg-secondary/30 border-b-4 border-secondary text-ink',
    };
  }

  return {
    stripe: 'bg-primary',
    badge: 'bg-primary text-ink',
    label: '提示',
    highlight: 'bg-primary/20 border-b-4 border-primary text-ink',
  };
}
