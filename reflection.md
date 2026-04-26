# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

- Enter or update basic owner and pet information so the assistant knows who is caring for which animal.
- Add and edit care tasks (walks, feeding, medication, enrichment, grooming, and similar) with enough detail—such as duration and priority—for the system to weigh tradeoffs.
- Generate a daily plan that respects constraints and priorities, view the schedule clearly, and read a short explanation of why the assistant chose that ordering.

**a. Initial design**

The initial UML design has four classes:

- **Owner** — Represents the pet owner. Stores their name, how many minutes they have available per day, and a preferences dictionary. Responsible for updating its own profile via `update_profile()`.
- **CareTask** (dataclass) — A single care activity such as a walk, feeding, or grooming session. Each task has a title, category, duration in minutes, and a priority level. It can edit its own fields and compare priority against another task.
- **Pet** (dataclass) — Represents one pet owned by the Owner. Holds a name, species, optional notes, and a list of CareTask objects. Responsible for adding tasks and listing them.
- **Planner** — The scheduling engine. It reads constraints from the Owner (available time, preferences), selects and orders CareTask objects for a given Pet, and produces a daily plan. It also generates a human-readable explanation of its reasoning. A private helper `_fits_within_budget()` checks whether a set of tasks fits the owner's time budget.

Relationships: Owner owns zero-or-more Pets; each Pet has zero-or-more CareTasks; Planner depends on all three to build a plan.

**b. Design changes**

Yes. After reviewing the skeleton against the UML, I noticed that the `Owner` class had no `pets` field even though the UML specifies an `Owner "1" --> "0..*" Pet` relationship. I added a `pets: list[Pet]` field to `Owner` so that the one-to-many ownership relationship is represented directly in code, matching the UML diagram. Without this, there would be no way to navigate from an Owner to their Pets without passing them around separately.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three main constraints: the owner's **available minutes per day** (hard cap on total task duration), each task's **priority level** (1–5, determines selection order), and **scheduled time slots** (used for conflict detection and chronological display). Priority was treated as the most important constraint because in pet care, missing a critical task like medication or an exercise walk has worse consequences than missing a lower-priority grooming session. Time budget acts as the hard boundary—no plan exceeds it.

**b. Tradeoffs**

The scheduler uses a **greedy priority-first** algorithm: it sorts all tasks by priority (highest first) and adds them one by one until the owner's time budget is full. This means a high-priority task is always chosen over a lower-priority one, even if skipping it would allow two smaller tasks to fit and cover more total care. For example, a 45-minute walk (priority 5) will be chosen over a 20-minute feeding + 20-minute grooming (priority 4 each), even though the two smaller tasks together provide broader coverage.

This tradeoff is reasonable because in pet care, missing a critical task (like medication or a walk for a high-energy dog) is worse than missing two lower-priority ones. The owner can always adjust priorities if they disagree with the plan. A more optimal knapsack-style algorithm would be harder to understand and explain, which conflicts with the app's goal of providing clear reasoning for its choices.

---

## 3. AI Collaboration

**a. How you used AI**

AI was used across every phase of the project: UML design brainstorming, skeleton generation, implementing scheduling algorithms, writing the test suite, and wiring the Streamlit UI. The most effective approach was using **separate chat sessions for each phase**—one for design, one for core logic, one for testing, and one for UI polish. This kept each conversation focused: the design session stayed at the architecture level without drifting into implementation details, the testing session could focus purely on edge cases without being distracted by UI concerns, and the UI session could reference the finalized backend without revisiting design decisions. It also prevented context overload—each session had a clear goal and a clean starting point.

The most helpful prompts were specific and constrained, like "What are the most important edge cases to test for a pet scheduler with sorting and recurring tasks?" or referencing a specific file and asking for updates to the UML. Open-ended prompts like "make this better" were less useful because they invited unnecessary refactoring.

**b. Judgment and verification**

One clear example: when generating tests, Copilot suggested adding extensive exception-handling tests (e.g., testing that invalid time formats like "25:99" raise errors, or that negative durations are rejected). I rejected these because the current system trusts internal input—validation happens at the UI boundary in Streamlit via `number_input` constraints and text input placeholders, not inside the data classes. Adding defensive checks to `CareTask` would have been speculative complexity for scenarios that the actual app flow prevents. I verified this by tracing the data path: user input flows through Streamlit widgets (which enforce types and ranges) into `CareTask` constructors, so the internal code never receives malformed data.

---

## 4. Testing and Verification

**a. What you tested**

The 20-test suite covers five areas: (1) **Sorting correctness**—tasks sort chronologically, tasks without a time slot land at the end. (2) **Recurrence logic**—daily tasks advance by one day, weekly by seven, one-time tasks return `None`. (3) **Conflict detection**—overlapping times produce warnings, non-overlapping times produce none, completed tasks are excluded. (4) **Daily plan budget**—highest-priority tasks are selected first, the budget is never exceeded, and an empty task list is handled gracefully. (5) **Filtering and aggregation**—`filter_by_status`, `filter_by_pet`, `get_all_tasks`, `edit`, and `mark_task_complete` all behave correctly, including edge cases like unknown pet names.

These tests matter because the scheduling logic is the core value of the app. A bug in conflict detection could let an owner double-book themselves; a bug in recurrence could silently drop a daily medication task.

**b. Confidence**

Confidence: **5/5**. All 20 tests pass and cover both happy paths and meaningful edge cases. If I had more time, I would add tests for: (1) tasks that are back-to-back but don't overlap (boundary condition at exactly the end time), (2) a plan where every task exceeds the budget (should return an empty plan), and (3) multiple recurring tasks completing in sequence to verify the chain of next-occurrences stays correct over several cycles.

---

## 5. Reflection

**a. What went well**

The part I'm most satisfied with is how cleanly the Planner class separates concerns. Sorting, filtering, conflict detection, and plan generation are all independent methods that compose well—the UI can call them in any combination without the methods knowing about each other. This made the Streamlit integration straightforward: each UI control maps to exactly one Planner method.

**b. What you would improve**

If I had another iteration, I would: (1) support **multiple pets in the UI** with a pet selector and per-pet task views using `filter_by_pet`, (2) replace the greedy algorithm with a **knapsack-style optimizer** that maximizes total priority within the budget rather than just picking the highest single-priority tasks, and (3) add **persistent storage** (SQLite or JSON file) so tasks survive between Streamlit sessions.

**c. Key takeaway**

The most important lesson was that AI is a powerful accelerator but not a substitute for architectural judgment. Copilot could generate code faster than I could type it, but it had no sense of scope—it would happily add defensive error handling, extra abstractions, and features I didn't ask for. Being the "lead architect" meant constantly deciding what to keep, what to reject, and what to simplify. The real skill isn't prompting—it's knowing when the AI's suggestion is solving a problem that doesn't exist, and having the confidence to say no.
