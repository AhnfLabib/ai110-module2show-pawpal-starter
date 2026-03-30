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
| Add / edit tasks | — (domain diagram only) | Partial (add only in starter; no domain objects) | Editing implies stable `id` on `CareTask` |
| Generate daily plan from constraints + priorities | Yes (`Scheduler.build_plan`) | No | |
| Display plan + reasoning | Partial (`DailyPlan`, `PlanItem.reason`) | No | UI should consume `summary()` / `iter_with_reasons()` |
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

1. **Preferences are not operational in the diagram** — `Owner.preferences` is a `dict` with no documented keys or methods. Decide how `_sort_candidates` (or `build_plan`) consumes them; update UML or add a short “preference contract” bullet here.
2. **Add/edit tasks vs domain-only UML** — The diagram does not model where tasks live between requests. Accept as boundary, or add a note when you introduce persistence / session state tied to `CareTask.id`.
3. **Task kinds from scenario** — Walks, meds, grooming, etc. are only implied by `title`. Enough for v1; revisit if rules become category-based.
4. **Traceability** — `DailyPlan` does not reference `Pet` or `Owner`. Fine if plans are anonymous snapshots; add fields if you need audit text (“Plan for Mochi on 2026-03-30”).
5. **Tests** — PRD requires them; keep scheduling logic importable without Streamlit so tests stay fast and deterministic.

## Implementation checklist (for you)

Use this before calling a milestone “done”:

- [ ] `build_plan` runs on real `CareTask` / `DailyConstraint` instances from UI or test fixtures
- [ ] At least one test: higher-priority (or higher score) tasks preferred when time is limited
- [ ] At least one test: tasks that do not fit appear in `skipped_tasks` (or equivalent behavior)
- [ ] Plan output is shown in Streamlit with human-readable reasons
- [ ] `CLASS_DIAGRAM.md` updated if public API or relationships changed
- [ ] This doc: alignment table + revision log updated

---

## Revision log

Newest first.

| Date | Change | What we re-checked |
|------|--------|-------------------|
| 2026-03-30 | Initial critique doc created from README + `CLASS_DIAGRAM.md`; starter `app.py` has no scheduler yet | Full alignment table, gaps list |

---

## Quick prompts for your next self-review

Answer in one line each after a big change:

1. Did the **PRD row** for that feature move from Partial/No to Yes?
2. Did **UML** gain/lose a class or method that tests or UI now depend on?
3. Is there **one test** that would fail if scheduling regressed?
4. Can a new reader understand **owner preferences** from code + diagram alone?

If any answer is “no,” that is your next improvement target.
