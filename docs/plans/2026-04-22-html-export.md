# HTML Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two working result-page exports: a clean HTML report and a merged annotated HTML contract.

**Architecture:** Keep export fully frontend-local so it can reuse the loaded `AnalysisReport` without adding backend endpoints. Build two pure HTML generator functions from the current report/workspace data, then wire the existing download menu buttons in the workspace header to trigger file downloads.

**Tech Stack:** React, TypeScript, Vite, browser Blob download API

---

### Task 1: Add HTML export generator

**Files:**
- Create: `e:\github-program\github-date\租房ai\租房避坑局\src\services\exportHtml.ts`
- Modify: `e:\github-program\github-date\租房ai\租房避坑局\src\components\workspaceData.ts`
- Test: `e:\github-program\github-date\租房ai\租房避坑局\src\services\exportHtml.regression.ts`

**Step 1: Write the export builders**

- Add a pure clean-report HTML builder based on `AnalysisReport`
- Add a pure merged-annotation HTML builder based on `AnalysisReport`
- Reuse workspace-derived annotations and summary counts
- Keep browser download logic separate from HTML string generation

**Step 2: Add minimal helpers for merged annotations**

- Export a helper from `workspaceData.ts` to flatten `owl/dog/beaver` annotations into per-line annotation groups for export

**Step 3: Add regression coverage**

- Verify clean export contains the expected summary and escaped content
- Verify annotated export contains merged agent annotations and original contract lines

### Task 2: Wire the result-page download menu

**Files:**
- Modify: `e:\github-program\github-date\租房ai\租房避坑局\src\components\WorkspaceResultView.tsx`

**Step 1: Replace placeholder alerts**

- Import the new export helpers
- Trigger the clean export from the “导出清洁版” button
- Trigger the annotated export from the “导出标注版” button
- Keep the existing menu interaction and close menu after download

### Task 3: Verify the build

**Files:**
- Test: `e:\github-program\github-date\租房ai\租房避坑局\src\services\exportHtml.regression.ts`

**Step 1: Run regression**

Run: `tsx src/services/exportHtml.regression.ts`

**Step 2: Run production build**

Run: `npm run build`
