# LLM Agentic Care Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an LLM-powered AI Care Coach to PawPal+ that recommends a pet care schedule, checks and revises that recommendation with Python guardrails, and logs every agent step.

**Architecture:** Keep the existing `Planner` and domain classes as trusted scheduling tools, then add an `ai_care_agent.py` module that wraps an LLM call in a plan-act-check-revise workflow. The LLM proposes an ordered list of task titles and a friendly explanation; Python validates the LLM JSON, maps titles back to real `CareTask` objects, enforces budget and conflict guardrails, revises unsafe plans, and returns an audit log for Streamlit. Tests use a fake LLM client so the feature is deterministic in CI and does not spend API credits.

**Tech Stack:** Python dataclasses, `openai` Python SDK, `python-dotenv`, existing PawPal+ classes in `pawpal_system.py`, Streamlit, pytest.

---

## File Structure

- Modify `requirements.txt`: Add `openai` and `python-dotenv`.
- Create `ai_care_agent.py`: Contains the LLM client wrapper, agent dataclasses, guardrail error, JSON parsing, validation, budget fitting, conflict revision, and audit logging.
- Create `tests/test_ai_care_agent.py`: Tests the LLM-driven ordering, malformed JSON fallback, unknown-task guardrail, input validation, conflict revision, and missing-key behavior.
- Modify `app.py`: Adds an "AI Care Coach" Streamlit section that calls the agent and displays the recommendation, skipped tasks, warnings, and audit log.
- Modify `README.md`: Documents the LLM feature, required environment variable, guardrails, and how to avoid committing secrets.
- Keep `.env` ignored and commit only `.env.example`.

---

### Task 1: Add LLM Dependencies and Secret Placeholder

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Verify: `.gitignore`

- [ ] **Step 1: Update dependencies**

Replace `requirements.txt` with:

```text
streamlit>=1.30
pytest>=7.0
openai>=1.0
python-dotenv>=1.0
```

- [ ] **Step 2: Update the example environment file**

Replace `.env.example` with:

```text
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-5
```

- [ ] **Step 3: Confirm secret files are ignored**

Ensure `.gitignore` contains:

```gitignore
# Local secrets
.env
.env.*
!.env.example
.streamlit/secrets.toml
```

- [ ] **Step 4: Verify `.env` is ignored**

Run:

```bash
git check-ignore -v .env
```

Expected: PASS with output showing `.gitignore` is the source of the ignore rule.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example .gitignore
git commit -m "chore: add OpenAI environment configuration"
```

---

### Task 2: Define the LLM Agent Contract

**Files:**
- Create: `ai_care_agent.py`
- Create: `tests/test_ai_care_agent.py`

- [ ] **Step 1: Write the failing contract test**

Create `tests/test_ai_care_agent.py` with:

```python
from ai_care_agent import AgentLogEntry, AgentRecommendation


def test_agent_recommendation_stores_llm_explanation_and_logs():
    log = AgentLogEntry(
        step="llm_plan",
        message="LLM returned a task order.",
        status="ok",
    )
    recommendation = AgentRecommendation(
        summary="Schedule the morning walk first.",
        plan=[],
        skipped=[],
        warnings=[],
        log=[log],
        llm_explanation="The walk has the strongest care impact today.",
    )

    assert recommendation.summary == "Schedule the morning walk first."
    assert recommendation.plan == []
    assert recommendation.skipped == []
    assert recommendation.warnings == []
    assert recommendation.log[0].step == "llm_plan"
    assert recommendation.log[0].status == "ok"
    assert "walk" in recommendation.llm_explanation
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py::test_agent_recommendation_stores_llm_explanation_and_logs -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ai_care_agent'`.

- [ ] **Step 3: Add the minimal data contract**

Create `ai_care_agent.py` with:

```python
from dataclasses import dataclass
from typing import Protocol

from pawpal_system import CareTask


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return a text response for the provided prompt."""


@dataclass
class AgentLogEntry:
    step: str
    message: str
    status: str


@dataclass
class AgentRecommendation:
    summary: str
    plan: list[CareTask]
    skipped: list[CareTask]
    warnings: list[str]
    log: list[AgentLogEntry]
    llm_explanation: str
```

