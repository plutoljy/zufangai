import type {
  RiskItem,
  LegalReference,
  CaseReference,
  Suggestion,
  NegotiationTip,
  HiddenCost,
  ImplicitValues,
  AnalysisReport,
} from '../services/api.ts';

export interface UnifiedCard {
  id: string;
  agent: 'owl' | 'dog' | 'beaver';
  category: string;
  title: string;
  body: string;
  badge: 'high' | 'medium' | 'low';
  metadata: {
    footnote?: string;
    legalBasis?: string;
    suggestion?: string;
    source?: string;
    confidence?: string;
    amount?: number;
    [key: string]: any;
  };
  lineIndex?: number;
}

type CardAnnotation = {
  lineIndex?: number;
};

export interface CardAnnotationGroups {
  owl?: CardAnnotation[];
  dog?: CardAnnotation[];
  beaver?: CardAnnotation[];
}

// === OWL CARDS ===
export function convertOwlCards(
  riskItems: RiskItem[],
  annotations: any[] = []
): UnifiedCard[] {
  return riskItems.map((item, index) => ({
    id: `owl-risk-${index}`,
    agent: 'owl',
    category: 'risk',
    title: item.issue,
    body: item.clause,
    badge: item.risk_level,
    metadata: {
      legalBasis: item.legal_basis,
      suggestion: item.suggestion,
    },
    lineIndex: annotations[index]?.lineIndex,
  }));
}

