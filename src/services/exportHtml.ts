import type { AnalysisReport, RiskItem, UtilityCheck } from './api.ts';
import {
  AGENT_META,
  buildWorkspaceData,
  mergeAnnotationsForExport,
  type AgentKey,
  type ExportDocumentAnnotation,
} from '../components/workspaceData.ts';

type ExportOptions = {
  report: AnalysisReport;
  fileName?: string | null;
  location?: string | null;
};

type Severity = 'high' | 'medium' | 'low';

const SEVERITY_META: Record<
  Severity,
  { label: string; accent: string; soft: string; border: string }
> = {
  high: {
    label: '高风险',
    accent: '#FF6B6B',
    soft: '#FFF1F1',
    border: '#FFC2C2',
  },
  medium: {
    label: '提示',
    accent: '#F4C95D',
    soft: '#FFF8DE',
    border: '#F2D680',
  },
  low: {
    label: '稳妥',
    accent: '#4ECDC4',
    soft: '#E9FFFC',
    border: '#9BE7E0',
  },
};

export function buildCleanReportHtml(options: ExportOptions): string {
  const { report, fileName, location } = options;
  const workspace = buildWorkspaceData(report);
  const exportTime = formatTimestamp(new Date());
  const highRisks = report.risk_items.filter((item) => item.risk_level === 'high');

  const summaryCards = [
    statCard('总风险数', String(report.summary.total_risks ?? report.risk_items.length)),
    statCard('高风险', String(report.summary.high_risks ?? highRisks.length)),
    statCard('法条依据', String(report.legal_references.length)),
    statCard('案例参考', String(report.case_references.length)),
  ].join('');

  const riskCards = renderRiskCards(report.risk_items);
  const lawCards = renderReferenceCards(
    report.legal_references.map((item) => ({
      title: item.title,
      body: item.content,
      footnote: item.application || item.relevance,
    })),
    '暂无法律条文依据。'
  );
  const caseCards = renderReferenceCards(
    report.case_references.map((item) => ({
      title: item.title,
      body: item.summary || item.content || '',
      footnote: item.relevance,
    })),
    '暂无案例参考。'
  );

  const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(buildCleanFileName(fileName, report, false))}</title>
  <style>${baseStyles()}</style>
</head>
<body class="clean">
  <main class="page">
    <header class="hero">
      <div class="hero-badge">租房避坑局 · 清洁版报告</div>
      <h1>${escapeHtml(stripExtension(fileName || '合同分析报告'))}</h1>
      <p class="hero-copy">这是一份适合直接阅读、转发和打印的合同风险说明报告，突出风险结论、法律依据和费用核算结果。</p>
      <dl class="meta-grid">
        ${metaItem('导出时间', exportTime)}
        ${metaItem('合同文件', fileName || `合同 ${report.contract_id}`)}
        ${metaItem('定位城市', location || '未设置')}
        ${metaItem('合同地址', report.entities.property_address || '未识别')}
      </dl>
    </header>

    <section class="section">
      <div class="section-title">风险总览</div>
      <div class="stats-grid">${summaryCards}</div>
    </section>

    <section class="section">
      <div class="section-title">合同概况</div>
      <div class="overview-grid">
        ${overviewCard('出租方', report.entities.lessor || '未识别')}
        ${overviewCard('承租方', report.entities.lessee || '未识别')}
        ${overviewCard('月租金', formatCurrency(report.entities.monthly_rent))}
        ${overviewCard('押金', formatCurrency(report.entities.deposit))}
        ${overviewCard('租期', report.entities.lease_term || '未识别')}
        ${overviewCard(
          '时间范围',
          [report.entities.start_date, report.entities.end_date].filter(Boolean).join(' 至 ') || '未识别'
        )}
      </div>
    </section>

    <section class="section">
      <div class="section-title">高风险与重点风险</div>
      <div class="stack">${riskCards}</div>
    </section>

    <section class="section two-column">
      <div>
        <div class="section-title">法律条文依据</div>
        <div class="stack">${lawCards}</div>
      </div>
      <div>
        <div class="section-title">案例参考</div>
        <div class="stack">${caseCards}</div>
      </div>
    </section>

    <section class="section">
      <div class="section-title">费用核算结论</div>
      ${renderCalculationSummary(report)}
    </section>

    <section class="section">
      <div class="section-title">完整说明</div>
      <div class="markdown-report">
        ${renderMarkdownLikeReport(workspace.reportLines)}
      </div>
    </section>
  </main>
