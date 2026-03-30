# PawPal+ — agent reference

Use this file as the **first stop** when onboarding to this repository. It summarizes purpose, architecture intent, file map, and **where implementation stands** relative to the assignment. Prefer linking to detailed docs rather than duplicating them.

**Last aligned with repo:** 2026-03-30 (domain + scheduler implemented; Streamlit UI wired to scheduler; time sorting + task filtering added; recurring task auto-spawn added; lightweight conflict warnings added; candidate filtering centralized via `CareTask.is_due_on`; README updated with “Smarter Scheduling” + “Testing PawPal+”).

---

## What this project is

**PawPal+** is a Codepath AI Module 2 deliverable: a **Streamlit** app that helps a pet owner **plan daily pet care** under a time budget, using **priorities** and (eventually) **owner preferences**, and **explaining why** tasks were chosen or skipped.

Canonical scenario and success criteria: [README.md](README.md).

---

## Architecture intent (domain model)

The intended object model and relationships are documented as Mermaid UML in [CLASS_DIAGRAM.md](CLASS_DIAGRAM.md).

**High level:**

- **Owner**, **Pet** — identity and preferences.
- **CareTask** — title, duration, priority, id, notes, optional `time` (`"HH:MM"`), and lightweight `pet_name` provenance (auto-populated by `Pet.add_task`) for cross-pet scheduling + warnings; sortable via `priority_score` / ordering and (optionally) by `time`.
- Recurring behavior: `CareTask.frequency` supports `daily`/`weekly`; completing a recurring task spawns the **next instance** with a `due_day` set using `timedelta` (daily: +1 day, weekly: +7 days).
- **DailyConstraint** — day + minutes available.
- **DailyPlan** — ordered **PlanItem**s (each links a **CareTask**, a **reason**, optional start time), plus totals, **skipped_tasks**, and non-fatal **warnings** (e.g., time conflicts).
- **Scheduler** — `build_plan(owner, pet, tasks, constraint) -> DailyPlan`; internal helpers for sorting, packing into the time budget, and explaining choices.

Agents implementing logic should match this API unless the student intentionally revises the UML (then update `CLASS_DIAGRAM.md` and [DESIGN_CRITIQUE.md](DESIGN_CRITIQUE.md)).

---

## File map

| Path | Role |
|------|------|
| [README.md](README.md) | Assignment / PRD: scenario, required features, setup, workflow |
| [CLASS_DIAGRAM.md](CLASS_DIAGRAM.md) | Target domain model (classes, methods, relationships) |
| [DESIGN_CRITIQUE.md](DESIGN_CRITIQUE.md) | PRD ↔ UML ↔ code alignment table, gaps, checklist, revision log |
| [reflection.md](reflection.md) | Student reflection template (prompts only; fill as you go) |
| [requirements.txt](requirements.txt) | `streamlit`, `pytest` |
| [app.py](app.py) | Streamlit UI: **Add pet** → `Owner.add_pet`; **Add task** → `Pet.add_task`; **Generate schedule** builds a real `DailyPlan` via `Scheduler.build_plan` using tasks from the selected pet |
| [pawpal_system.py](pawpal_system.py) | Backend domain + scheduler (`Owner`, `Pet`, `CareTask`, `DailyPlan`, `Scheduler`, etc.) — keep pure (no Streamlit) |
| [main.py](main.py) | **Temporary test ground**: CLI trial harness that runs multiple scenarios (today/tomorrow, tight budgets, recurrence, time conflicts) and prints raw vs candidate vs scheduled outputs |
| [tests/test_pawpal_system.py](tests/test_pawpal_system.py) | Pytest coverage for domain + scheduler; includes task add/complete, time sorting, recurrence gating, and conflict-warning behaviors |

PRD expects tests for core scheduling behavior; this repo now includes `tests/test_pawpal_system.py`.

---

## Current progress (implementation snapshot)

