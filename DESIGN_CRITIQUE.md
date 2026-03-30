# PawPal+ design critique (living doc)

Use this when you need **grounded guidance**: how the **product requirements** (`README.md`), **UML** (`CLASS_DIAGRAM.md`), and **implementation** line up—and where the gaps are.

**Update this file after each major change** (see [When to update](#when-to-update)).

---

## Sources of truth

| Source | Role |
|--------|------|
| [README.md](README.md) | Scenario + “what you will build” (treat as PRD) |
| [CLASS_DIAGRAM.md](CLASS_DIAGRAM.md) | Intended domain model (Mermaid UML) |
| [app.py](app.py) | Streamlit UI and wiring to logic |
| Tests (`tests/` or `test_*.py`, when added) | Behavior contracts for scheduling |

---

## When to update

Update at least a **revision log** row and any affected checklist cells after:

- UML edits in `CLASS_DIAGRAM.md`
- New or changed domain classes / scheduler API
- Meaningful `app.py` integration (inputs → scheduler → display)
- New tests or changed scheduling behavior
- Intentional scope changes (what you are *not* building)

*Minor typo fixes in comments only—skip the log, or note as “nit” in the log.*

---

## PRD ↔ design ↔ code alignment

Legend: **Yes** = explicitly covered · **Partial** = implied or incomplete · **No** = missing · **—** = not applicable yet

| PRD requirement (from README) | CLASS_DIAGRAM | Implementation (current) | Notes |
|--------------------------------|---------------|--------------------------|-------|
| Track care tasks (duration, type of activity) | Yes (`CareTask`; category via `title` / `notes`) | Partial (UI dicts only) | Add `category` later if preferences depend on task kind |
| Consider time available | Yes (`DailyConstraint`) | No | |
| Consider priority | Yes (`CareTask`, `priority_score`, ordering) | Partial (UI only) | |
| Consider owner preferences | Partial (`preferences` dict; how it affects sort not shown) | No | Define how `Scheduler` reads preferences |
| Basic owner + pet info | Yes (`Owner`, `Pet`) | Partial (`app.py` inputs, not wired to classes) | |
| Add / edit tasks | Partial (`CareTask.id` exists but lifecycle not modeled) | Partial (add only in starter; no domain objects) | Editing implies stable `id` on `CareTask` and UI → domain mapping |
| Generate daily plan from constraints + priorities | Yes (`Scheduler.build_plan`) | No | |
| Display plan + reasoning | Partial (`DailyPlan`, `PlanItem.reason`) | No | Consider adding plan traceability (pet/day) if needed for display text |
| Tests for key scheduling behaviors | — | No | Prefer pure `Scheduler` tests, no Streamlit |

*Refresh the “Implementation” column whenever code changes.*

---

## What the UML does well

- **Single orchestration point**: `Scheduler.build_plan` matches “generate a daily schedule.”
- **Explanation hooks**: `PlanItem.reason`, `_explain_choice`, `DailyPlan.iter_with_reasons` / `summary` align with “explain why it chose that plan.”
- **Budget realism**: `leftover_minutes`, `skipped_tasks` support edge cases when time is tight.
- **Multi-pet-ready**: `Owner` → `0..*` `Pet` matches “pet(s)” in the scenario.
- **Comparable tasks**: `priority_score` / `__lt__` signal a clear sort contract for scheduling.

## Gaps and risks (prioritized)

1. **Preferences are not operational (yet)** — `Owner.preferences` is a `dict` with no contract. If you want “preferences” to count as implemented, you need: (a) defined keys, and (b) a single place in `Scheduler` where those keys influence ordering/selection, and (c) a test that proves it.
2. **Owner↔Pet relationship mismatch (UML vs code)** — UML models `Owner cares_for Pets`, but `pawpal_system.py` currently has no `Owner.pets`. Decide whether this relationship is *stored in domain objects* (add `Owner.pets`) or *managed externally by UI/state* (then adjust UML/notes so it’s not misleading).
3. **Two ordering mechanisms can diverge** — UML/code provide both `CareTask.__lt__` and a planned `_sort_candidates`. If both exist, it’s easy to accidentally use different rules in different codepaths (e.g., `sorted(tasks)` vs `_sort_candidates`). Pick a single “source of truth” for ordering.
4. **Add/edit tasks needs stable identity** — `CareTask.id` exists but defaults to empty; editing implies IDs are stable and unique per task across Streamlit reruns/session state. If IDs aren’t stable, “edit” becomes error-prone.
5. **Packing strategy can surprise users** — A greedy “sort then fill” algorithm is simplest, but can produce unintuitive outcomes (one long high-priority task blocks many shorter tasks). This isn’t wrong, but it must be explained consistently via `PlanItem.reason` / `_explain_choice`.
6. **Validation gaps** — Durations and budgets aren’t constrained in the domain model; negative/zero values can break packing logic and reasons. Decide where validation lives (domain constructors vs scheduler).
7. **Traceability** — `DailyPlan` doesn’t carry `pet`/`day`/`constraint`. Fine for a pure output object, but the UI may want “Plan for {pet} on {day}” without rebuilding context elsewhere.
8. **Tests** — PRD requires them; keep scheduling logic importable without Streamlit so tests stay fast and deterministic.

---

## Preference contract (define before implementing “preferences”)

Keep this intentionally small; add keys only when you have a behavior + test.

- **Scope**: preferences affect **ordering** (via `_sort_candidates`) and/or **selection** (via `_pack_into_budget`), and reasons must reflect the effect.
- **Minimum viable contract (suggested)**:
  - `max_tasks_per_day: int` (cap selected tasks even if time remains)
  - `deprioritize_keywords: list[str]` (lower score if title/notes match)
  - `prioritize_keywords: list[str]` (higher score if match)
- **Non-goals for v1**: complex time-of-day scheduling, multi-day plans, per-task recurrence.

## Implementation checklist (for you)

Use this before calling a milestone “done”:

- [ ] `build_plan` runs on real `CareTask` / `DailyConstraint` instances from UI or test fixtures
- [ ] At least one test: higher-priority (or higher score) tasks preferred when time is limited
- [ ] At least one test: tasks that do not fit appear in `skipped_tasks` (or equivalent behavior)
- [ ] At least one test: a preference key changes ordering/selection (only once you claim “preferences supported”)
- [ ] Plan output is shown in Streamlit with human-readable reasons
- [ ] `CLASS_DIAGRAM.md` updated if public API or relationships changed
- [ ] This doc: alignment table + revision log updated

---

## Revision log

Newest first.

| Date | Change | What we re-checked |
|------|--------|-------------------|
| 2026-03-30 | Updated critique with concrete gaps from `pawpal_system.py` (Owner↔Pet mismatch, ordering divergence risk, stable IDs, packing explanation, validation, traceability); added a minimal “preference contract” section | Alignment table, gaps list, checklist |
| 2026-03-30 | Initial critique doc created from README + `CLASS_DIAGRAM.md`; starter `app.py` has no scheduler yet | Full alignment table, gaps list |

---

## Quick prompts for your next self-review

Answer in one line each after a big change:

1. Did the **PRD row** for that feature move from Partial/No to Yes?
2. Did **UML** gain/lose a class or method that tests or UI now depend on?
3. Is there **one test** that would fail if scheduling regressed?
4. Can a new reader understand **owner preferences** from code + diagram alone?

If any answer is “no,” that is your next improvement target.
