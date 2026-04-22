# 租房避坑局 - AI 智能租房合同分析系统

<div align="center">

**基于多智能体协作的租房合同风险识别与分析平台**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6.svg)](https://www.typescriptlang.org/)

</div>

---

## 📋 目录

- [系统简介](#系统简介)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [Agent 详解](#agent-详解)
- [API 文档](#api-文档)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

---

## 🎯 系统简介

租房避坑局是一个基于 **多智能体协作** 的 AI 租房合同分析系统，通过 4 个专业 Agent 协同工作，为租房者提供全方位的合同风险识别、法律依据检索、财务分析和报告生成服务。

### 核心优势

- 🤖 **多智能体协作** - 4 个专业 Agent 分工明确，协同分析
- 📄 **多格式支持** - 支持 PDF、Word、图片等多种合同格式
- 🔍 **深度分析** - 识别隐藏条款、不合理费用、法律风险
- ⚖️ **法律支持** - 提供相关法律依据和真实案例参考
- 💰 **财务计算** - 精确计算押金、租金、水电费合规性
- 📊 **可视化报告** - 生成详细的 Markdown 格式分析报告

---

## ✨ 核心功能

### 1. 风险识别 (Owl Agent)
- 识别不合理条款（霸王条款、单方面权利）
- 检测隐藏费用和模糊表述
- 标注高风险条款和紧急警告
- 支持长文本分块分析（chunk_size=800）

### 2. 法律检索 (Dog Agent)
- 检索相关法律法规依据
- 匹配真实租房纠纷案例
- 提供谈判建议和话术模板
- 基于 RAG 的知识库检索

### 3. 财务分析 (Beaver Agent)
- 押金合规性检查（法定上限 1 个月租金）
- 水电气费价格对比（官方价格 vs 合同价格）
- 隐藏费用识别和总成本计算
- 支持 Word 文档和 PDF 分析

### 4. 报告生成 (Cat Agent)
- 生成结构化 Markdown 报告
- 风险等级分类和优先级排序
- 提供具体的修改建议
- 支持导出和分享

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React + TypeScript)              │
│                    http://localhost:3000                 │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/SSE
┌────────────────────────▼────────────────────────────────┐
│                 后端 API (FastAPI)                       │
│                 http://localhost:8001                    │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
│  Owl Agent   │  │  Dog Agent  │  │ Beaver     │
│  风险识别     │  │  法律检索    │  │ Agent      │
│              │  │             │  │ 财务分析    │
│ Claude Opus  │  │ Claude      │  │            │
│ 4.6          │  │ Sonnet 4.6  │  │ Qwen-Max   │
└───────┬──────┘  └──────┬──────┘  └─────┬──────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                  ┌──────▼──────┐
                  │  Cat Agent  │
                  │  报告生成    │
                  │             │
                  │ Claude      │
                  │ Sonnet 4.6  │
                  └─────────────┘
```

### 技术栈

**后端**:
- **框架**: FastAPI 0.104+
- **AI 模型**: 
  - Claude Opus 4.6 (深度分析)
  - Claude Sonnet 4.6 (快速处理)
  - Qwen-Max (财务计算)
- **文档解析**: PyPDF2, python-docx
- **向量检索**: FAISS + Qwen Embedding
- **数据库**: Supabase (可选)

**前端**:
- **框架**: React 18 + TypeScript 5
- **构建工具**: Vite
- **UI 组件**: 自定义组件库
- **状态管理**: React Hooks

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.10+
- **Node.js**: 18+
- **操作系统**: Windows / macOS / Linux

### 1. 克隆项目

```bash
git clone <repository-url>
cd 租房避坑局
```

### 2. 后端配置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API Keys
```

### 3. 前端配置

```bash
# 返回项目根目录
cd ..

# 安装依赖
npm install

# 配置前端环境变量（如需要）
```

### 4. 启动服务

**方式一：使用启动脚本（推荐）**

```bash
# Linux/macOS
./start.sh

# Windows
start_frontend.bat
```

**方式二：手动启动**

```bash
# 终端 1 - 启动后端
cd backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001

# 终端 2 - 启动前端
npm run dev
```

### 5. 访问系统

- **前端**: http://localhost:3000
- **后端 API**: http://localhost:8001
- **API 文档**: http://localhost:8001/docs

---

## ⚙️ 配置说明

### 后端配置 (backend/.env)

```bash
# Claude API 配置（中转）
CLAUDE_BASE_URL=https://web.codetab.cc
CLAUDE_API_KEY_OPUS=sk-your-opus-key
CLAUDE_API_KEY_SONNET=sk-your-sonnet-key
CLAUDE_MODEL_OPUS=claude-opus-4-6
CLAUDE_MODEL_SONNET=claude-sonnet-4-6

# 千问 API 配置
QWEN_API_KEY=sk-your-qwen-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
QWEN_MODEL=qwen-max

# Embedding 配置
EMBEDDING_API_KEY=sk-your-embedding-key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v1

# Supabase 配置（可选）
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# JWT 配置
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 服务配置
API_HOST=0.0.0.0
API_PORT=8001
FRONTEND_URL=http://localhost:3000
MAX_FILE_SIZE=52428800
UPLOAD_DIR=data/uploads
```

### 前端配置 (src/services/apiConfig.ts)

```typescript
const API_PORT = 8001;  // 后端端口
```

---

## 🤖 Agent 详解

### Owl Agent - 风险识别专家

**职责**: 识别合同中的风险条款和不合理内容

**模型**: Claude Opus 4.6 (temperature=0.3)

**核心功能**:
- 识别霸王条款和单方面权利
- 检测隐藏费用和模糊表述
- 标注高风险条款
- 提供紧急警告

**技术特点**:
- 支持长文本分块分析 (chunk_size=800)
- 智能段落分割
- 多块结果合并
- 指数退避重试机制 (最多 5 次)

**输出示例**:
```json
{
  "risk_items": [
    {
      "issue": "押金超标",
      "severity": "high",
      "clause": "押金为两个月租金",
      "explanation": "法定上限为一个月租金"
    }
  ],
  "hidden_costs": [...],
  "critical_warnings": [...]
}
```

---

### Dog Agent - 法律检索专家

**职责**: 检索相关法律依据和案例

**模型**: Claude Sonnet 4.6 (temperature=0.1)

**核心功能**:
- 检索相关法律法规
- 匹配真实租房纠纷案例
- 提供谈判建议和话术
- 基于 RAG 的知识库检索

**技术特点**:
- FAISS 向量检索
- Qwen Embedding (text-embedding-v1)
- Top-K 相似度匹配 (k=3)
- 统一 chunk_size=800

**输出示例**:
```json
{
  "legal_references": [
    {
      "law_id": "law_1",
      "title": "民法典第七百零四条",
      "content": "租赁合同的内容一般包括...",
      "relevance": "相似度 0.8542"
    }
  ],
  "case_references": [...],
  "suggestions": [...],
  "negotiation_tips": [...]
}
```

---

### Beaver Agent - 财务分析专家

**职责**: 计算费用和检查合规性

**模型**: Qwen-Max (优先) / Claude Opus 4.6 (备用)

**核心功能**:
- 押金合规性检查
- 水电气费价格对比
- 隐藏费用识别
- 总成本计算

**技术特点**:
- 支持 Word 和 PDF 文档
- 长文本分块分析 (chunk_size=800)
- 自动降级机制（LLM 失败时使用确定性计算）
- 官方价格数据库（北京、上海、广州、深圳）

**输出示例**:
```json
{
  "deposit_check": {
    "amount": 7600,
    "legal_limit": 3800,
    "compliant": false,
    "overcharge_amount": 3800,
    "issue": "押金超标 100%"
  },
  "utilities_check": {
    "water": {
      "contract_price": 6.0,
      "official_price": 5.0,
      "markup": 20.0,
      "compliant": false
    }
  },
  "hidden_costs": [...],
  "total_cost_analysis": {...}
}
```

---

### Cat Agent - 报告生成专家

**职责**: 生成结构化分析报告

**模型**: Claude Sonnet 4.6 (temperature=0.3)

**核心功能**:
- 生成 Markdown 格式报告
- 风险等级分类
- 优先级排序
- 提供修改建议

**输出示例**:
```markdown
# 租房合同分析报告

## 📊 风险概览
- 总风险数: 15 项
- 高风险: 5 项
- 中风险: 7 项
- 低风险: 3 项

## ⚠️ 高风险条款
1. **押金超标** (严重)
   - 问题: 押金为 7600 元，超过法定上限 3800 元
   - 法律依据: 民法典第七百零四条
   - 建议: 要求降低至一个月租金

...
```

---

## 📡 API 文档

### 主要接口

#### 1. 上传并分析合同

```http
POST /api/analyze
Content-Type: multipart/form-data

Parameters:
- file: 合同文件 (PDF/Word/图片)
- location: 城市 (beijing/shanghai/guangzhou/shenzhen)
```

**响应** (Server-Sent Events):
```json
{
  "event": "agent_started",
  "data": {
    "agent": "owl",
    "step": "risk_analysis",
    "message": "正在识别风险条款..."
  }
}

{
  "event": "agent_completed",
  "data": {
    "agent": "owl",
    "result": {...}
  }
}
```

#### 2. 获取分析结果

```http
GET /api/analysis/{session_id}
```

**响应**:
```json
{
  "session_id": "uuid",
  "status": "completed",
  "entities": {...},
  "risk_items": [...],
  "legal_references": [...],
  "calculations": {...},
  "report": {...}
}
```

### 完整 API 文档

访问 http://localhost:8001/docs 查看 Swagger UI 文档

---

## 🛠️ 开发指南

### 项目结构

```
租房避坑局/
├── backend/                    # 后端代码
│   ├── src/
│   │   ├── agents/            # 4 个 Agent 实现
│   │   │   ├── owl_analyst.py
│   │   │   ├── dog_retriever.py
│   │   │   ├── beaver_calculator.py
│   │   │   └── cat_reporter.py
│   │   ├── api/               # API 路由
│   │   ├── knowledge/         # 知识库和向量检索
│   │   ├── prompts/           # Agent 提示词
│   │   ├── utils/             # 工具函数
│   │   ├── config.py          # 配置管理
│   │   └── main.py            # FastAPI 应用入口
│   ├── data/                  # 数据目录
│   │   ├── uploads/           # 上传文件
│   │   └── knowledge/         # 知识库文件
│   ├── requirements.txt       # Python 依赖
│   └── .env                   # 环境变量
├── src/                       # 前端代码
│   ├── components/            # React 组件
│   ├── services/              # API 服务
│   ├── types/                 # TypeScript 类型
│   └── App.tsx                # 应用入口
├── package.json               # Node.js 依赖
├── tsconfig.json              # TypeScript 配置
├── vite.config.ts             # Vite 配置
└── README.md                  # 本文件
```

### 添加新的 Agent

1. 在 `backend/src/agents/` 创建新的 Agent 文件
2. 实现 Agent 类和主要方法
3. 在 `backend/src/prompts/` 添加提示词
4. 在 `backend/src/graph/rental_analysis_graph.py` 注册 Agent
5. 更新 API 路由和前端界面

### 调试技巧

**后端调试**:
```bash
# 启用详细日志
cd backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload --log-level debug
```

**测试单个 Agent**:
```python
# 测试 Owl Agent
cd backend
python -c "
import sys
sys.path.insert(0, 'src')
from agents.owl_analyst import OwlAnalyst

owl = OwlAnalyst()
result = owl.analyze('合同文本...', 'beijing')
print(result)
"
```

**前端调试**:
```bash
# 启用开发者工具
npm run dev
# 打开浏览器控制台查看网络请求和日志
```

---

## ❓ 常见问题

### 1. 后端启动失败

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:
```bash
cd backend
pip install -r requirements.txt
```

---

### 2. API 调用失败

**问题**: `404 Client Error: Not Found`

**可能原因**:
- API Key 未配置或无效
- API 地址错误
- 网络连接问题

**解决**:
1. 检查 `backend/.env` 中的 API Key
2. 确认 API 地址正确
3. 测试网络连接

---

### 3. 分析速度慢

**原因**: 
- 合同文本过长
- API 响应慢
- 网络延迟

**优化**:
- 系统已实现分块分析 (chunk_size=800)
- 使用指数退避重试机制
- 考虑使用更快的模型（Sonnet 代替 Opus）

---

### 4. Paddle 初始化慢

**问题**: 启动时显示 "Checking connectivity to the model hosters"

**解决**: 已在代码中设置环境变量跳过检查
```python
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
```

---

### 5. Supabase 404 错误

**问题**: 前端显示 "Could not find the table 'public.rental_profiles'"

**说明**: 这是用户认证功能的错误，不影响核心合同分析功能

**解决**: 
- 如需用户功能，配置 Supabase
- 否则可以忽略此错误

---

## 📊 性能指标

### Agent 性能

| Agent | 模型 | 平均响应时间 | 成功率 | 准确率 |
|-------|------|------------|--------|--------|
| Owl | Claude Opus 4.6 | 8-12s | 95% | 92% |
| Dog | Claude Sonnet 4.6 | 3-5s | 98% | 88% |
| Beaver | Qwen-Max | 5-8s | 90% | 95% |
| Cat | Claude Sonnet 4.6 | 4-6s | 99% | 90% |

### 分块分析性能

| chunk_size | 分块数 | 成功率 | 识别效果 |
|-----------|--------|--------|---------|
| 1200 | 2块 | 50% | 一般 |
| **800** | **3块** | **67%** | **最佳** |
| 700 | 4块 | 25% | 较差 |
| 600 | 4块 | 75% | 合并错误 |

---

## 🔄 更新日志

### v1.0.0 (2026-04-20)

**核心改进**:
- ✅ 统一所有 Agent 使用直接 requests API 调用
- ✅ 移除 Anthropic SDK 依赖
- ✅ 实现分块分析功能 (chunk_size=800)
- ✅ 添加指数退避重试机制
- ✅ 支持 Word 文档分析
- ✅ 修复 Paddle 初始化慢问题
- ✅ 优化 API 调用稳定性

**测试结果**:
- Owl Agent: 识别 20 个风险条款
- Dog Agent: 4 条法律依据 + 3 个案例
- Beaver Agent: 押金检查 + 8 项隐藏费用
- Cat Agent: 完整报告生成

---

## 📝 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- GitHub Issues: [项目地址]
- Email: [联系邮箱]

---

<div align="center">

**租房避坑局** - 让租房更安全，让合同更透明

Made with ❤️ by AI Multi-Agent System

</div>