| Area | Status |
|------|--------|
| UML / design | Documented in `CLASS_DIAGRAM.md` |
| Domain + scheduler code | Implemented in `pawpal_system.py` (tasks, pets, multi-pet brain, greedy scheduler; `CareTask.time` + time sorting helpers; centralized “candidate due-ness” via `CareTask.is_due_on(day)`) |
| Recurring tasks | Implemented in `pawpal_system.py`: `CareTask.mark_completed()` spawns the next instance for `daily`/`weekly` tasks and sets `due_day`; `Scheduler._sort_candidates()` filters out tasks not due yet |
| Conflict detection (lightweight) | Implemented as non-fatal warnings: if 2+ scheduled tasks share the same valid `CareTask.time` (`"HH:MM"`), scheduler adds a warning message (same pet vs different pets) to `DailyPlan.warnings` |
| Streamlit ↔ logic | Connected: `app.py` persists domain objects in `st.session_state`; “Add pet” calls `Owner.add_pet`; “Add task” calls `Pet.add_task`; “Generate schedule” calls `Scheduler.build_plan` using tasks from the active pet; UI displays `DailyPlan.warnings` via `st.warning()` |
| Tests | Added pytest coverage for core domain + scheduling (`tests/test_pawpal_system.py`) incl. time sorting, recurrence gating semantics, and conflict warnings |
| CLI test script | `main.py` now runs multiple terminal “trials” to validate algorithm changes: due-day gating, recurrence auto-spawn, candidate filtering via `CareTask.is_due_on`, budget packing/skips, and same-time conflict warnings |
| Living alignment doc | `DESIGN_CRITIQUE.md` tracks gaps and checklist |

**When you change code meaningfully:** refresh the alignment table and revision log in [DESIGN_CRITIQUE.md](DESIGN_CRITIQUE.md) (see “When to update” there).

---

## Suggested workflow for agents (matches README)

1. Treat [README.md](README.md) as the PRD; treat [CLASS_DIAGRAM.md](CLASS_DIAGRAM.md) as the target API unless revised.
2. Domain and scheduling live in `pawpal_system.py` — keep it **pure** (no Streamlit imports) for testability.
3. Add/extend **pytest** tests when behavior changes (`pytest -q`).
4. Wire [app.py](app.py): build real objects from UI state, call `Scheduler.build_plan`, display `DailyPlan` (e.g. `summary()`, `iter_with_reasons()`).
5. Update UML and `DESIGN_CRITIQUE.md` when the public model or behavior diverges from the diagram (e.g., multi-pet storage via `Owner.pets` and `PawPalBrain`).

---

## Pitfalls called out in design review

- **Owner.preferences** needs a concrete contract (keys / how `Scheduler` uses them) before it affects sorting.
- **UML vs code relationships**: `CLASS_DIAGRAM.md` shows `Owner cares_for Pets`, but `pawpal_system.py` currently does not store pets on `Owner`. Decide whether the relationship is stored in-domain or managed by UI/session state; update UML/docs accordingly.
- **Ordering source of truth**: avoid implementing two different ordering rules via both `CareTask.__lt__` and `Scheduler._sort_candidates` that can drift over time.
- **Edit tasks** implies stable **`CareTask.id`** and UI state that maps back to domain objects.
- **Packing behavior expectations**: a simple greedy packer is fine, but it must produce consistent, explainable reasons for included vs skipped tasks.
- Prefer **importable, deterministic** scheduler code so tests do not need Streamlit.
- **Conflict detection scope**: current “time conflict” logic is intentionally lightweight (same `"HH:MM"` start time). It emits warnings rather than raising; it does not yet model durations or overlapping time windows.

Details: [DESIGN_CRITIQUE.md](DESIGN_CRITIQUE.md) (gaps, checklist, prompts).

---

## Next target feature workplan (for future agents)

Target: **“sorting tasks by time, filtering by pet/status, handling recurring tasks, and basic conflict detection.”**

