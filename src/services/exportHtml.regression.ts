import assert from 'node:assert/strict';

import type { AnalysisReport } from './api.ts';
import {
  buildAnnotatedContractHtml,
  buildCleanReportHtml,
} from './exportHtml.ts';

const sampleReport: AnalysisReport = {
  contract_id: 'contract-123',
  contract_text: [
    '第一条 房屋租金为每月 5000 元。',
    '第二条 水费按 8.5 元/立方米收取。',
    '第三条 提前退租需支付剩余租期全部租金。',
  ].join('\n'),
  entities: {
    lessor: '张房东',
    lessee: '李同学',
    monthly_rent: 5000,
    deposit: 5000,
    lease_term: '12个月',
    property_address: '北京市海淀区测试路 1 号',
    start_date: '2026-05-01',
    end_date: '2027-04-30',
    utilities: {
      water: 8.5,
      electricity: 0.56,
      gas: 3.2,
    },
  },
  risk_items: [
    {
      clause: '提前退租需支付剩余租期全部租金。',
      risk_level: 'high',
      issue: '提前退租赔付过高<script>',
      legal_basis: '民法典关于违约责任应与实际损失相当。',
      suggestion: '建议改为按实际损失承担，不超过两个月租金。',
    },
  ],
  legal_references: [
    {
      law_id: 'law-1',
      title: '民法典第585条',
      content: '违约金应当与实际损失相当。',
      relevance: '限制过高违约责任',
      application: '可用于反驳剩余租期全额赔付。',
    },
  ],
  case_references: [
    {
      case_id: 'case-1',
      title: '北京租赁纠纷案例',
      summary: '法院支持按实际损失核定违约责任。',
      relevance: '支持缩减过高赔偿。',
    },
  ],
  suggestions: [],
  negotiation_tips: [],
  calculations: {
    deposit_check: {
      amount: 5000,
      legal_limit: 5000,
      compliant: true,
      overcharge_amount: 0,
      issue: null,
      suggestion: '押金金额与月租持平。',
    },
    utilities_check: {
      water: {
        charged: 8.5,
        official: 5,
        overcharge_rate: 70,
        overcharged: true,
        issue: '水费明显高于官方参考价。',
        suggestion: '建议要求按官方指导价或出示定价依据。',
      },
      electricity: {
        charged: 0.56,
        official: 0.56,
        overcharge_rate: 0,
        overcharged: false,
        issue: null,
        suggestion: null,
      },
      gas: {
        charged: 3.2,
        official: 3.2,
        overcharge_rate: 0,
        overcharged: false,
        issue: null,
        suggestion: null,
      },
    },
    hidden_costs: [
      {
        description: '保洁服务费',
        amount: 300,
        risk_level: 'medium',
      },
    ],
    ambiguous_clauses: {
      count: 1,
      items: [
        {
          clause: '其他费用由乙方承担。',
          issue: '费用范围不明确。',
        },
      ],
    },
    explicit_values: {
      monthly_rent: 5000,
      deposit: 5000,
      payment_method: '押一付一',
      water_price: 8.5,
      electricity_price: 0.56,
      gas_price: 3.2,
      lease_term: '12个月',
    },
    implicit_values: {},
    total_cost_analysis: {
      monthly_base: 5000,
      estimated_utilities: 300,
      monthly_total: 5300,
      yearly_total: 63600,
      market_comparison: '整体成本略高于周边平均水平。',
    },
  },
  report_markdown: '# 租房合同分析报告\n\n## 风险警示\n- 提前退租赔付过高\n',
  summary: {
    total_risks: 1,
    high_risks: 1,
    medium_risks: 0,
    low_risks: 0,
    compliant: false,
  },
};

function testCleanExportContainsReadableSummary() {
  const html = buildCleanReportHtml({
    report: sampleReport,
    fileName: '北京个人出租风险合同.docx',
    location: '北京',
  });

  assert.match(html, /租房避坑局 · 清洁版报告/);
  assert.match(html, /风险总览/);
  assert.match(html, /民法典第585条/);
  assert.match(html, /&lt;script&gt;/);
}

function testAnnotatedExportContainsMergedAnnotations() {
  const html = buildAnnotatedContractHtml({
    report: sampleReport,
    fileName: '北京个人出租风险合同.docx',
    location: '北京',
  });

  assert.match(html, /租房避坑局 · 标注版合同/);
  assert.match(html, /第一条 房屋租金为每月 5000 元。/);
  assert.match(html, /legend-owl/);
  assert.match(html, /legend-dog/);
  assert.match(html, /legend-beaver/);
}

testCleanExportContainsReadableSummary();
testAnnotatedExportContainsMergedAnnotations();
