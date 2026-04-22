# Queue And Burn-After-Reading Design

**Context**

The current `analyze/queue` endpoint is not a real queue. It immediately starts work with `asyncio.create_task(...)`, so multiple expensive LLM analyses can run at once. Task, event, contract, and report state also live forever in process memory unless the process restarts. The UI exposes a `burnAfterReading` toggle, but backend cleanup semantics are incomplete.

**Goals**

1. Make queued analysis truly single-worker and serial.
2. Bound in-memory growth with explicit task, event, contract, and report cleanup.
3. Turn burn-after-reading into a backend-enforced lifecycle, not only a frontend preference.
4. Preserve the existing frontend contract as much as possible.

**Architecture**

We will keep the current in-process design, but change it from "fire-and-forget tasks plus dicts" to "single worker plus lifecycle-aware stores". `analysis_queue.py` becomes the queue state manager with a pending deque, a single running slot, task/event metadata, and cleanup helpers. `analysis_queue_worker.py` becomes a long-lived worker loop started from FastAPI startup that continuously consumes the queue.

`main.py` keeps `contracts_store` and `analysis_results` for now, but every record gets lifecycle metadata such as ownership, timestamps, burn-after-reading, and last access time. The backend will expose cleanup hooks so a logout action or TTL sweep can purge contract text, reports, and task/event history. This gives us a stable base now and a clean path to Redis or database persistence later.

**Data Flow**

1. Upload stores contract text and metadata but does not start analysis.
2. `analyze/queue` creates a task record, appends it to the pending queue, and returns task metadata.
3. The single worker dequeues the next task only when no other analysis is running.
4. Worker writes SSE events into task event storage and writes final report state into `analysis_results`.
5. SSE readers stream from the stored event buffer until the task finishes.
6. Cleanup runs in two ways:
   - explicit cleanup on logout / burn-after-reading action
   - periodic TTL cleanup for completed tasks, events, contracts, and reports

**Fallback Semantics**

We cannot safely kill a Python thread spawned by `asyncio.to_thread`, so the real fix is to stop creating many concurrent analyses. We will keep task-level serial execution and improve step handling so fallback is explicit in metadata. The worker will never start another task until the current task's analysis loop returns.

**Burn-After-Reading**

Burn-after-reading will be stored with each uploaded contract. When enabled:

1. the frontend sends the contract/session preference at upload time
2. the backend marks the contract/report/task records as burnable
3. logout triggers an authenticated cleanup request
4. TTL cleanup also removes stale burnable data if logout never happens

User preferences remain intact. Only contract text, report payloads, queue tasks, and event buffers are deleted.

**Testing Strategy**

Add focused regression tests for:

1. single-worker queue ordering
2. task state transitions and queue positions
3. cleanup of completed tasks and stale event buffers
4. burn-after-reading logout cleanup
5. report/task access after cleanup

Keep tests isolated from live LLM calls by patching the worker/runtime boundaries.