- **Where to implement**
 - **Core logic**: `pawpal_system.py` (`CareTask.time`, `sort_tasks_by_time`, `PawPalBrain.filter_tasks`, `Scheduler._sort_candidates`, `Scheduler._pack_into_budget`, reasons)
 - **Tests**: `tests/test_pawpal_system.py` (add recurrence + time sorting + filtering tests)
  - **Design guidance**: `DESIGN_CRITIQUE.md` → sections:
    - **“Workplan: sorting + filtering + recurring tasks + conflict detection”**
    - **“Algorithm review (example): simplify `Scheduler._sort_candidates`”** (recommended refactor as filtering rules grow)

- **Suggested approach**
 - **Time sorting**: store a string `CareTask.time` in `"HH:MM"` format, and sort with a `key=lambda t: ...` (invalid/missing times should sort last).
 - **Recurring tasks**: completing a `daily`/`weekly` task spawns a new instance with `due_day` computed via `timedelta` (daily +1 day, weekly +7 days); scheduler filters out tasks whose `due_day` is in the future.
 - **Filtering**: keep “due today” filtering inside scheduler for correctness; use `CareTask.is_due_on(day)` as the single predicate for candidate inclusion (today-completion + `due_day` gating).
 - **Conflict detection**: treat “conflicts” as **warnings** (never exceptions). Current implementation flags 2+ scheduled tasks with the same valid `"HH:MM"` time; future work could extend this to interval overlap once start times and durations are used for scheduling.

- **Acceptance checks**
  - Run `pytest -q` and confirm new tests cover daily/weekly recurrence behaviors.
  - Run `streamlit run app.py` and confirm a task completed today does not appear in today’s schedule when frequency makes it not due.

---

## Setup (verify environment)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Changelog (this file)

| Date | Note |
|------|------|
| 2026-03-30 | Initial `AGENTS.md`: overview, file map, progress snapshot, pointers to README / UML / critique |
| 2026-03-30 | Implemented `pawpal_system.py` core domain + `Scheduler`; added `tests/` + `pytest.ini` |
| 2026-03-30 | Added `main.py` temporary CLI script to print a schedule using the domain + scheduler |
| 2026-03-30 | Refined `tests/test_pawpal_system.py` to verify task addition + completion (incl. duplicate IDs and completion-day filtering) |
| 2026-03-30 | Wired `app.py` to `pawpal_system.py`: “Add pet” → `Owner.add_pet`; “Add task” → `Pet.add_task`; “Generate schedule” → `Scheduler.build_plan` |
| 2026-03-30 | Persisted `Owner` + `Pet` in Streamlit `st.session_state` (reuse across reruns/navigation) |
| 2026-03-30 | Added a focused workplan pointer for recurrence/sorting/filtering/conflict detection to speed up future iterations |
| 2026-03-30 | Added `CareTask.time` (`"HH:MM"`) + time sorting helper and `PawPalBrain.filter_tasks` (filter by completed and/or pet name) |
| 2026-03-30 | Added recurring task automation: completing `daily`/`weekly` tasks spawns the next instance with `due_day` (`timedelta`), and scheduler filters out not-due tasks; added pytest coverage |
| 2026-03-30 | Added lightweight conflict detection: `DailyPlan.warnings` + `CareTask.pet_name` provenance; scheduler warns on same-time tasks; UI displays warnings |
| 2026-03-30 | Added pointer to algorithm simplification notes for `Scheduler._sort_candidates` in `DESIGN_CRITIQUE.md` |
| 2026-03-30 | Centralized scheduler candidate filtering in `CareTask.is_due_on(day)`; simplified `Scheduler._sort_candidates` to a predicate + list comprehension |
| 2026-03-30 | Expanded `tests/test_pawpal_system.py` with focused tests for time sorting, daily recurrence due gating through `Scheduler`, and same-time conflict warnings |
| 2026-03-30 | Updated `README.md` with “Smarter Scheduling” and “Testing PawPal+” sections (incl. `pytest -q` command and confidence rating) |
| 2026-03-30 | Updated `.gitignore` to ignore repo-local operational files (`AGENTS.md`, `pytest.ini`) |

If you rename entrypoints or add a `tests/` layout, add one line here so the next agent knows.
