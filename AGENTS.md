# PawPal+ — agent reference

Use this file as the **first stop** when onboarding to this repository. It summarizes purpose, architecture intent, file map, and **where implementation stands** relative to the assignment. Prefer linking to detailed docs rather than duplicating them.

**Last aligned with repo:** 2026-03-30 (domain + scheduler: `CareTask.is_due_on`, recurrence, conflict warnings; Streamlit **UI consolidated** — Owner & pets in one flow, **bordered task cards** + humanized labels, **Done today** → `mark_completed` / `mark_incomplete` with **recurring spawn + undo**; **schedule scope** Active pet vs **All pets**; `Scheduler.preview` + `build_plan`; README “Smarter Scheduling” / “Testing PawPal+”; optional `CLAUDE.md` / `code_review_by_claude.md`.)

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
| [app.py](app.py) | Streamlit UI: **Owner** name + **add pet** form → `Owner.add_pet` / `Pet`; **care tasks** (title, duration, priority, optional `HH:MM`, `TaskFrequency`, notes) → `Pet.add_task`; **Done today** checkboxes → `CareTask.mark_completed` / `mark_incomplete` (recurring undo removes auto-spawned next instance when toggled off); **Daily plan**: minutes + scope (**active pet** vs **all pets** → `owner.all_tasks()`), `Scheduler.preview` then `Scheduler.build_plan`, tables + `DailyPlan.warnings` |
| [CLAUDE.md](CLAUDE.md) | Claude Code onboarding: commands, architecture layers, conventions (if present) |
| [code_review_by_claude.md](code_review_by_claude.md) | Narrative code review notes (if present); not part of the assignment rubric |
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
| Streamlit ↔ logic | Connected: `app.py` keeps an `Owner` in `st.session_state` (with `Owner.pets`); add/list pets; add tasks with scheduler-relevant fields; completion UI drives domain methods (incl. recurrence); schedule uses `preview` + `build_plan` and optional **all-pets** task list for cross-pet warnings; warnings surfaced with `st.warning()` |
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
- **UML vs code relationships**: `Owner.pets` + `Owner.add_pet` / `get_pet` are implemented in `pawpal_system.py` and reflected in [CLASS_DIAGRAM.md](CLASS_DIAGRAM.md); keep UI/session state aligned (e.g. selected pet name) without duplicating pet storage outside `Owner`.
- **Ordering source of truth**: avoid implementing two different ordering rules via both `CareTask.__lt__` and `Scheduler._sort_candidates` that can drift over time.
- **Edit tasks** implies stable **`CareTask.id`** and UI state that maps back to domain objects.
- **Packing behavior expectations**: a simple greedy packer is fine, but it must produce consistent, explainable reasons for included vs skipped tasks.
- Prefer **importable, deterministic** scheduler code so tests do not need Streamlit.
- **Conflict detection scope**: current “time conflict” logic is intentionally lightweight (same `"HH:MM"` start time). It emits warnings rather than raising; it does not yet model durations or overlapping time windows.

Details: [DESIGN_CRITIQUE.md](DESIGN_CRITIQUE.md) (gaps, checklist, prompts).

---

## Next target feature workplan (for future agents)

**Done in-repo (high level):** due-day + completion gating via `CareTask.is_due_on`, `daily`/`weekly` recurrence + spawn, lightweight same-`HH:MM` conflict **warnings**, `PawPalBrain.filter_tasks` + `sort_tasks_by_time` helpers, Streamlit wired to preview + plan + all-pets scope.

**Still good next steps:**

- **README “edit tasks”**: stable `CareTask.id` exists; add in-UI edit (or remove task) mapped to domain objects without breaking checkbox session keys.
- **Scheduler ordering**: `_sort_candidates` currently uses priority, then duration, then title — **not** start time. Optionally add a tie-breaker / secondary key on `_hhmm_sort_key(time)` if plans should respect clock order when priorities tie.
- **Owner.preferences**: define keys + wire into `_sort_candidates` (or documented non-use).
- **Richer conflicts**: overlap by duration from `HH:MM`, not only duplicate start times.
- **Where to implement**: `pawpal_system.py` + `tests/test_pawpal_system.py`; UI in `app.py`; track API drift in `DESIGN_CRITIQUE.md`.

**Acceptance checks:** `pytest -q`; manual `streamlit run app.py` — complete a recurring task today, confirm next instance has future `due_day` and today’s plan respects `is_due_on`.

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
| 2026-03-30 | Streamlit UI: removed redundant demo inputs; single Owner & pets section; task cards + **Done today** / recurrence undo; schedule scope **All pets**; `Scheduler.preview` pipeline |
| 2026-03-30 | `AGENTS.md`: refreshed snapshot, `app.py` file-map blurb, **Owner.pets** pitfall correction, revised “next workplan”, `CLAUDE.md` / `code_review_by_claude.md` in file map |

If you rename entrypoints or add a `tests/` layout, add one line here so the next agent knows.
