---
name: refine-backlog
description: 'Refine and maintain the BACKLOG.md file. Use to check item relevance, triage by priority, and identify/add missing requirements or feature gaps.'
argument-hint: 'Provide specific areas to focus on or leave blank for a full review'
---

# Refine Backlog Skill

This skill guides the agent through refining and maintaining the `BACKLOG.md` file, ensuring it remains relevant, properly prioritized, and comprehensive.

## When to Use
- You need to clean up or triage the project's backlog.
- You want to ensure the backlog reflects the current implementation state.
- You need to identify missing requirements, technical debt, or gaps in the current solution.

## Procedure

1. **Review Current State**
   - Read the existing `BACKLOG.md` file (create it if it does not exist).
   - Review the project's core documentation (e.g., `README.md`) and recent source code to understand the current capabilities.

2. **Relevance Check**
   - Evaluate each existing backlog item.
   - Check off or remove items that have already been implemented in the codebase.
   - Remove or flag items that no longer align with the project's architecture or goals.

3. **Triage and Prioritize**
   - Organize the remaining backlog items.
   - **Crucial**: Always ask the user to confirm or set priorities for the items before finalizing the update.

4. **Identify Gaps and Add Items**
   - Compare the codebase's current state against the intended project functionality.
   - Identify missing features, needed testing/documentation, or refactoring opportunities.
   - Add new backlog items for these gaps with a "Draft" status.

5. **Update BACKLOG.md**
   - Write the updated list back to `BACKLOG.md`.
   - Maintain a clean Markdown Table structure with columns: `| Priority | Category | Task | Status |`.