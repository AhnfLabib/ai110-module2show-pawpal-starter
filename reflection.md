# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- **UML:** Domain objects (`Owner`, `Pet`, `CareTask`) plus a **`Scheduler`** that reads a **daily time budget** and outputs a **`DailyPlan`** (ordered tasks + short **reasons**). UI only displays what the scheduler returns.

- **Classes:** `Owner`/`Pet` — basic info and preferences; `CareTask` — title, duration, priority; `DailyConstraint` (or fields on owner) — minutes available; `DailyPlan` — scheduled order; `Scheduler` — pick/fit tasks and explain tradeoffs (e.g. priority vs leftover time).




**b. Design changes**

- **Yes.** After comparing the PRD/UML/implementation in `DESIGN_CRITIQUE.md`, I tightened the design in a few places to reduce ambiguity and future bugs.
- **Preferences became a small contract (not just a dict):** define a couple of keys (e.g., keyword boosts/caps) and apply them in one place in the scheduler, with reasons + a test, so “preferences” is real behavior.
- **Clarified relationships + ordering:** decide whether `Owner` actually stores `pets` (or the UI owns that), and keep **one source of truth** for task ordering (avoid both `CareTask.__lt__` and separate scheduler sorting drifting apart). I also noted the need for stable `CareTask.id` to support edit, and consistent “why included/why skipped” output for a greedy packer.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- **Constraints considered:** (1) **daily time budget** (`DailyConstraint.minutes_available`), (2) **priority** (high/medium/low → `priority_score`), and (3) basic **eligibility** rules like “not due yet” (`due_day`) and “already completed today” (`last_completed_day`). Tasks with invalid durations (≤0) are skipped.
- **What mattered most:** I prioritized **time budget + priority** first because the PRD’s core promise is “fit what matters into limited time.” Due/completion filters keep plans realistic, and preferences are a planned extension once they have a clear contract + tests.

**b. Tradeoffs**

- **Tradeoff:** The scheduler uses a **greedy packer** (sort by priority, then add tasks until the time budget is full) instead of searching for the globally “best” combination of tasks.
- **Why reasonable:** It’s simple, fast, and easy to explain (“higher priority first; skip what doesn’t fit”), which matters more for a daily helper app than perfectly optimal packing.

---

## 3. AI Collaboration

**a. How you used AI**

- **Cursor chat experience:** I used Cursor chat as a “pair designer” to turn the PRD + UML into concrete APIs, then iterated quickly by asking for small changes with `@` file context (e.g. “make `Scheduler.build_plan` pure and testable,” “add skipped tasks + reasons,” “write pytest cases for overflow and due dates”).
- **Most effective feature for building the scheduler:** Having chat read the *exact* code context (the current `pawpal_system.py` + failing tests) and propose targeted edits/tests was the biggest accelerator—especially for getting the scheduler’s **sorting + packing** behavior and edge cases (0 minutes, negative durations, due dates) consistent.

**b. Judgment and verification**

- **Example I rejected/modified:** An AI suggestion pushed toward a more “optimal” scheduler (knapsack-style selection or modeling time overlaps). I kept the design **greedy + explainable** (priority-first pack) and only added lightweight time conflict *warnings* for exact start-time matches, because that preserves a clean, testable core and matches the project scope.
- **How I verified:** I encoded the intended behavior as pytest cases (priority order under tight budgets, overflow → `skipped_tasks`, due-day filtering, completed-today filtering). If a change broke a test or made reasons inconsistent with the actual selection, I adjusted the design back to a single clear contract.

---

## 4. Testing and Verification

**a. What you tested**

- **Behaviors:** empty inputs, zero/negative budgets and durations, priority sorting under limited minutes, overflow → `skipped_tasks`, due-date filtering, completed-today filtering, and recurrence spawning for daily/weekly tasks.
- **Why important:** these are the failure modes that would silently produce a “bad plan” for a user, so tests act like the scheduler’s spec and keep the logic stable while the UI evolves.

**b. Confidence**

- **Confidence:** fairly confident for the current v1 scope (priority-first packing + due/completion rules) because the core behaviors are covered by deterministic unit tests.
- **Next edge cases:** tie-breaking rules (same priority), preference-based reordering once preferences are implemented, multi-pet scheduling interactions, and richer time logic (overlaps vs exact start times).

---

## 5. Reflection

**a. What went well**

- I’m most satisfied with keeping the scheduler **pure and testable** (no Streamlit dependency), while still producing user-facing outputs (`DailyPlan`, `skipped_tasks`, reasons/warnings) that the UI can display directly.

**b. What you would improve**

- I would formalize **owner preferences** into a small, versioned contract (with 1–2 behaviors + tests), and improve time handling beyond exact-match warnings (true overlap checks and/or optional time windows).

**c. Key takeaway**

- Collaborating with powerful AI made me faster, but it only stayed “clean” when I acted as the **lead architect**: define contracts, keep one source of truth for ordering/selection, demand tests for new behavior, and resist over-engineering that expands scope without improving the user experience.
