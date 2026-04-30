# Dog And Cat Structured Chunking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Dog and Cat stable on the Claude relay by replacing oversized monolithic prompts with structured chunked analysis while preserving RAG retrieval for Dog.

**Architecture:** Dog consumes Owl's structured risk output, splits it into three top-level groups, recursively subdivides any group that still exceeds prompt budget, runs RAG + LLM formatting per chunk, then merges only legal references and case references. Cat consumes three structured categories (Owl risks, Dog references, Beaver calculations), builds category-level summaries first, then produces the final report from those summaries instead of the full raw payloads.

**Tech Stack:** FastAPI, in-memory queue worker, Claude relay (`/v1/messages`), React/Vite frontend, Python unit regression tests.

---

### Task 1: Dog chunking utility

**Files:**
- Modify: `backend/src/agents/dog_retriever.py`
- Test: `backend/test_analysis_runtime_regressions.py`

**Step 1: Write the failing test**

Add regression coverage for:
- three-way top-level chunking
- recursive split when one chunk still exceeds size budget
- final chunk payloads containing only compact `risk_level / issue / clause_excerpt`

**Step 2: Run test to verify it fails**

Run: `python backend/test_analysis_runtime_regressions.py`
Expected: FAIL until chunking helper exists.

**Step 3: Write minimal implementation**

Add helpers in `DogRetriever`:
- `_compact_risk_items`
- `_estimate_payload_size`
- `_split_into_three_groups`
- `_split_until_within_budget`
- `_merge_reference_results`

Keep output limited to:
- `legal_references`
- `case_references`

**Step 4: Run test to verify it passes**

Run: `python backend/test_analysis_runtime_regressions.py`
Expected: PASS.

### Task 2: Dog per-chunk RAG formatting

**Files:**
- Modify: `backend/src/agents/dog_retriever.py`
- Test: `backend/test_analysis_runtime_regressions.py`

**Step 1: Write the failing test**

Add a regression asserting Dog:
- runs RAG per chunk
- formats each chunk independently
- merges deduplicated references
- does not emit suggestions or negotiation tips

**Step 2: Run test to verify it fails**

Run: `python backend/test_analysis_runtime_regressions.py`
Expected: FAIL before Dog aggregation is updated.

**Step 3: Write minimal implementation**

Refactor `format_results` flow to:
- iterate chunked risks
- call `_call_llm_api` per chunk
- merge `legal_references` and `case_references`
- return empty arrays for `suggestions` and `negotiation_tips`

**Step 4: Run test to verify it passes**

Run: `python backend/test_analysis_runtime_regressions.py`
Expected: PASS.

### Task 3: Cat category summaries

**Files:**
- Modify: `backend/src/agents/cat_reporter.py`
- Test: `backend/test_analysis_runtime_regressions.py`

**Step 1: Write the failing test**

Add regression coverage for:
- three category summaries: Owl / Dog / Beaver
- compact category payloads
- final prompt built from summaries instead of raw full payloads

**Step 2: Run test to verify it fails**

Run: `python backend/test_analysis_runtime_regressions.py`
Expected: FAIL until summary helpers exist.

**Step 3: Write minimal implementation**

Add helpers in `CatReporter`:
- `_build_owl_summary_payload`
- `_build_dog_summary_payload`
- `_build_beaver_summary_payload`
- `_build_category_summaries`

Generate the final report prompt from those summaries only.

**Step 4: Run test to verify it passes**

Run: `python backend/test_analysis_runtime_regressions.py`
Expected: PASS.

### Task 4: Runtime and frontend compatibility

**Files:**
- Modify: `backend/src/analysis_runtime.py`
- Modify: `backend/src/main.py`
- Modify: `src/components/cardConverters.ts`
- Modify: `src/components/LiveAnalysisStage.tsx`
- Test: `backend/test_analysis_runtime_regressions.py`

**Step 1: Write the failing test**

Add regression coverage for:
- Dog returning only legal refs / case refs
- Cat summary flow preserving full Owl risk count in stored state
- Beaver mode metadata still surfacing in progress events

**Step 2: Run test to verify it fails**

Run: `python backend/test_analysis_runtime_regressions.py`
Expected: FAIL before runtime wiring is updated.

**Step 3: Write minimal implementation**

Update runtime and UI expectations:
- keep `risk_items` untouched after Owl
- treat Dog as references-only
- show Beaver/Cat progress without depending on suggestions

**Step 4: Run test to verify it passes**

Run:
- `python backend/test_analysis_runtime_regressions.py`
- `npm.cmd run build`

Expected: both PASS.

### Task 5: Manual verification

**Files:**
- No source changes required

**Step 1: Restart services**

Run backend:
`python -m uvicorn src.main:app --host 0.0.0.0 --port 8003`

Run frontend:
`npm run dev`

**Step 2: Verify logs**

Expected:
- Owl snapshot keeps full LLM risk count
- Dog payload size materially smaller than before
- Cat payload size materially smaller than before
- fewer relay disconnects

**Step 3: Verify API output**

Check `/api/contracts/{id}/report`
Expected:
- `risk_items` count matches Owl snapshot
- Dog returns populated `legal_references` / `case_references`
- no dependence on `suggestions` / `negotiation_tips`
