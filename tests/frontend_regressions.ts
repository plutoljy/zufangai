import assert from 'node:assert/strict';

import { buildWorkspaceData } from '../src/components/workspaceData.ts';

type AnalysisReport = Parameters<typeof buildWorkspaceData>[0] extends infer T ? T : never;

function createBaseReport(): NonNullable<AnalysisReport> {
  return {
    contract_id: 'contract-1',
    contract_text: '押一付三，月租金 4980 元。',
    entities: {
      lessor: '甲方',
      lessee: '乙方',
      monthly_rent: 4980,
      deposit: 4980,
      lease_term: '12个月',
      property_address: '上海市浦东新区',
      start_date: null,
      end_date: null,
      utilities: {},
    },
    risk_items: [],
    legal_references: [],
    case_references: [],
    suggestions: [],
    negotiation_tips: [],
    calculations: {
      deposit_check: {
        amount: 4980,
        legal_limit: 4980,
        compliant: true,
        overcharge_amount: 0,
        issue: null,
        suggestion: null,
      },
      utilities_check: {
        water: {
          charged: 0,
          official: 3.45,
          overcharge_rate: 0,
          overcharged: false,
          issue: null,
          suggestion: null,
        },
        electricity: {
          charged: 0,
          official: 0.617,
          overcharge_rate: 0,
          overcharged: false,
          issue: null,
          suggestion: null,
        },
        gas: {
          charged: 0,
          official: 3,
          overcharge_rate: 0,
          overcharged: false,
          issue: null,
          suggestion: null,
        },
      },
      hidden_costs: [],
      ambiguous_clauses: { count: 0, items: [] },
      explicit_values: {
        monthly_rent: 4980,
        deposit: 4980,
        payment_method: '押一付三',
        water_price: 0,
        electricity_price: 0,
        gas_price: 0,
        lease_term: '12个月',
      },
      implicit_values: {},
      total_cost_analysis: {
        monthly_base: 4980,
        estimated_utilities: 0,
        monthly_total: 4980,
        yearly_total: 59760,
        market_comparison: '符合市场平均水平',
      },
    },
    report_markdown: '## 测试报告',
    summary: {
      total_risks: 0,
      high_risks: 0,
      medium_risks: 0,
      low_risks: 0,
      compliant: true,
    },
    is_template: false,
  };
}

function testDogSuggestionCardsShowMeaningfulPreview() {
  const workspace = buildWorkspaceData({
    ...createBaseReport(),
    suggestions: ['要求删除租金贷条款，并保留按月支付方式。'],
  });

  assert.equal(workspace.dogCards.length, 1);
  assert.equal(workspace.dogCards[0].title, '建议 1');
  assert.equal(
    workspace.dogCards[0].note,
    '要求删除租金贷条款，并保留按月支付方式。'
  );
}

function testDogStructuredSuggestionKeepsCategoryTitle() {
  const workspace = buildWorkspaceData({
    ...createBaseReport(),
    suggestions: [
      {
        category: '协商策略',
        content: '先要求删除租金贷，再谈押金和服务费。',
        priority: 'high',
      },
    ],
  });

  assert.equal(workspace.dogCards.length, 1);
  assert.equal(workspace.dogCards[0].title, '建议: 协商策略');
  assert.equal(workspace.dogCards[0].note, '先要求删除租金贷，再谈押金和服务费。');
}

function testWorkspaceAnnotationsWireCardsBackToSourceLines() {
  const workspace = buildWorkspaceData({
    ...createBaseReport(),
    contract_text: [
      '房屋租赁合同',
      '押金：4980 元',
      '乙方提前退租，押金不退。',
      '水费：8 元/吨',
      '电费：1.2 元/度',
    ].join('\n'),
    risk_items: [
      {
        clause: '乙方提前退租，押金不退。',
        risk_level: 'high',
        issue: '押金不退',
        legal_basis: '民法典第 497 条',
        suggestion: '要求改为按实际损失扣除后退还。',
      },
    ],
    legal_references: [
      {
        law_id: 'law-1',
        title: '民法典第 497 条',
        content: '格式条款不得不合理免除或加重责任。',
        relevance: '直接关联',
        application: '可用于押金不退条款。',
      },
    ],
  });

  assert.ok(workspace.annotationsByAgent.owl.length > 0);
  assert.equal(workspace.annotationsByAgent.owl[0].lineIndex, 2);
  assert.equal(workspace.owlCards[0].lineIndex, 2);
  assert.equal(workspace.dogCards[0].lineIndex, 2);
  assert.ok(workspace.beaverCards.some((card) => typeof card.lineIndex === 'number'));
}

testDogSuggestionCardsShowMeaningfulPreview();
testDogStructuredSuggestionKeepsCategoryTitle();
testWorkspaceAnnotationsWireCardsBackToSourceLines();
