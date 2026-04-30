# README 与当前架构图设计

## 目标

把现有项目说明重写成更适合作业提交与答辩展示的版本，并补一张“当前真实架构图”，确保文档表述与实际代码一致。

## 设计原则

1. 不描述理想架构，只描述当前真实可运行架构。
2. README 按老师要求组织，而不是按开发者习惯组织。
3. 重点突出：多智能体、RAG、工具调用、提示词工程、可演示原型、测试评估。
4. 不改业务逻辑，不新增后端接口，只整理表达。

## 当前真实架构范围

- 前端：React + TypeScript + Vite
- 后端：FastAPI
- 编排层：`analysis_runtime.py` + 队列与流式事件
- Agent：
  - `OwlAnalyst`
  - `DogRetriever`
  - `BeaverCalculator`
  - `CatReporter`
- RAG：
  - `knowledge/retriever.py`
  - `knowledge/vectorize.py`
  - `knowledge/data/*`
- 工具：
  - 文档解析工具
  - 隐私脱敏工具
  - 水电气价格工具
  - 自定义 JSON 提取与运行时辅助工具

## README 新结构

1. 项目简介
2. 按老师要求的完成情况对照表
3. 当前真实系统架构图
4. 系统工作流程
5. 多智能体角色设计
6. RAG 知识库设计
7. 工具调用设计
8. 提示词工程设计
9. 测试与评估
10. 可运行与可演示说明
11. 项目结构
12. 快速启动
13. 后续改进方向

## 当前架构图设计

架构图采用 Mermaid，分 5 层：

1. 用户与前端交互层
2. FastAPI API 与认证/上传层
3. 分析编排与事件流层
4. 多智能体协作层
5. RAG 与工具支撑层

图中明确标注：

- `App.tsx`
- `LiveAnalysisStage.tsx`
- `WorkspaceResultView.tsx`
- `main.py`
- `analysis_runtime.py`
- `analysis_queue_worker.py`
- `streaming.py`
- `knowledge/retriever.py`
- `document_parser.py`
- `utility_price_loader.py`

## 交付效果

改写后的 README 应该满足：

- 老师能快速判断项目达标
- 组员能直接拿去写项目说明书
- 答辩时能直接作为口头讲稿提纲
