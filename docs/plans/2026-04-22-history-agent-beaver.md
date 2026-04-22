# History, Agent Chat, And Beaver Utility Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add session-scoped review history, in-workspace agent follow-up chat, logout-only burn-after-reading cleanup, aligned progress UI, and Beaver-owned utility extraction.

**Architecture:** Keep the current in-memory runtime model, extend the backend with history and agent-chat endpoints, and move Beaver fee extraction to a contract-text-first deterministic layer. Frontend state in `App.tsx` becomes the source of truth for active history selection and per-contract/per-agent chat threads.

**Tech Stack:** FastAPI, in-memory Python runtime stores, React 19, TypeScript, Vite, pytest, existing TS regression scripts

---

### Task 1: Add backend regression tests for history and burn-after-reading semantics

**Files:**
- Modify: `backend/tests/test_burn_after_reading.py`
- Modify: `backend/tests/test_state_cleanup.py`

**Step 1: Write the failing test**

Add tests that verify:
- `/api/contracts/history` returns only user-owned contracts with reports.
- `cleanup_runtime_state()` does not auto-purge a burn-after-reading contract just because the analysis finished.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_burn_after_reading.py backend/tests/test_state_cleanup.py -v`
Expected: FAIL because history endpoint does not exist and cleanup still purges burn-after-reading by completion age.

**Step 3: Write minimal implementation**

Implement history listing and remove completion-age-based burn-after-reading purge logic.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_burn_after_reading.py backend/tests/test_state_cleanup.py -v`
Expected: PASS

### Task 2: Add backend regression tests for agent chat endpoint

**Files:**
- Create: `backend/tests/test_agent_chat.py`
- Modify: `backend/src/main.py`

**Step 1: Write the failing test**

Add tests that verify:
- Authenticated owner can call `/api/contracts/{contract_id}/agents/{agent_key}/chat`.
- Non-owner receives `403`.
- Endpoint returns a reply payload and echoes agent key.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_agent_chat.py -v`
Expected: FAIL because endpoint does not exist.

**Step 3: Write minimal implementation**

Add request/response models, ownership checks, and a small chat service hook in `backend/src/main.py`.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_agent_chat.py -v`
Expected: PASS

### Task 3: Add Beaver deterministic extraction regression tests

**Files:**
- Create: `backend/tests/test_beaver_utility_extraction.py`
- Modify: `backend/src/agents/beaver_calculator.py`

**Step 1: Write the failing test**

Add tests for:
- Explicit overcharge extraction from raw text.
- Explicit compliant extraction from raw text.
- Ambiguous utility clause without explicit price.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_beaver_utility_extraction.py -v`
Expected: FAIL because Beaver does not yet expose the new extraction behavior.

**Step 3: Write minimal implementation**

Add Beaver-owned extraction helpers and integrate them into deterministic and fallback flows.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_beaver_utility_extraction.py -v`
Expected: PASS

### Task 4: Implement backend history and agent chat services

**Files:**
- Modify: `backend/src/main.py`
- Create: `backend/src/agents/agent_chat.py`

**Step 1: Write the failing test**

Reuse Task 1 and Task 2 tests as the safety net.

**Step 2: Run targeted tests to confirm red**

Run: `pytest backend/tests/test_burn_after_reading.py backend/tests/test_state_cleanup.py backend/tests/test_agent_chat.py -v`

**Step 3: Write minimal implementation**

- Add history summary serializer.
- Add `/api/contracts/history`.
- Add `/api/contracts/{contract_id}/agents/{agent_key}/chat`.
- Remove completion-grace burn purge branch.
- Keep logout cleanup endpoint as the explicit deletion path.

**Step 4: Run targeted tests**

Run: `pytest backend/tests/test_burn_after_reading.py backend/tests/test_state_cleanup.py backend/tests/test_agent_chat.py -v`

### Task 5: Implement Beaver-owned utility extraction

