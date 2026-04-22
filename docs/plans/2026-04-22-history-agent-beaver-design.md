# History, Agent Chat, And Beaver Utility Extraction Design

**Context**

The workspace currently shows only the active contract in the history tab, the agent chat input is non-functional, and burn-after-reading still has backend time-based deletion semantics. Beaver also underperforms on utility-price recognition because it depends too heavily on shared entity extraction instead of owning fee extraction from raw contract text.

**Goals**

1. Let authenticated users browse and reopen all in-memory review history available in the current runtime.
2. Change burn-after-reading so deletion happens on logout-triggered cleanup, not automatically shortly after analysis completion.
3. Enable result-page follow-up chat with Owl, Dog, and Beaver using the current contract and report as context.
4. Align frontend analysis progress with backend stages and remove elapsed-second messaging.
5. Make Beaver extract utility and fee signals directly from contract text with its own rules and risk classification.

**Non-Goals**

1. No cross-restart persistence for history or chat in this iteration.
2. No database schema changes.
3. No redesign of the overall workspace layout.

**Architecture**

Backend remains in-process and memory-backed. We add a user-scoped history summary endpoint and an agent-chat endpoint that uses the selected contract plus the current report payload as prompt context. Burn-after-reading keeps contract-level flags but no longer triggers automatic grace-period purging; cleanup remains explicit on logout and still supports immediate purge requests.

Frontend keeps session-scoped state in `App.tsx` for history selection and per-contract/per-agent chat threads. The workspace switches between contracts by loading report data for the chosen history item, without leaving the results shell.

Beaver becomes the source of truth for fee extraction. Deterministic Beaver analysis reads raw contract text, extracts monthly rent, deposit clues, payment pattern, utility phrases, explicit unit prices, and ambiguous fee clauses, then runs compliance checks from its own normalized fee model. Owl entity extraction is no longer required for Beaver utility analysis.

**Data Flow**

1. Upload stores contract metadata and text with `burn_after_reading` on the contract record.
2. Queued analysis produces the final report as before.
3. Workspace startup and history refresh call `/api/contracts/history` to fetch all user-visible report summaries.
4. Selecting a history item fetches `/api/contracts/{contract_id}/report` and swaps the active workspace contract.
5. Agent follow-up chat posts the active agent key, recent messages, and current question to `/api/contracts/{contract_id}/agents/{agent_key}/chat`.
6. Logout always calls burn-after-reading cleanup for the authenticated user; backend purges only contracts flagged for burn-after-reading.

**History Behavior**

1. History lists only contracts owned by the current user and with an available report payload.
2. History cards show filename, location, timestamps, and high/medium/low counts.
3. Reopening history restores the selected contract as the active workspace context.
4. Current runtime TTL stays for general cleanup, but burn-after-reading no longer has a short completion-based purge.

**Burn-After-Reading Behavior**

1. Contracts marked `burn_after_reading=True` remain visible during the active login/runtime.
2. Logout-triggered cleanup deletes all burnable contracts for the authenticated user, regardless of the current UI toggle state.
3. Time-based burn-after-reading grace deletion is removed.

**Agent Chat Behavior**

1. Chat is available inside the result page for Owl, Dog, and Beaver.
2. Each contract keeps separate chat threads per agent in frontend session state.
3. Backend answers with the selected agent persona, contract text, report snapshot, and recent messages.
4. Chat remains session-scoped and is cleared on logout/new app session.

**Beaver Utility Extraction**

Beaver deterministic analysis should:

1. Parse explicit unit-price patterns such as `水费 6 元/吨`, `电费 0.8 元/度`, `燃气费 3 元/方`.
2. Recognize synonymous labels such as `水价`, `电价`, `燃气单价`.
3. Capture ambiguous utility clauses such as `按实际用量收取`, `按民用标准`, `另计`, `据实结算`.
4. Emit normalized status for each utility:
   - explicit_price
   - ambiguous_price
   - missing_price
5. Run compliance checks from Beaver-owned extracted data, not Owl-owned entities.
6. Surface “needs clarification” style issues when the contract references utility charging without a concrete price.

**Testing Strategy**

Add or extend regression coverage for:

1. History listing returns only user-owned completed reports with summary counts.
2. Burn-after-reading contracts survive runtime cleanup before logout and are deleted on explicit cleanup.
3. Agent chat endpoint enforces auth/ownership and returns agent-shaped replies.
4. Beaver detects explicit overcharge, explicit compliant price, and ambiguous utility clauses from raw contract text.
5. Frontend workspace history/chat state utilities behave correctly without regressions.

