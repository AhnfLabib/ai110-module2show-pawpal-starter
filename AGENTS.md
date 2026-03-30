# PawPal+ — agent reference

Use this file as the **first stop** when onboarding to this repository. It summarizes purpose, architecture intent, file map, and **where implementation stands** relative to the assignment. Prefer linking to detailed docs rather than duplicating them.

**Last aligned with repo:** 2026-03-30 (starter state: UI shell, no domain/scheduler wired).

---

## What this project is

**PawPal+** is a Codepath AI Module 2 deliverable: a **Streamlit** app that helps a pet owner **plan daily pet care** under a time budget, using **priorities** and (eventually) **owner preferences**, and **explaining why** tasks were chosen or skipped.

Canonical scenario and success criteria: [README.md](README.md).

---

## Architecture intent (domain model)

The intended object model and relationships are documented as Mermaid UML in [CLASS_DIAGRAM.md](CLASS_DIAGRAM.md).

**High level:**

- **Owner**, **Pet** — identity and preferences.
- **CareTask** — title, duration, priority, id, notes; sortable via `priority_score` / ordering.
- **DailyConstraint** — day + minutes available.
- **DailyPlan** — ordered **PlanItem**s (each links a **CareTask**, a **reason**, optional start time), plus totals and **skipped_tasks**.
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
| [app.py](app.py) | Streamlit UI: demo inputs, task list in session state, **schedule button not wired** |
| [pawpal_system.py](pawpal_system.py) | **Placeholder** for backend (`Owner`, `Pet`, `CareTask`, `Scheduler`, etc.) |

No `tests/` or `test_*.py` files yet; PRD expects tests for core scheduling behavior.

---

## Current progress (implementation snapshot)

| Area | Status |
|------|--------|
| UML / design | Documented in `CLASS_DIAGRAM.md` |
| Domain + scheduler code | Not implemented (`pawpal_system.py` is a stub) |
| Streamlit ↔ logic | Not connected; “Generate schedule” shows a placeholder warning |
| Tests | None added |
| Living alignment doc | `DESIGN_CRITIQUE.md` tracks gaps and checklist |

**When you change code meaningfully:** refresh the alignment table and revision log in [DESIGN_CRITIQUE.md](DESIGN_CRITIQUE.md) (see “When to update” there).

---

## Suggested workflow for agents (matches README)

1. Treat [README.md](README.md) as the PRD; treat [CLASS_DIAGRAM.md](CLASS_DIAGRAM.md) as the target API unless revised.
2. Implement domain classes and **Scheduler** in `pawpal_system.py` (or a `pawpal/` package if the repo grows) — keep scheduling **pure** (no Streamlit imports) for testability.
3. Add **pytest** tests: priority under limited time, overflow → `skipped_tasks`, and any preference behavior you add.
4. Wire [app.py](app.py): build real objects from UI state, call `build_plan`, display `DailyPlan` (e.g. `summary()`, `iter_with_reasons()`).
5. Update UML and `DESIGN_CRITIQUE.md` when the public model or behavior diverges from the diagram.

---

## Pitfalls called out in design review

- **Owner.preferences** needs a concrete contract (keys / how `Scheduler` uses them) before it affects sorting.
- **Edit tasks** implies stable **`CareTask.id`** and UI state that maps back to domain objects.
- Prefer **importable, deterministic** scheduler code so tests do not need Streamlit.

Details: [DESIGN_CRITIQUE.md](DESIGN_CRITIQUE.md) (gaps, checklist, prompts).

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

If you rename entrypoints or add a `tests/` layout, add one line here so the next agent knows.