// === DOG CARDS ===
export function convertDogCards(
  report: AnalysisReport,
  annotations: any[] = []
): UnifiedCard[] {
  const cards: UnifiedCard[] = [];
  let annotationIndex = 0;

  // 1. Legal References
  report.legal_references?.forEach((ref, index) => {
    cards.push({
      id: `dog-legal-${index}`,
      agent: 'dog',
      category: 'legal',
      title: ref.title,
      body: ref.content,
      badge: 'low',
      metadata: {
        footnote: ref.application || ref.relevance,
        lawId: ref.law_id,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  // 2. Case References
  report.case_references?.forEach((caseRef, index) => {
    // 兼容 content 和 summary 字段
    const caseBody = caseRef.summary || caseRef.content || '';

    cards.push({
      id: `dog-case-${index}`,
      agent: 'dog',
      category: 'case',
      title: `案例: ${caseRef.title}`,
      body: caseBody,
      badge: 'low',
      metadata: {
        footnote: caseRef.relevance,
        caseId: caseRef.case_id,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  // 3. Suggestions
  report.suggestions?.forEach((sug, index) => {
    // 兼容字符串和对象两种格式
    let category = '建议';
    let content = '';
    let priority: 'high' | 'medium' | 'low' = 'medium';

    if (typeof sug === 'string') {
      // 字符串格式
      content = sug;
    } else if (typeof sug === 'object') {
      // 对象格式
      category = sug.category || '建议';
      content = sug.content || '';
      priority = sug.priority || 'medium';
    }

    if (!content) return; // 跳过空内容

    const normalizedCategory = category.trim() || '建议';
    const title =
      normalizedCategory === '建议'
        ? `建议 ${index + 1}`
        : `建议: ${normalizedCategory}`;

    cards.push({
      id: `dog-suggestion-${index}`,
      agent: 'dog',
      category: 'suggestion',
      title,
      body: content,
      badge: priority,
      metadata: {
        category: normalizedCategory,
        footnote: content,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  // 4. Negotiation Tips
  report.negotiation_tips?.forEach((tip, index) => {
    // 兼容新旧字段格式
    const scenario = tip.issue || tip.scenario || '谈判场景';
    const tipContent = tip.strategy || tip.tip || '';
    const example = tip.script || tip.example;

    cards.push({
      id: `dog-tip-${index}`,
      agent: 'dog',
      category: 'negotiation',
      title: `谈判技巧: ${scenario}`,
      body: tipContent,
      badge: 'low',
      metadata: {
        footnote: tipContent,
        example: example,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  return cards;
}

// === BEAVER CARDS ===
export function convertBeaverCards(
  calculations: AnalysisReport['calculations'] | undefined,
  annotations: any[] = []
): UnifiedCard[] {
  const cards: UnifiedCard[] = [];
  let annotationIndex = 0;

  if (!calculations) return cards;

  // 1. Deposit Check
  const dc = calculations.deposit_check;
  if (dc) {
    cards.push({
      id: 'beaver-deposit',
      agent: 'beaver',
      category: 'compliance',
      title: '押金合规检查',
      body: dc.compliant
        ? `押金 ${dc.amount} 元，未超过法定上限 ${dc.legal_limit} 元。`
        : dc.issue || '押金存在合规风险。',
      badge: dc.compliant ? 'low' : 'high',
      metadata: {
        footnote: dc.suggestion || `法定上限：${dc.legal_limit} 元`,
        amount: dc.amount,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  }

  // 2-4. Utilities Check
  const uc = calculations.utilities_check;
  if (uc) {
    const utilityNames = [
      { key: 'water', label: '水费' },
      { key: 'electricity', label: '电费' },
      { key: 'gas', label: '燃气费' },
    ];

    utilityNames.forEach(({ key, label }) => {
      const util = uc[key as keyof typeof uc];
      if (util) {
        cards.push({
          id: `beaver-${key}`,
          agent: 'beaver',
          category: 'utility',
          title: `${label}检查`,
          body: util.overcharged
            ? util.issue || `${label}存在加价风险。`
            : `当前单价 ${util.charged}，官方参考 ${util.official}。`,
          badge: util.overcharged ? 'medium' : 'low',
          metadata: {
            footnote: util.suggestion || `加价幅度：${util.overcharge_rate}%`,
            charged: util.charged,
            official: util.official,
          },
          lineIndex: annotations[annotationIndex++]?.lineIndex,
        });
      }
    });
  }

  // 5. Total Cost
  const tca = calculations.total_cost_analysis;
  if (tca) {
    cards.push({
      id: 'beaver-total-cost',
      agent: 'beaver',
      category: 'cost',
      title: '总成本估算',
      body: `月度总成本约 ${tca.monthly_total} 元，年度总成本约 ${tca.yearly_total} 元。`,
      badge: 'low',
      metadata: {
        footnote: tca.market_comparison,
        monthlyTotal: tca.monthly_total,
        yearlyTotal: tca.yearly_total,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  }

  // 6-N. Hidden Costs
  calculations.hidden_costs?.forEach((cost, index) => {
    cards.push({
      id: `beaver-hidden-${index}`,
      agent: 'beaver',
      category: 'hidden-cost',
      title: `隐藏费用 ${index + 1}`,
      body: cost.description,
      badge: cost.risk_level,
      metadata: {
        footnote: cost.amount ? `金额: ${cost.amount}元` : '金额未知',
        amount: cost.amount,
        inference: cost.inference,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  // N+1-M. Ambiguous Clauses
  calculations.ambiguous_clauses?.items?.forEach((clause, index) => {
    cards.push({
      id: `beaver-ambiguous-${index}`,
      agent: 'beaver',
      category: 'ambiguous',
      title: `模糊条款 ${index + 1}`,
      body: clause.clause,
      badge: 'medium',
      metadata: {
        footnote: clause.issue,
        inference: clause.inference,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  // M+1. First Payment (v3)
  const iv = calculations.implicit_values;
  if (iv?.first_payment) {
    const fp = iv.first_payment;
    cards.push({
      id: 'beaver-first-payment',
      agent: 'beaver',
      category: 'inference',
      title: '首期支付推断',
      body: `${fp.calculation}`,
      badge: 'low',
      metadata: {
        footnote: `来源: ${fp.source}`,
        amount: fp.amount,
        source: fp.source,
        confidence: fp.confidence,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  }

  // M+2-N. Penalty Scenarios (v3)
  iv?.penalty_scenarios?.forEach((scenario, index) => {
    cards.push({
      id: `beaver-penalty-${index}`,
      agent: 'beaver',
      category: 'inference',
      title: `违约成本 ${index + 1}`,
      body: `${scenario.timing}: 损失 ${scenario.loss_amount} 元`,
      badge: 'medium',
      metadata: {
        footnote: scenario.calculation,
        amount: scenario.loss_amount,
        source: scenario.source,
        confidence: scenario.confidence,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  // N+1-P. Hidden Fee Risks (v3)
  iv?.hidden_fee_risks?.forEach((risk, index) => {
    cards.push({
      id: `beaver-fee-risk-${index}`,
      agent: 'beaver',
      category: 'inference',
      title: `隐藏费用风险 ${index + 1}`,
      body: risk.description,
      badge: 'medium',
      metadata: {
        footnote: `来源: ${risk.source}`,
        amount: risk.estimated_amount,
        source: risk.source,
        confidence: risk.confidence,
      },
      lineIndex: annotations[annotationIndex++]?.lineIndex,
    });
  });

  return cards;
}

// === 统一转换函数 ===
export function convertAllCards(
  report: AnalysisReport | null | undefined,
  annotations: CardAnnotationGroups = {}
): UnifiedCard[] {
  if (!report) {
    console.warn('[cardConverters] 报告为空');
    return [];
  }

  console.log('[cardConverters] 开始转换卡片:', {
    riskItems: report.risk_items?.length ?? 0,
    legalRefs: report.legal_references?.length ?? 0,
    caseRefs: report.case_references?.length ?? 0,
    suggestions: report.suggestions?.length ?? 0,
    negotiationTips: report.negotiation_tips?.length ?? 0,
    calculations: !!report.calculations,
  });

  const owlCards = convertOwlCards(report.risk_items || [], annotations.owl ?? []);
  const dogCards = convertDogCards(report, annotations.dog ?? []);
  const beaverCards = convertBeaverCards(
    report.calculations,
    annotations.beaver ?? []
  );

  console.log('[cardConverters] 卡片转换完成:', {
    owlCards: owlCards.length,
    dogCards: dogCards.length,
    beaverCards: beaverCards.length,
    total: owlCards.length + dogCards.length + beaverCards.length,
  });

  return [...owlCards, ...dogCards, ...beaverCards];
}