</body>
</html>`;

  return html;
}

export function buildAnnotatedContractHtml(options: ExportOptions): string {
  const { report, fileName, location } = options;
  const workspace = buildWorkspaceData(report);
  const mergedAnnotations = mergeAnnotationsForExport(workspace.annotationsByAgent);
  const annotationsByLine = groupAnnotationsByLine(mergedAnnotations);

  const documentRows = workspace.documentLines
    .map((line, index) => renderDocumentRow(line, index, annotationsByLine.get(index) ?? []))
    .join('');

  const legend = AGENT_META.map(
    (agent) =>
      `<span class="legend-chip legend-${agent.key}">${escapeHtml(agent.name)}</span>`
  ).join('');

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(buildCleanFileName(fileName, report, true))}</title>
  <style>${baseStyles()}</style>
</head>
<body class="annotated">
  <main class="page wide">
    <header class="hero">
      <div class="hero-badge">租房避坑局 · 标注版合同</div>
      <h1>${escapeHtml(stripExtension(fileName || '合同标注版'))}</h1>
      <p class="hero-copy">本文件将 Owl、Dog、Beaver 的风险识别、法律依据和费用核算标注合并到同一份合同原文中，便于逐条对照。</p>
      <dl class="meta-grid">
        ${metaItem('导出时间', formatTimestamp(new Date()))}
        ${metaItem('合同文件', fileName || `合同 ${report.contract_id}`)}
        ${metaItem('定位城市', location || '未设置')}
        ${metaItem('总标注数', String(mergedAnnotations.length))}
      </dl>
      <div class="legend-row">${legend}</div>
    </header>

    <section class="section">
      <div class="section-title">原文与合并标注</div>
      <div class="document-stack">${documentRows}</div>
    </section>
  </main>
</body>
</html>`;
}

export function downloadCleanReportHtml(options: ExportOptions): void {
  downloadHtmlDocument(buildCleanFileName(options.fileName, options.report, false), buildCleanReportHtml(options));
}

export function downloadAnnotatedContractHtml(options: ExportOptions): void {
  downloadHtmlDocument(buildCleanFileName(options.fileName, options.report, true), buildAnnotatedContractHtml(options));
}

function buildCleanFileName(
  fileName: string | null | undefined,
  report: AnalysisReport,
  annotated: boolean
): string {
  const base = sanitizeFileName(stripExtension(fileName || `contract-${report.contract_id}`));
  return `${base}${annotated ? '-标注版合同' : '-清洁版报告'}.html`;
}