**Files:**
- Modify: `backend/src/agents/beaver_calculator.py`
- Modify: `backend/src/analysis_runtime.py`

**Step 1: Write the failing test**

Reuse Task 3 regression tests.

**Step 2: Run targeted tests to confirm red**

Run: `pytest backend/tests/test_beaver_utility_extraction.py -v`

**Step 3: Write minimal implementation**

- Add raw-text utility extraction and normalization helpers.
- Feed deterministic calculation from Beaver-owned extraction.
- Mark ambiguous utility clauses when prices are omitted.
- Keep Owl entities optional, not required.

**Step 4: Run targeted tests**

Run: `pytest backend/tests/test_beaver_utility_extraction.py -v`

### Task 6: Add frontend API and state regressions

**Files:**
- Modify: `src/services/api.ts`
- Create: `src/services/workspaceState.regression.ts`

**Step 1: Write the failing test**

Add lightweight TS regressions for history/chat state shaping.

**Step 2: Run test to verify it fails**

Run: `npx tsx src/services/workspaceState.regression.ts`
Expected: FAIL until new helpers/types exist.

**Step 3: Write minimal implementation**

Add history/chat API types and state helper utilities.

**Step 4: Run test to verify it passes**

Run: `npx tsx src/services/workspaceState.regression.ts`

### Task 7: Implement workspace history switching and agent chat UI

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/components/WorkspaceResultView.tsx`
- Modify: `src/services/api.ts`

**Step 1: Write the failing test**

Reuse Task 6 regression and existing `tests/frontend_regressions.ts`.

**Step 2: Run tests to confirm red**

Run: `npx tsx src/services/workspaceState.regression.ts`
Run: `npx tsx tests/frontend_regressions.ts`

**Step 3: Write minimal implementation**

- Keep workspace history in `App.tsx`.
- Fetch history list after analysis and on workspace open.
- Allow selecting a prior contract and loading its report.
- Implement per-contract/per-agent session chat threads.
- Wire send button and loading/error states.

**Step 4: Run tests**

Run: `npx tsx src/services/workspaceState.regression.ts`
Run: `npx tsx tests/frontend_regressions.ts`

### Task 8: Align progress UI and remove elapsed-second pressure

**Files:**
- Modify: `src/components/LiveAnalysisStage.tsx`

**Step 1: Write the failing test**

Cover this with a small TS regression or direct component-state helper if needed.

**Step 2: Run test to confirm red**

Run the relevant TS regression command.

**Step 3: Write minimal implementation**

- Remove elapsed-second messaging.
- Keep progress bound to backend event stages only.
- Preserve queue messaging but avoid countdown pressure.

**Step 4: Run test**

Run the relevant TS regression command.

### Task 9: Run full verification

**Files:**
- No source changes required

**Step 1: Backend verification**

Run: `pytest backend/tests/test_burn_after_reading.py backend/tests/test_state_cleanup.py backend/tests/test_agent_chat.py backend/tests/test_beaver_utility_extraction.py -v`

**Step 2: Runtime regression verification**

Run: `pytest backend/test_analysis_runtime_regressions.py -v`

**Step 3: Frontend verification**

Run: `npm run lint`
Run: `npx tsx tests/frontend_regressions.ts`
Run: `npx tsx src/services/workspaceState.regression.ts`

**Step 4: Commit**

```bash
git add backend/tests/test_burn_after_reading.py backend/tests/test_state_cleanup.py backend/tests/test_agent_chat.py backend/tests/test_beaver_utility_extraction.py backend/src/main.py backend/src/agents/agent_chat.py backend/src/agents/beaver_calculator.py backend/src/analysis_runtime.py src/services/api.ts src/services/workspaceState.regression.ts src/components/WorkspaceResultView.tsx src/components/LiveAnalysisStage.tsx src/App.tsx docs/plans/2026-04-22-history-agent-beaver-design.md docs/plans/2026-04-22-history-agent-beaver.md
git commit -m "feat: add workspace history chat and beaver extraction"
```
