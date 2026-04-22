# Queue And Burn-After-Reading Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the fake queue with a real single-worker serial queue, add lifecycle cleanup for in-memory state, and make burn-after-reading a backend-enforced cleanup flow.

**Architecture:** Keep the current in-process storage model for now, but add explicit queue state, a single long-lived worker loop, and TTL-based cleanup. Extend contract/report/task metadata so logout and periodic sweeps can safely remove burnable content and stale completed tasks.

**Tech Stack:** FastAPI, asyncio, Python in-memory queue/state, pytest/TestClient, React TypeScript frontend.

---

### Task 1: Queue State Model

**Files:**
- Modify: `backend/src/analysis_queue.py`
- Test: `backend/tests/test_queue_runtime.py`

**Step 1: Write the failing tests**

Cover:
- enqueue keeps FIFO order
- only one task can be marked running at once
- queue position reflects pending items, not all tasks ever seen
- completed tasks can be cleared by cleanup helpers

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_queue_runtime.py -q`
Expected: FAIL because the queue model does not yet support real pending/running state.

**Step 3: Write minimal implementation**

Implement:
- pending deque
- running task id
- enqueue/dequeue helpers
- queue position recomputation
- cleanup helpers for finished task/event state

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_queue_runtime.py -q`
Expected: PASS

### Task 2: Single Worker Runtime

**Files:**
- Modify: `backend/src/analysis_queue_worker.py`
- Modify: `backend/src/main.py`
- Test: `backend/tests/test_queue_worker_flow.py`

**Step 1: Write the failing tests**

Cover:
- `analyze/queue` only enqueues work
- startup creates one worker loop
- worker processes tasks serially
- second task does not enter running state until first completes

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_queue_worker_flow.py -q`
Expected: FAIL because `analyze/queue` still starts work immediately.

**Step 3: Write minimal implementation**

Implement:
- startup hook to create one worker loop
- enqueue-only endpoint behavior
- worker loop that waits for pending work and runs one task at a time
- completion/failure bookkeeping through queue helpers

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_queue_worker_flow.py -q`
Expected: PASS

### Task 3: State Lifecycle And TTL Cleanup

**Files:**
- Modify: `backend/src/main.py`
- Modify: `backend/src/analysis_queue.py`
- Test: `backend/tests/test_state_cleanup.py`

**Step 1: Write the failing tests**

Cover:
- completed tasks/events are removed after TTL
- stale contract/report payloads are removed after TTL
- accessing cleaned-up reports returns 404

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state_cleanup.py -q`
Expected: FAIL because cleanup is not wired and `clear_task()` is unused.

**Step 3: Write minimal implementation**

Implement:
- metadata fields: `created_at`, `completed_at`, `last_accessed_at`
- periodic cleanup coroutine started with app startup
- actual `clear_task()` usage
- cleanup for stale `contracts_store` and `analysis_results`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_state_cleanup.py -q`
Expected: PASS

### Task 4: Burn-After-Reading End-To-End

**Files:**
- Modify: `backend/src/main.py`
- Modify: `src/services/api.ts`
- Modify: `src/App.tsx`
- Test: `backend/tests/test_burn_after_reading.py`

**Step 1: Write the failing tests**

Cover:
- upload can mark contract as `burn_after_reading`
- authenticated cleanup endpoint removes contract/report/task state
- preferences are not deleted

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_burn_after_reading.py -q`
Expected: FAIL because logout cleanup semantics are incomplete.

**Step 3: Write minimal implementation**

Implement:
- upload metadata support for `burn_after_reading`
- authenticated cleanup endpoint for current user/session
- frontend logout path calls cleanup before sign-out when the setting is enabled

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_burn_after_reading.py -q`
Expected: PASS

### Task 5: Regression Verification

**Files:**
- Modify: `backend/tests/test_auth_boundaries.py` if needed
- Reuse: `backend/tests/test_preferences_router_module.py`
- Reuse: `tests/frontend_regressions.ts`

**Step 1: Run focused backend suite**

Run: `python -m pytest tests/test_queue_runtime.py tests/test_queue_worker_flow.py tests/test_state_cleanup.py tests/test_burn_after_reading.py tests/test_auth_boundaries.py tests/test_preferences_router_module.py -q`
Expected: PASS

**Step 2: Run frontend regression and type-check**

Run: `node --experimental-strip-types tests/frontend_regressions.ts`
Expected: PASS

Run: `npm.cmd run lint`
Expected: PASS

**Step 3: Review manual risks**

Check:
- startup/shutdown worker lifecycle
- queue status text still sensible in UI
- no reliance on legacy immediate execution path
