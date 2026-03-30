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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- **Tradeoff:** The scheduler uses a **greedy packer** (sort by priority, then add tasks until the time budget is full) instead of searching for the globally “best” combination of tasks.
- **Why reasonable:** It’s simple, fast, and easy to explain (“higher priority first; skip what doesn’t fit”), which matters more for a daily helper app than perfectly optimal packing.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
