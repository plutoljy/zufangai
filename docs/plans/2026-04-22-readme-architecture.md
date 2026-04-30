# README And Architecture Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the project README around the teacher’s grading rubric and replace the old architecture section with a current, code-accurate architecture diagram.

**Architecture:** Keep the implementation documentation-only. The new README should describe the currently running frontend, backend, orchestration, agents, RAG layer, and tools exactly as implemented, while also mapping each capability to the assignment requirements. No runtime behavior changes are needed.

**Tech Stack:** Markdown, Mermaid, React/FastAPI code references, existing tests/docs

---

### Task 1: Gather architecture evidence

**Files:**
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\analysis_runtime.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\main.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\agents\owl_analyst.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\agents\dog_retriever.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\agents\beaver_calculator.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\agents\cat_reporter.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\knowledge\retriever.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\knowledge\vectorize.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\utils\document_parser.py`
- Read: `e:\github-program\github-date\租房ai\租房避坑局\backend\src\utils\utility_price_loader.py`

**Step 1: Confirm current runtime path**

Run targeted reads and record which files reflect the current production path versus legacy experiments.

**Step 2: Confirm assignment coverage evidence**

Collect concrete references for:
- multi-agent roles
- RAG pipeline
- tool usage
- prompt engineering
- prototype UI
- tests/evaluation

### Task 2: Rewrite README

**Files:**
- Modify: `e:\github-program\github-date\租房ai\租房避坑局\README.md`

**Step 1: Replace the old structure**

Write a clean Chinese README organized by:
- 项目简介
- 对照老师要求的完成情况
- 当前真实系统架构图
- 系统工作流程
- Agent 角色设计
- RAG 设计
- 工具设计
- 提示词工程设计
- 测试与评估
- 原型与演示方式
- 项目结构
- 快速启动
- 后续改进方向

**Step 2: Use the current architecture only**

Do not describe idealized LangGraph or future tool-calling designs as if they already exist.

### Task 3: Verify readability and references

**Files:**
- Verify: `e:\github-program\github-date\租房ai\租房避坑局\README.md`

**Step 1: Check that the README is self-contained**

Make sure a teacher can understand the project without opening other files.

**Step 2: Check that no runtime claims are false**

Re-read the architecture section against the actual code paths.
