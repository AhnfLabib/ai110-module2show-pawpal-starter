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
| Track care tasks (duration, type of activity) | Yes (`CareTask`; category via `title` / `notes`) | Yes (domain `CareTask`; Streamlit creates tasks and shows tables) | Add `category` later if preferences depend on task kind |
| Consider time available | Yes (`DailyConstraint`) | Yes (UI captures minutes; `Scheduler` packs into budget) | In `main.py`, budget is currently reused per-pet (can over-allocate owner time) |
| Consider priority | Yes (`CareTask`, `priority_score`, ordering) | Yes (`priority_score` + `_sort_candidates` used by scheduler) | Confirm ordering “source of truth” stays in `Scheduler` to avoid drift with `__lt__` |
| Consider owner preferences | Partial (`preferences` dict; how it affects sort not shown) | No (stored but not applied) | Define preference keys + implement in `_sort_candidates` with a test |
| Basic owner + pet info | Yes (`Owner`, `Pet`) | Yes (`Owner`/`Pet` objects persisted in `st.session_state`) | |
| Add / edit tasks | Partial (`CareTask.id` exists but lifecycle not modeled) | Partial (add works; edit/delete not implemented) | Editing implies stable `CareTask.id` and a UI mapping back to a specific task |
| Generate daily plan from constraints + priorities | Yes (`Scheduler.build_plan`) | Yes (wired in `app.py` for the active pet; CLI demo in `main.py`) | Consider adding a cross-pet “single owner budget” plan mode later |
| Display plan + reasoning | Partial (`DailyPlan`, `PlanItem.reason`) | Partial (scheduled-task reasons shown; skipped tasks listed without per-task reasons) | Option: attach skip reasons or include a plan trace for explanation |
| Tests for key scheduling behaviors | — | Yes (`tests/test_pawpal_system.py`) | Keep tests Streamlit-free and deterministic |

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

---

## Workplan: sorting + filtering + recurring tasks + conflict detection

Target feature: **“Implement logic for sorting tasks by time, filtering by pet/status, handling recurring tasks, and basic conflict detection.”**

This plan is designed to be incremental: each step is testable and UI-friendly without requiring a full calendar/time-of-day system.

### Scope (define “done”)

- **Sorting by time**:
  - Deterministic ordering for candidates (e.g., prioritize by priority first, then duration as a tie-break).
  - Deterministic ordering for plan items (order index already provides this).
- **Filtering**:
  - Filter tasks by **pet** (already happens via `Pet.list_tasks(...)` / `PawPalBrain.tasks_for_pet(...)`).
  - Filter tasks by **status** (completed vs incomplete, and “completed today” behavior for scheduling).
- **Recurring tasks**:
  - Use `CareTask.frequency` to decide whether a “completed” task is still due on `constraint.day`.
  - Keep it simple (daily/weekly/once/as_needed); do not add multi-day plan generation.
- **Basic conflict detection**:
  - Detect and surface *data-level* conflicts (e.g., duplicate task IDs within a pet, invalid durations) and *schedule-level* conflicts (e.g., selected tasks exceed budget should never happen; overlapping times only if start times exist).
  - If time-of-day is not modeled, treat “conflict detection” as **impossible/inconsistent inputs** plus **budget overflow**.

### Proposed implementation steps (small, test-driven)

1. **Centralize “due-ness” logic** (recurrence + completion)
   - Add a helper on `CareTask` or in `Scheduler`:
     - `CareTask.is_due_on(day: date) -> bool` (recommended) OR
     - `Scheduler._is_due(task, constraint.day) -> bool`
   - Rules (simple and explainable):
     - `once`: due if not completed
     - `daily`: due if last_completed_day != day
     - `weekly`: due if last_completed_day is None or (day - last_completed_day).days >= 7
     - `as_needed`: due if not completed (or always due; pick one and document it)