- [ ] **Step 4: Run the contract test**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py::test_agent_recommendation_stores_llm_explanation_and_logs -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_care_agent.py tests/test_ai_care_agent.py
git commit -m "feat: add LLM care agent contract"
```

---

### Task 3: Add the OpenAI Client Wrapper

**Files:**
- Modify: `ai_care_agent.py`
- Modify: `tests/test_ai_care_agent.py`

- [ ] **Step 1: Add failing missing-key test**

Append to `tests/test_ai_care_agent.py`:

```python
import os

import pytest

from ai_care_agent import AgentConfigurationError, OpenAILLMClient


def test_openai_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")

    with pytest.raises(AgentConfigurationError, match="OPENAI_API_KEY"):
        OpenAILLMClient()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py::test_openai_client_requires_api_key -v
```

Expected: FAIL with `ImportError` or `AttributeError` for `AgentConfigurationError` and `OpenAILLMClient`.

- [ ] **Step 3: Implement the OpenAI wrapper**

Replace `ai_care_agent.py` with:

```python
import json
import os
from dataclasses import dataclass
from typing import Protocol

from dotenv import load_dotenv
from openai import OpenAI

from pawpal_system import CareTask, Owner, Pet, Planner


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return a text response for the provided prompt."""


@dataclass
class AgentLogEntry:
    step: str
    message: str
    status: str


@dataclass
class AgentRecommendation:
    summary: str
    plan: list[CareTask]
    skipped: list[CareTask]
    warnings: list[str]
    log: list[AgentLogEntry]
    llm_explanation: str


class AgentConfigurationError(RuntimeError):
    """Raised when the LLM agent is missing required configuration."""


class AgentGuardrailError(ValueError):
    """Raised when the agent refuses unsafe or invalid scheduling input."""


class OpenAILLMClient:
    def __init__(self, model: str | None = None) -> None:
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            raise AgentConfigurationError("OPENAI_API_KEY is not set.")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")
        self.client = OpenAI()

    def complete(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=500,
        )
        return response.output_text
```

- [ ] **Step 4: Run the missing-key test**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py::test_openai_client_requires_api_key -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_care_agent.py tests/test_ai_care_agent.py requirements.txt .env.example
git commit -m "feat: add OpenAI LLM client wrapper"
```

---

### Task 4: Ask the LLM for a Structured Task Order

**Files:**
- Modify: `ai_care_agent.py`
- Modify: `tests/test_ai_care_agent.py`

- [ ] **Step 1: Add fake LLM tests**

Append to `tests/test_ai_care_agent.py`:

```python
from ai_care_agent import CareCoachAgent, AgentGuardrailError
from pawpal_system import CareTask, Owner, Pet, Planner


class FakeLLMClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def test_agent_uses_llm_task_order_before_budgeting():
    owner = Owner(name="Alex", available_minutes_per_day=30)
    pet = Pet(name="Buddy", species="Dog")
    pet.add_care_task(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5)
    )
    pet.add_care_task(
        CareTask(title="Brush coat", category="Grooming", duration_minutes=30, priority=2)
    )
    llm = FakeLLMClient(
        '{"task_order": ["Brush coat", "Morning walk"], '
        '"explanation": "Brush coat is recommended first today."}'
    )
    agent = CareCoachAgent(planner=Planner(), llm_client=llm)

    recommendation = agent.recommend(owner, pet)

    assert [task.title for task in recommendation.plan] == ["Brush coat"]
    assert [task.title for task in recommendation.skipped] == ["Morning walk"]
    assert "Owner: Alex" in llm.prompts[0]
    assert "Brush coat" in recommendation.llm_explanation
    assert [entry.step for entry in recommendation.log] == [
        "guardrails",
        "llm_plan",
        "act",
        "check",
    ]


def test_agent_rejects_unknown_llm_task_title():
    owner = Owner(name="Alex", available_minutes_per_day=30)
    pet = Pet(name="Buddy", species="Dog")
    pet.add_care_task(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5)
    )
    llm = FakeLLMClient(
        '{"task_order": ["Give chocolate treat"], '
        '"explanation": "This title is not in the real task list."}'
    )
    agent = CareCoachAgent(planner=Planner(), llm_client=llm)

    with pytest.raises(AgentGuardrailError, match="unknown task"):
        agent.recommend(owner, pet)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py::test_agent_uses_llm_task_order_before_budgeting tests/test_ai_care_agent.py::test_agent_rejects_unknown_llm_task_title -v
```

Expected: FAIL because `CareCoachAgent` does not exist yet.

- [ ] **Step 3: Implement the LLM-driven agent**

Append this class to `ai_care_agent.py`:

```python
class CareCoachAgent:
    def __init__(self, planner: Planner, llm_client: LLMClient) -> None:
        self.planner = planner
        self.llm_client = llm_client

    def recommend(self, owner: Owner, pet: Pet) -> AgentRecommendation:
        self._validate_inputs(owner, pet)
        log = [
            AgentLogEntry(
                step="guardrails",
                message="Inputs passed safety checks.",
                status="ok",
            )
        ]

        tasks = self.planner.filter_by_status(pet.list_tasks(), completed=False)
        if not tasks:
            log.append(
                AgentLogEntry(
                    step="check",
                    message="No incomplete tasks need scheduling.",
                    status="ok",
                )
            )
            return AgentRecommendation(
                summary="No incomplete tasks need scheduling right now.",
                plan=[],
                skipped=[],
                warnings=[],
                log=log,
                llm_explanation="No tasks were sent to the LLM because everything is complete.",
            )

        prompt = self._build_prompt(owner, pet, tasks)
        raw_response = self.llm_client.complete(prompt)
        task_order, llm_explanation = self._parse_llm_response(raw_response, tasks)
        log.append(
            AgentLogEntry(
                step="llm_plan",
                message=f"LLM returned {len(task_order)} task title(s).",
                status="ok",
            )
        )

        ordered_tasks = self._order_tasks(tasks, task_order)
        plan, skipped = self._fit_budget(ordered_tasks, owner.available_minutes_per_day)
        log.append(
            AgentLogEntry(
                step="act",
                message=f"Built a budget-safe plan with {len(plan)} task(s).",
                status="ok",
            )
        )

        warnings = self.planner.detect_conflicts(plan)
        log.append(
            AgentLogEntry(
                step="check",
                message=(
                    f"Found {len(warnings)} schedule conflict warning(s)."
                    if warnings
                    else "Plan passed conflict checks."
                ),
                status="warning" if warnings else "ok",
            )
        )

        return AgentRecommendation(
            summary=self._build_summary(plan, skipped, warnings),
            plan=plan,
            skipped=skipped,
            warnings=warnings,
            log=log,
            llm_explanation=llm_explanation,
        )

    def _validate_inputs(self, owner: Owner, pet: Pet) -> None:
        if owner.available_minutes_per_day <= 0:
            raise AgentGuardrailError("Owner available minutes must be greater than 0.")

        for task in pet.list_tasks():
            if task.duration_minutes <= 0:
                raise AgentGuardrailError(
                    f"Task '{task.title}' must have a positive duration."
                )
            if task.priority < 1 or task.priority > 5:
                raise AgentGuardrailError(
                    f"Task '{task.title}' priority must be between 1 and 5."
                )

    def _build_prompt(self, owner: Owner, pet: Pet, tasks: list[CareTask]) -> str:
        task_lines = "\n".join(
            (
                f"- title={task.title}; category={task.category}; "
                f"duration={task.duration_minutes}; priority={task.priority}; "
                f"time={task.time or 'unscheduled'}; frequency={task.frequency}"
            )
            for task in tasks
        )
        return (
            "You are PawPal+'s AI Care Coach. Return only valid JSON with two keys: "
            "'task_order' as a list of exact task titles from the provided list, and "
            "'explanation' as a short user-friendly reason.\n\n"
            f"Owner: {owner.name}\n"
            f"Available minutes today: {owner.available_minutes_per_day}\n"
            f"Pet: {pet.name} ({pet.species})\n"
            f"Tasks:\n{task_lines}"
        )

    def _parse_llm_response(
        self, raw_response: str, tasks: list[CareTask]
    ) -> tuple[list[str], str]:
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise AgentGuardrailError("LLM response was not valid JSON.") from exc

        task_order = data.get("task_order")
        explanation = data.get("explanation")
        if not isinstance(task_order, list) or not all(
            isinstance(title, str) for title in task_order
        ):
            raise AgentGuardrailError("LLM response must include a list of task titles.")
        if not isinstance(explanation, str) or not explanation.strip():
            raise AgentGuardrailError("LLM response must include an explanation.")

        known_titles = {task.title for task in tasks}
        for title in task_order:
            if title not in known_titles:
                raise AgentGuardrailError(f"LLM returned unknown task title: {title}")

        return task_order, explanation.strip()

    def _order_tasks(self, tasks: list[CareTask], task_order: list[str]) -> list[CareTask]:
        by_title = {task.title: task for task in tasks}
        ordered = [by_title[title] for title in task_order]
        ordered_titles = set(task_order)
        ordered.extend(task for task in tasks if task.title not in ordered_titles)
        return ordered

    def _fit_budget(
        self, tasks: list[CareTask], available_minutes: int
    ) -> tuple[list[CareTask], list[CareTask]]:
        plan = []
        skipped = []
        used_minutes = 0
        for task in tasks:
            if used_minutes + task.duration_minutes <= available_minutes:
                plan.append(task)
                used_minutes += task.duration_minutes
            else:
                skipped.append(task)
        return plan, skipped

    def _build_summary(
        self, plan: list[CareTask], skipped: list[CareTask], warnings: list[str]
    ) -> str:
        task_word = "task" if len(plan) == 1 else "tasks"
        if warnings:
            return (
                f"Recommended {len(plan)} {task_word}; {len(skipped)} skipped; "
                f"{len(warnings)} conflict warning(s) need review."
            )
        return f"Recommended {len(plan)} {task_word}; {len(skipped)} skipped; no conflicts found."
```

- [ ] **Step 4: Run all agent tests**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_care_agent.py tests/test_ai_care_agent.py
git commit -m "feat: add LLM-driven care coach planning"
```

---

### Task 5: Add Self-Check Revision for Conflicts

**Files:**
- Modify: `ai_care_agent.py`
- Modify: `tests/test_ai_care_agent.py`

- [ ] **Step 1: Add failing revision test**

Append to `tests/test_ai_care_agent.py`:

```python
def test_agent_revises_llm_plan_when_tasks_conflict():
    owner = Owner(name="Alex", available_minutes_per_day=60)
    pet = Pet(name="Buddy", species="Dog")
    pet.add_care_task(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5, time="07:00")
    )
    pet.add_care_task(
        CareTask(title="Breakfast", category="Feeding", duration_minutes=10, priority=4, time="07:15")
    )
    llm = FakeLLMClient(
        '{"task_order": ["Morning walk", "Breakfast"], '
        '"explanation": "Both tasks matter, but the walk has higher impact."}'
    )
    agent = CareCoachAgent(planner=Planner(), llm_client=llm)

    recommendation = agent.recommend(owner, pet)

    assert [task.title for task in recommendation.plan] == ["Morning walk"]
    assert [task.title for task in recommendation.skipped] == ["Breakfast"]
    assert recommendation.warnings == []
    assert [entry.step for entry in recommendation.log] == [
        "guardrails",
        "llm_plan",
        "act",
        "check",
        "revise",
    ]
    revise_entry = recommendation.log[-1]
    assert revise_entry.status == "ok"
    assert "Breakfast" in revise_entry.message
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py::test_agent_revises_llm_plan_when_tasks_conflict -v
```

Expected: FAIL because the agent detects conflicts but does not revise them.

- [ ] **Step 3: Add conflict revision helpers**

Add these methods inside `CareCoachAgent`:

```python
    def _revise_conflicts(
        self, plan: list[CareTask], skipped: list[CareTask]
    ) -> tuple[list[CareTask], list[CareTask], list[CareTask]]:
        revised_plan = list(plan)
        revised_skipped = list(skipped)
        removed = []

        while self.planner.detect_conflicts(revised_plan):
            task_to_remove = self._lowest_priority_task(revised_plan)
            revised_plan.remove(task_to_remove)
            revised_skipped.append(task_to_remove)
            removed.append(task_to_remove)

        return revised_plan, revised_skipped, removed

    def _lowest_priority_task(self, tasks: list[CareTask]) -> CareTask:
        return sorted(
            tasks,
            key=lambda task: (
                task.priority,
                task.time if task.time else "99:99",
                task.duration_minutes,
            ),
        )[0]
```

Then in `recommend()`, immediately after the `check` log entry, add:

```python
        if warnings:
            plan, skipped, removed = self._revise_conflicts(plan, skipped)
            removed_titles = ", ".join(task.title for task in removed)
            warnings = self.planner.detect_conflicts(plan)
            log.append(
                AgentLogEntry(
                    step="revise",
                    message=f"Removed conflicting task(s): {removed_titles}.",
                    status="ok" if not warnings else "warning",
                )
            )
```

The final `AgentRecommendation` return must use the updated `plan`, `skipped`, and `warnings`.

- [ ] **Step 4: Run agent tests**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_care_agent.py tests/test_ai_care_agent.py
git commit -m "feat: revise unsafe LLM schedule recommendations"
```

---

### Task 6: Wire the LLM Agent into Streamlit

**Files:**
- Modify: `app.py`
- Test: `tests/test_ai_care_agent.py`
- Test: `tests/test_pawpal.py`

- [ ] **Step 1: Run tests before UI wiring**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py tests/test_pawpal.py -v
```

Expected: PASS.

- [ ] **Step 2: Import the agent**

In `app.py`, replace:

```python
from pawpal_system import CareTask, Pet, Owner, Planner
```

with:

```python
from ai_care_agent import (
    AgentConfigurationError,
    AgentGuardrailError,
    CareCoachAgent,
    OpenAILLMClient,
)
from pawpal_system import CareTask, Pet, Owner, Planner
```

- [ ] **Step 3: Initialize the agent lazily**

After the existing planner session-state block:

```python
if "planner" not in st.session_state:
    st.session_state.planner = Planner()
```

add:

```python
if "care_agent" not in st.session_state:
    st.session_state.care_agent = None
```

- [ ] **Step 4: Add the AI Care Coach section**

Append this section after the existing "Generate Daily Plan" section:

```python
st.divider()
st.subheader("AI Care Coach")

st.markdown(
    "The AI Care Coach asks an LLM to recommend a task order, then checks and "
    "revises the result with PawPal+'s scheduling guardrails."
)

if st.button("Ask AI Care Coach"):
    try:
        if st.session_state.care_agent is None:
            st.session_state.care_agent = CareCoachAgent(
                planner=st.session_state.planner,
                llm_client=OpenAILLMClient(),
            )
        recommendation = st.session_state.care_agent.recommend(
            st.session_state.owner,
            st.session_state.pet,
        )
    except AgentConfigurationError as exc:
        st.error(str(exc))
        st.info("Set OPENAI_API_KEY in your local .env file before using the AI coach.")
    except AgentGuardrailError as exc:
        st.error(str(exc))
    else:
        st.success(recommendation.summary)
        st.markdown("#### AI Explanation")
        st.write(recommendation.llm_explanation)

        if recommendation.plan:
            st.markdown("#### Recommended Plan")
            st.table([
                {
                    "Title": task.title,
                    "Category": task.category,
                    "Time": task.time or "-",
                    "Duration": f"{task.duration_minutes} min",
                    "Priority": task.priority,
                }
                for task in st.session_state.planner.sort_by_time(recommendation.plan)
            ])
        else:
            st.info("No tasks were added to the AI recommendation.")

        if recommendation.skipped:
            st.markdown("#### Skipped Tasks")
            st.table([
                {
                    "Title": task.title,
                    "Reason": "Time budget or conflict guardrail",
                    "Duration": f"{task.duration_minutes} min",
                    "Priority": task.priority,
                }
                for task in recommendation.skipped
            ])

        st.markdown("#### Agent Audit Log")
        st.table([
            {
                "Step": entry.step,
                "Status": entry.status,
                "Message": entry.message,
            }
            for entry in recommendation.log
        ])
```

- [ ] **Step 5: Run tests after UI wiring**

Run:

```bash
python -m pytest tests/test_ai_care_agent.py tests/test_pawpal.py -v
```

Expected: PASS.

- [ ] **Step 6: Compile Python files**

Run:

```bash
python -m py_compile app.py ai_care_agent.py pawpal_system.py main.py
```

Expected: exits with code 0 and prints no errors.

- [ ] **Step 7: Commit**

```bash
git add app.py ai_care_agent.py tests/test_ai_care_agent.py
git commit -m "feat: add LLM care coach to Streamlit app"
```

---

### Task 7: Document the LLM Agent and Secret Handling

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Verify: `.gitignore`

- [ ] **Step 1: Add README AI feature section**

In `README.md`, add this section after `## Final Project Overview`:

```markdown
## AI Feature: LLM Agentic Care Coach

PawPal+ includes an **LLM Agentic Care Coach**. The coach sends the current incomplete care tasks to an LLM, asks for a structured task order and short explanation, then validates that response before showing it to the user.

The feature is agentic because it follows a plan-act-check-revise loop: it asks the LLM to plan, builds a budget-safe schedule from that plan, checks the result for conflicts, revises unsafe recommendations, and displays an audit log. Python guardrails reject invalid task data, malformed LLM JSON, unknown task titles, missing API configuration, and conflicting schedules that require revision.
```

Add this bullet under `## Features`:

```markdown
- **LLM Agentic Care Coach**: Uses an LLM to recommend task order, then validates, revises, and logs the result with local guardrails.
```

- [ ] **Step 2: Add setup instructions**

In `README.md`, after dependency installation, add:

````markdown
Create a local `.env` file:

```bash
cp .env.example .env
```

Then set your real key in `.env`:

```text
OPENAI_API_KEY=your-real-api-key
OPENAI_MODEL=gpt-5
```

Do not commit `.env`. The repository's `.gitignore` is configured to keep local secret files out of Git.
````

- [ ] **Step 3: Add README file structure entry**

In the repository structure block in `README.md`, add:

```text
├── ai_care_agent.py    # LLM agent workflow, guardrails, and audit logging
```

- [ ] **Step 4: Verify docs and secret ignore rules**

Run:

```bash
git check-ignore -v .env
git diff --check -- README.md .env.example .gitignore
```

Expected: `.env` is ignored, and the diff check exits with code 0.

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example .gitignore
git commit -m "docs: document LLM care coach setup"
```

---

### Task 8: Final Verification

**Files:**
- Verify: `ai_care_agent.py`
- Verify: `app.py`
- Verify: `pawpal_system.py`
- Verify: `tests/test_ai_care_agent.py`
- Verify: `tests/test_pawpal.py`
- Verify: `README.md`
- Verify: `.gitignore`
- Verify: `.env.example`

- [ ] **Step 1: Run the full test suite**

Run:

```bash
python -m pytest -v
```

Expected: all existing PawPal+ tests and all new AI care agent tests pass.

- [ ] **Step 2: Compile Python files**

Run:

```bash
python -m py_compile app.py ai_care_agent.py pawpal_system.py main.py
```

Expected: exits with code 0 and prints no errors.

- [ ] **Step 3: Confirm real secrets are not tracked**

Run:

```bash
git check-ignore -v .env
git status --short
```

Expected: `.env` is ignored and does not appear in `git status --short`.

- [ ] **Step 4: Search staged and unstaged tracked content for secret patterns**

Run:

```bash
rg "sk-|OPENAI_API_KEY=.*sk-" README.md .env.example .gitignore app.py ai_care_agent.py tests requirements.txt
```

Expected: no output containing a real API key. Placeholder references such as `OPENAI_API_KEY=your-api-key-here` are acceptable.

- [ ] **Step 5: Check whitespace**

Run:

```bash
git diff --check
```

Expected: exits with code 0 and prints no errors.

- [ ] **Step 6: Record final result**

In the final handoff, report:

```text
Implemented LLM Agentic Care Coach.
The LLM proposes task order and explanation.
Python validates LLM JSON, rejects unsafe outputs, enforces the time budget, revises conflicts, and logs each step.
Verified with python -m pytest -v and python -m py_compile app.py ai_care_agent.py pawpal_system.py main.py.
Confirmed .env is ignored and no real API key is tracked.
```

---

## Self-Review

- **Spec coverage:** The plan now includes an LLM-powered agent, not just a deterministic local workflow. It still satisfies the final-project agentic requirement with plan, act, check, revise, logging, and guardrails.
- **Secret safety:** The plan uses `OPENAI_API_KEY` from environment configuration, commits only `.env.example`, and includes verification that `.env` is ignored.
- **Placeholder scan:** No placeholders or vague implementation steps remain. Every code step includes concrete code or exact insertion text.
- **Type consistency:** `LLMClient`, `OpenAILLMClient`, `CareCoachAgent`, `AgentRecommendation`, `AgentLogEntry`, `AgentConfigurationError`, and `AgentGuardrailError` are introduced before use and reused consistently.
- **Testing coverage:** The plan covers LLM ordering, unknown task rejection, missing API key handling, conflict revision, full regression tests, Python compilation, and secret scanning.