function downloadHtmlDocument(fileName: string, html: string): void {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function renderRiskCards(riskItems: RiskItem[]): string {
  if (riskItems.length === 0) {
    return emptyState('当前报告没有识别到需要展示的风险条目。');
  }

  return riskItems
    .map((item, index) => {
      const severity = SEVERITY_META[item.risk_level];
      return `<article class="card risk-card" style="--card-accent:${severity.accent};--card-soft:${severity.soft};--card-border:${severity.border}">
        <div class="card-header">
          <div class="card-index">风险 ${index + 1}</div>
          <div class="severity">${severity.label}</div>
        </div>
        <h3>${escapeHtml(item.issue)}</h3>
        <p class="body">${escapeHtml(item.clause)}</p>
        <div class="detail-block">
          <div class="detail-title">法律依据</div>
          <p>${escapeHtml(item.legal_basis || '暂无')}</p>
        </div>
        <div class="detail-block">
          <div class="detail-title">建议</div>
          <p>${escapeHtml(item.suggestion || '暂无')}</p>
        </div>
      </article>`;
    })
    .join('');
}

function renderReferenceCards(
  items: Array<{ title: string; body: string; footnote?: string }>,
  emptyText: string
): string {
  if (items.length === 0) {
    return emptyState(emptyText);
  }

  return items
    .map(
      (item) => `<article class="card reference-card">
        <h3>${escapeHtml(item.title)}</h3>
        <p class="body">${escapeHtml(item.body || '暂无')}</p>
        ${
          item.footnote
            ? `<div class="detail-footnote">${escapeHtml(item.footnote)}</div>`
            : ''
        }
      </article>`
    )
    .join('');
}

function renderCalculationSummary(report: AnalysisReport): string {
  const calculations = report.calculations;
  if (!calculations) {
    return emptyState('当前报告没有费用核算结果。');
  }

  const utilityRows = [
    utilitySummary('水费', calculations.utilities_check.water),
    utilitySummary('电费', calculations.utilities_check.electricity),
    utilitySummary('燃气费', calculations.utilities_check.gas),
  ].join('');

  const hiddenCosts = calculations.hidden_costs.length
    ? calculations.hidden_costs
        .map(
          (item) =>
            `<li>${escapeHtml(item.description)}${
              item.amount !== null ? `（${formatCurrency(item.amount)}）` : ''
            }</li>`
        )
        .join('')
    : '<li>未识别到明确的隐藏收费项目。</li>';

  return `<div class="calc-grid">
    <article class="card calc-card">
      <h3>押金合规</h3>
      <p class="body">${
        calculations.deposit_check.compliant
          ? `押金 ${formatCurrency(calculations.deposit_check.amount)}，未超过法定上限 ${formatCurrency(calculations.deposit_check.legal_limit)}。`
          : escapeHtml(calculations.deposit_check.issue || '押金存在合规风险。')
      }</p>
      <div class="detail-footnote">${escapeHtml(
        calculations.deposit_check.suggestion || '建议结合当地押金上限与合同用途再次确认。'
      )}</div>
    </article>
    <article class="card calc-card">
      <h3>水电燃气</h3>
      <table class="utility-table">
        <thead><tr><th>项目</th><th>合同单价</th><th>官方参考</th><th>结论</th></tr></thead>
        <tbody>${utilityRows}</tbody>
      </table>
    </article>
    <article class="card calc-card">
      <h3>总成本估算</h3>
      <p class="body">月度总成本约 ${formatCurrency(
        calculations.total_cost_analysis.monthly_total
      )}，年度总成本约 ${formatCurrency(
        calculations.total_cost_analysis.yearly_total
      )}。</p>
      <div class="detail-footnote">${escapeHtml(
        calculations.total_cost_analysis.market_comparison
      )}</div>
    </article>
    <article class="card calc-card">
      <h3>隐藏费用与模糊条款</h3>
      <ul class="bullet-list">${hiddenCosts}</ul>
    </article>
  </div>`;
}

function utilitySummary(label: string, utility: UtilityCheck): string {
  return `<tr>
    <td>${escapeHtml(label)}</td>
    <td>${escapeHtml(String(utility.charged))}</td>
    <td>${escapeHtml(String(utility.official))}</td>
    <td>${escapeHtml(
      utility.overcharged ? utility.issue || '存在加价风险' : '未发现明显加价'
    )}</td>
  </tr>`;
}

function renderMarkdownLikeReport(lines: string[]): string {
  return lines
    .map((line) => {
      const safe = escapeHtml(line.replace(/^\s+|\s+$/g, ''));
      if (!safe) {
        return '<div class="spacer"></div>';
      }
      if (safe.startsWith('### ')) {
        return `<h3>${safe.replace(/^###\s*/, '')}</h3>`;
      }
      if (safe.startsWith('## ')) {
        return `<h2>${safe.replace(/^##\s*/, '')}</h2>`;
      }
      if (safe.startsWith('# ')) {
        return `<h1>${safe.replace(/^#\s*/, '')}</h1>`;
      }
      if (safe.startsWith('- ')) {
        return `<p class="bullet">• ${safe.replace(/^- /, '')}</p>`;
      }
      if (safe.startsWith('> ')) {
        return `<blockquote>${safe.replace(/^> /, '')}</blockquote>`;
      }
      return `<p>${safe}</p>`;
    })
    .join('');
}

function groupAnnotationsByLine(
  annotations: ExportDocumentAnnotation[]
): Map<number, ExportDocumentAnnotation[]> {
  const grouped = new Map<number, ExportDocumentAnnotation[]>();
  annotations.forEach((annotation) => {
    const current = grouped.get(annotation.lineIndex) ?? [];
    current.push(annotation);
    grouped.set(annotation.lineIndex, current);
  });
  return grouped;
}

function renderDocumentRow(
  line: string,
  index: number,
  annotations: ExportDocumentAnnotation[]
): string {
  const highestSeverity = pickHighestSeverity(annotations);
  const rowClass = highestSeverity ? `line line-${highestSeverity}` : 'line';
  const annotationHtml = annotations
    .map((annotation) => renderAnnotation(annotation))
    .join('');

  return `<article class="${rowClass}">
    <div class="line-main">
      <div class="line-number">${index + 1}</div>
      <div class="line-text">${escapeHtml(line)}</div>
    </div>
    ${
      annotations.length
        ? `<div class="annotation-stack">${annotationHtml}</div>`
        : ''
    }
  </article>`;
}

function renderAnnotation(annotation: ExportDocumentAnnotation): string {
  const severity = SEVERITY_META[annotation.level];
  const agent = AGENT_META.find((item) => item.key === annotation.agent);
  return `<div class="annotation-card" style="--annotation-accent:${severity.accent};--annotation-soft:${severity.soft};--annotation-border:${severity.border}">
    <div class="annotation-header">
      <span class="legend-chip legend-${annotation.agent}">${escapeHtml(
        agent?.name || annotation.agent
      )}</span>
      <span class="severity severity-inline">${severity.label}</span>
    </div>
    <div class="annotation-title">${escapeHtml(annotation.title)}</div>
    <p class="annotation-note">${escapeHtml(annotation.note)}</p>
  </div>`;
}

function pickHighestSeverity(
  annotations: ExportDocumentAnnotation[]
): Severity | null {
  if (annotations.some((item) => item.level === 'high')) {
    return 'high';
  }
  if (annotations.some((item) => item.level === 'medium')) {
    return 'medium';
  }
  if (annotations.some((item) => item.level === 'low')) {
    return 'low';
  }
  return null;
}

function statCard(label: string, value: string): string {
  return `<article class="stat-card">
    <div class="stat-label">${escapeHtml(label)}</div>
    <div class="stat-value">${escapeHtml(value)}</div>
  </article>`;
}

function overviewCard(label: string, value: string): string {
  return `<article class="overview-card">
    <div class="overview-label">${escapeHtml(label)}</div>
    <div class="overview-value">${escapeHtml(value)}</div>
  </article>`;
}

function metaItem(label: string, value: string): string {
  return `<div class="meta-item"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`;
}

function emptyState(text: string): string {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function formatCurrency(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '未识别';
  }
  return `${value} 元`;
}

function formatTimestamp(date: Date): string {
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function stripExtension(name: string): string {
  return name.replace(/\.[^.]+$/, '');
}

function sanitizeFileName(name: string): string {
  return name.replace(/[<>:"/\\|?*\u0000-\u001F]/g, '_').trim() || '合同导出';
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function baseStyles(): string {
  const legendStyles = AGENT_META.map(
    (agent) =>
      `.legend-${agent.key}{background:${agent.key === 'owl' ? '#FFE1E1' : agent.key === 'dog' ? '#DDF7F5' : '#FFF0B8'};}`
  ).join('');

  return `
    :root{
      color-scheme: light;
      --ink:#2D3142;
      --paper:#FFF9E8;
      --surface:#FFFCF1;
      --surface-alt:#F6F2E3;
      --primary:#4ECDC4;
      --secondary:#F4C95D;
      --accent:#FF6B6B;
    }
    *{box-sizing:border-box;}
    body{margin:0;background:linear-gradient(180deg,#FFF8E6 0%,#FFFDF5 100%);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC","Helvetica Neue",Arial,sans-serif;}
    .page{max-width:1080px;margin:0 auto;padding:32px 24px 64px;}
    .page.wide{max-width:1240px;}
    .hero{background:var(--surface);border:4px solid var(--ink);border-radius:28px;padding:28px 32px;box-shadow:8px 8px 0 var(--ink);margin-bottom:28px;}
    .hero-badge{display:inline-block;padding:8px 12px;border:2px solid var(--ink);border-radius:999px;background:var(--secondary);font-weight:900;font-size:13px;}
    h1{margin:18px 0 12px;font-size:34px;line-height:1.2;}
    .hero-copy{margin:0 0 18px;color:#4D5364;font-size:15px;line-height:1.7;}
    .meta-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:0;}
    .meta-item{background:var(--paper);border:2px solid var(--ink);border-radius:18px;padding:12px 14px;}
    .meta-item dt{font-size:12px;font-weight:800;color:#6A7080;margin-bottom:6px;}
    .meta-item dd{margin:0;font-size:14px;font-weight:800;}
    .section{margin-bottom:24px;}
    .section-title{font-size:22px;font-weight:900;margin-bottom:14px;}
    .stats-grid,.overview-grid,.calc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;}
    .stat-card,.overview-card,.card,.line{background:var(--surface);border:3px solid var(--ink);border-radius:22px;box-shadow:5px 5px 0 var(--ink);}
    .stat-card{padding:18px 20px;}
    .stat-label{font-size:13px;font-weight:800;color:#6A7080;}
    .stat-value{font-size:28px;font-weight:900;margin-top:10px;}
    .overview-card{padding:16px 18px;}
    .overview-label{font-size:12px;font-weight:800;color:#6A7080;margin-bottom:8px;}
    .overview-value{font-size:16px;font-weight:900;line-height:1.5;}
    .stack{display:flex;flex-direction:column;gap:14px;}
    .two-column{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;}
    .card{padding:18px 20px;}
    .card h3{margin:0 0 10px;font-size:18px;}
    .card .body{margin:0 0 12px;line-height:1.8;color:#4D5364;}
    .card-header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;}
    .card-index,.severity,.legend-chip{display:inline-flex;align-items:center;padding:6px 10px;border:2px solid var(--ink);border-radius:999px;font-size:12px;font-weight:900;}
    .severity{background:var(--card-soft,#FFF8DE);}
    .detail-block{border-top:1px dashed #B6AF95;padding-top:12px;margin-top:12px;}
    .detail-title{font-size:12px;font-weight:900;color:#6A7080;margin-bottom:6px;}
    .detail-footnote{font-size:13px;font-weight:800;color:#5F6777;line-height:1.7;}
    .calc-card{min-height:100%;}
    .utility-table{width:100%;border-collapse:collapse;font-size:13px;}
    .utility-table th,.utility-table td{border-bottom:1px solid #D8D2BF;padding:8px 6px;text-align:left;vertical-align:top;}
    .utility-table th{font-weight:900;}
    .bullet-list{margin:0;padding-left:20px;line-height:1.8;color:#4D5364;}
    .markdown-report{background:var(--surface);border:3px solid var(--ink);border-radius:22px;padding:22px 24px;box-shadow:5px 5px 0 var(--ink);}
    .markdown-report h1,.markdown-report h2,.markdown-report h3{margin-top:1.2em;margin-bottom:.6em;}
    .markdown-report p,.markdown-report blockquote{margin:.5em 0;line-height:1.85;}
    .markdown-report .bullet{padding-left:12px;}
    .markdown-report blockquote{padding-left:14px;border-left:4px solid var(--secondary);color:#5D6474;}
    .spacer{height:10px;}
    .legend-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px;}
    ${legendStyles}
    .document-stack{display:flex;flex-direction:column;gap:16px;}
    .line{padding:16px 18px;}
    .line-high{background:#FFF3F3;}
    .line-medium{background:#FFFBE9;}
    .line-low{background:#F1FFFD;}
    .line-main{display:grid;grid-template-columns:56px 1fr;gap:14px;align-items:start;}
    .line-number{font-size:12px;font-weight:900;color:#6A7080;text-align:center;padding-top:2px;}
    .line-text{font-size:15px;font-weight:800;line-height:1.9;white-space:pre-wrap;}
    .annotation-stack{display:flex;flex-direction:column;gap:10px;margin-top:14px;margin-left:70px;}
    .annotation-card{background:var(--annotation-soft,#FFF8DE);border:2px solid var(--annotation-border,#F2D680);border-radius:18px;padding:12px 14px;}
    .annotation-header{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;}
    .annotation-title{font-size:14px;font-weight:900;margin-bottom:6px;}
    .annotation-note{margin:0;font-size:13px;font-weight:800;line-height:1.75;color:#4D5364;}
    .empty-state{background:var(--surface);border:2px dashed #B6AF95;border-radius:18px;padding:18px 20px;color:#5F6777;font-weight:800;}
    @media (max-width: 860px){
      .page,.page.wide{padding:20px 14px 48px;}
      .hero{padding:22px 18px;}
      .two-column{grid-template-columns:1fr;}
      .line-main{grid-template-columns:42px 1fr;}
      .annotation-stack{margin-left:0;}
    }
    @media print{
      body{background:#fff;}
      .page,.page.wide{max-width:none;padding:0;}
      .hero,.stat-card,.overview-card,.card,.line,.markdown-report{box-shadow:none;}
    }
  `;
}