2. **Filtering pipeline in one place**
   - Make `Scheduler._sort_candidates(...)` the single “source of truth” for:
     - filtering non-due tasks (via step 1)
     - filtering invalid durations (<=0)
     - applying preference-based boosts/penalties (later)
   - Ensure UI uses `pet.list_tasks(include_completed=True)` but scheduler decides “due today”.

3. **Sorting improvements (“by time”)**
   - Keep the current stable rule but formalize it as a policy:
     - Primary: priority (desc)
     - Secondary: duration (asc) OR “value per minute” score (desc)
     - Tertiary: title (asc)
   - Add at least one test asserting ordering under ties.

4. **Recurring tasks in the plan output**
   - Update `DailyPlan.summary()` or reasons to mention when a task is recurring (optional).
   - If a task is not due, it should not appear in `items` nor `skipped_tasks` (it’s neither “skipped” nor “selected”; it’s “not a candidate”).

5. **Basic conflict detection output**
   - Add a lightweight collection to `DailyPlan`, e.g. `warnings: list[str]` (or similar), for:
     - invalid task durations encountered
     - tasks dropped as non-due (optional)
   - If you don’t want to change the public model, you can still compute warnings in UI for now, but prefer the plan to carry them so tests can cover.

### Test plan (minimal additions)

Add tests in `tests/test_pawpal_system.py`:

- **Recurring: daily**: a daily task completed today is not scheduled; same task completed yesterday is scheduled.
- **Recurring: weekly**: completed within last 6 days is not scheduled; completed 7+ days ago is scheduled.
- **Sorting by time tie-break**: two tasks same priority → shorter duration scheduled first when budget is tight.
- **Filtering by pet/status**: when scheduling for pet A, tasks for pet B never considered (already implicit via UI; test at domain level using `PawPalBrain.tasks_for_pet` + scheduler).
- **Conflict detection (data-level)**: invalid duration tasks are excluded and a warning exists (if warnings are implemented).

### Notes / non-goals (keep it small)

- No real “overlap” conflicts until you introduce `start_time`/time windows. Until then, “conflicts” should mean **bad inputs** or **budget violations**.
- If you later add time windows (morning/evening), conflict detection can become “cannot fit tasks into windows,” but that’s out of scope for this target feature.

---

## Algorithm review (example): simplify `Scheduler._sort_candidates`

Current implementation in `pawpal_system.py` performs filtering via a manual loop into `filtered`, then calls `sorted(filtered, key=...)`. It works, but it is more verbose than necessary and repeats “filtering policy” inline.

**Why simplify**

- **Readability**: filtering rules are easier to scan when expressed as a single predicate and a list comprehension.
- **Maintainability**: when you add recurrence rules (daily/weekly), you want one obvious place to update.
- **Performance**: negligible difference for small lists, but fewer lines/branches reduces bug surface.

**Suggested simplification (same behavior, clearer structure)**

- Extract a small predicate (either a nested function or a private helper like `_is_candidate_for_day(task, constraint)`).
- Use a list comprehension to filter.
- Keep the sort key as-is (or wrap it in a named function for readability).

Pseudo-shape:

- `candidates = [t for t in tasks if is_candidate(t, constraint)]`
- `return sorted(candidates, key=sort_key)`

Where `is_candidate` captures today-completion + due-day filtering (and later: recurrence `frequency` and invalid durations).

**Optional small improvement**

If you adopt `CareTask.is_due_on(day)` (from the workplan), then `_sort_candidates` can become almost self-documenting:

- filter `t.is_due_on(constraint.day)`
- sort by `(-t.priority_score(), t.duration_minutes, t.title.lower())`

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
| 2026-03-30 | Refreshed alignment table to reflect current implementation (domain + scheduler + Streamlit wiring + tests); documented remaining gaps (preferences, edit tasks, cross-pet budget realism, skip reasons) | README requirements, `app.py` flow, `pawpal_system.py` scheduler, tests |
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
