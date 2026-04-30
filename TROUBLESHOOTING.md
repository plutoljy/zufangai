# 前端显示问题排查指南

## 问题描述
AI 分析结果在后端测试正常，但前端显示不出来。

## 已完成的修复

### 1. ✅ 字段映射问题
**文件**: `src/services/api.ts`, `src/components/cardConverters.ts`

**问题**: 后端返回 `issue/strategy/script`，前端期望 `scenario/tip/example`

**解决**: 添加了字段兼容逻辑
```typescript
const scenario = tip.issue || tip.scenario || '谈判场景';
const tipContent = tip.strategy || tip.tip || '';
const example = tip.script || tip.example;
```

### 2. ✅ Beaver API Key 更新
**文件**: `backend/.env`

**更新**: `CLAUDE_API_KEY_BEAVER=your-beaver-api-key`

### 3. ✅ 添加前端日志
**文件**: `src/components/cardConverters.ts`

**添加**: 详细的转换日志，方便追踪数据流

## 诊断结果

### 后端测试 ✅ 正常
```bash
cd backend
python diagnose_agents.py
```

**结果**:
- Owl: 识别到 5 个风险 ✓
- Dog: 找到 3 条法律，3 条谈判技巧 ✓
- Beaver: 押金检查正常 ✓

## 排查步骤

### 步骤 1: 检查浏览器控制台
1. 打开浏览器 F12
2. 切换到 Console 标签
3. 上传合同并分析
4. 查找以下日志:

```
[前端] 获取到分析报告: {...}
[cardConverters] 开始转换卡片: {...}
[cardConverters] 卡片转换完成: {...}
```

**期望输出**:
```javascript
[前端] 获取到分析报告: {
  contractId: "xxx",
  riskItemsCount: 5,
  highRiskCount: 1,
  mediumRiskCount: 2,
  lowRiskCount: 2,
  entities: {...}
}

[cardConverters] 开始转换卡片: {
  riskItems: 5,
  legalRefs: 3,
  caseRefs: 2,
  suggestions: 3,
  negotiationTips: 3,
  calculations: true
}

[cardConverters] 卡片转换完成: {
  owlCards: 5,
  dogCards: 8,  // 3法律 + 2案例 + 3建议
  beaverCards: 6,
  total: 19
}
```

### 步骤 2: 检查 Network 请求
1. 打开浏览器 F12
2. 切换到 Network 标签
3. 上传合同并分析
4. 找到 `/api/contracts/{id}/report` 请求
5. 查看 Response

**期望响应**:
```json
{
  "contract_id": "xxx",
  "entities": {...},
  "risk_items": [...],  // 应该有数据
  "legal_references": [...],  // 应该有数据
  "negotiation_tips": [...],  // 应该有数据
  "calculations": {...}  // 应该有数据
}
```

### 步骤 3: 检查是否走了模板路线
在浏览器 Console 中检查:
```javascript
// 查看报告对象
console.log(report);

// 检查是否被标记为模板
console.log('is_template:', report.is_template);

// 检查各个数据数组
console.log('risk_items:', report.risk_items);
console.log('legal_references:', report.legal_references);
console.log('negotiation_tips:', report.negotiation_tips);
```

## 可能的问题和解决方案

### 问题 1: 数据为空数组
**症状**: `risk_items: []`, `legal_references: []`

**原因**: 后端 API 调用失败，走了 fallback 逻辑

**解决**:
1. 检查后端日志是否有错误
2. 检查 API Key 是否有效
3. 检查网络连接

### 问题 2: 前端没有接收到数据
**症状**: Network 中看到数据，但前端没有显示

**原因**: 前端数据处理逻辑有问题

**解决**:
1. 检查 `convertAllCards` 函数的日志
2. 检查 `buildWorkspaceData` 函数
3. 检查组件的 render 逻辑

### 问题 3: 字段不匹配
**症状**: 显示 "undefined"

**原因**: 前后端字段名不一致

**解决**: 已修复（见上面的字段映射问题）

## 快速测试

### 测试后端
```bash
cd backend
python test_full_flow.py
```

### 测试前端
1. 启动后端: `cd backend && uvicorn src.main:app --reload`
2. 启动前端: `cd .. && npm run dev`
3. 打开浏览器: `http://localhost:5173`
4. 上传测试合同
5. 查看控制台日志

## 联系信息
如果问题仍然存在，请提供:
1. 浏览器控制台的完整日志
2. Network 中 `/api/contracts/{id}/report` 的响应
3. 后端日志（如果有错误）
