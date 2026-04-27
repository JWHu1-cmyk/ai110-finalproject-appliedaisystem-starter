import pytest

from pawpal_system import CareTask, Owner, Pet, Planner
from ai_care_agent import (
    AgentConfigurationError,
    AgentGuardrailError,
    AgentLogEntry,
    AgentRecommendation,
    CareCoachAgent,
    OpenAILLMClient,
)


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


def make_owner_pet(*tasks, minutes=60):
    owner = Owner(name="Alex", available_minutes_per_day=minutes)
    pet = Pet(name="Buddy", species="dog")
    for task in tasks:
        pet.add_care_task(task)
    owner.add_pet(pet)
    return owner, pet


def test_agent_recommendation_stores_llm_explanation_and_logs():
    log = [AgentLogEntry(step="plan", message="ordered tasks", status="ok")]
    recommendation = AgentRecommendation(
        summary="Recommended 1 task; 0 skipped; no conflicts found.",
        plan=[],
        skipped=[],
        warnings=[],
        log=log,
        llm_explanation="Brush coat first.",
    )

    assert recommendation.llm_explanation == "Brush coat first."
    assert recommendation.log == log


def test_openai_llm_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(AgentConfigurationError, match="OPENAI_API_KEY"):
        OpenAILLMClient(load_env=False)


def test_agent_uses_llm_task_order_before_budgeting():
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5),
        CareTask(title="Brush coat", category="Grooming", duration_minutes=30, priority=2),
        minutes=30,
    )
    llm = FakeLLM('{"task_order": ["Brush coat", "Morning walk"], "explanation": "Grooming first."}')

    recommendation = CareCoachAgent(Planner(), llm).recommend(owner, pet)

    assert [task.title for task in recommendation.plan] == ["Brush coat"]
    assert [task.title for task in recommendation.skipped] == ["Morning walk"]
    assert recommendation.llm_explanation == "Grooming first."


def test_unknown_llm_task_title_is_rejected():
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5)
    )
    llm = FakeLLM('{"task_order": ["Mystery task"], "explanation": "Unknown first."}')

    with pytest.raises(AgentGuardrailError, match="Unknown task title"):
        CareCoachAgent(Planner(), llm).recommend(owner, pet)


def test_non_positive_budget_rejected():
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5),
        minutes=0,
    )

    with pytest.raises(AgentGuardrailError, match="available minutes"):
        CareCoachAgent(Planner(), FakeLLM("{}")).recommend(owner, pet)


def test_non_positive_task_duration_rejected():
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=0, priority=5)
    )

    with pytest.raises(AgentGuardrailError, match="duration"):
        CareCoachAgent(Planner(), FakeLLM("{}")).recommend(owner, pet)


def test_priority_outside_one_to_five_rejected():
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=6)
    )

    with pytest.raises(AgentGuardrailError, match="priority"):
        CareCoachAgent(Planner(), FakeLLM("{}")).recommend(owner, pet)


def test_natural_language_llm_response_uses_priority_fallback_order():
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5),
        CareTask(title="Brush coat", category="Grooming", duration_minutes=30, priority=2),
        minutes=30,
    )

    recommendation = CareCoachAgent(
        Planner(),
        FakeLLM("Start with Morning walk because it has the highest priority."),
    ).recommend(owner, pet)

    assert [task.title for task in recommendation.plan] == ["Morning walk"]
    assert [task.title for task in recommendation.skipped] == ["Brush coat"]
    assert "Start with Morning walk" in recommendation.llm_explanation
    assert recommendation.log[1].status == "ok"


@pytest.mark.parametrize(
    "response",
    [
        '{"explanation": "Missing order."}',
        '{"task_order": "Morning walk", "explanation": "Wrong type."}',
        '{"task_order": [123], "explanation": "Wrong item type."}',
    ],
)
def test_missing_or_invalid_task_order_uses_priority_fallback(response):
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5)
    )

    recommendation = CareCoachAgent(Planner(), FakeLLM(response)).recommend(owner, pet)

    assert [task.title for task in recommendation.plan] == ["Morning walk"]


@pytest.mark.parametrize(
    "response",
    [
        '{"task_order": ["Morning walk"]}',
        '{"task_order": ["Morning walk"], "explanation": "   "}',
    ],
)
def test_blank_or_missing_explanation_uses_safe_fallback(response):
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5)
    )

    recommendation = CareCoachAgent(Planner(), FakeLLM(response)).recommend(owner, pet)

    assert [task.title for task in recommendation.plan] == ["Morning walk"]
    assert recommendation.llm_explanation


def test_empty_incomplete_task_list_returns_clear_recommendation_without_calling_llm():
    owner, pet = make_owner_pet(
        CareTask(
            title="Morning walk",
            category="Exercise",
            duration_minutes=30,
            priority=5,
            completed=True,
        )
    )
    llm = FakeLLM("{}")

    recommendation = CareCoachAgent(Planner(), llm).recommend(owner, pet)

    assert recommendation.summary == "No incomplete tasks need scheduling right now."
    assert recommendation.plan == []
    assert recommendation.skipped == []
    assert recommendation.warnings == []
    assert recommendation.llm_explanation == "No tasks were sent to the LLM because everything is complete."
    assert [entry.step for entry in recommendation.log] == ["guardrails", "check"]
    assert llm.calls == []


def test_conflict_revision_removes_lower_priority_conflicting_task_and_logs_revise():
    owner, pet = make_owner_pet(
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5, time="08:00"),
        CareTask(title="Brush coat", category="Grooming", duration_minutes=20, priority=2, time="08:10"),
        minutes=60,
    )
    llm = FakeLLM('{"task_order": ["Morning walk", "Brush coat"], "explanation": "Walk first."}')

    recommendation = CareCoachAgent(Planner(), llm).recommend(owner, pet)

    assert [task.title for task in recommendation.plan] == ["Morning walk"]
    assert [task.title for task in recommendation.skipped] == ["Brush coat"]
    assert recommendation.warnings == []
    revise_entries = [entry for entry in recommendation.log if entry.step == "revise"]
    assert revise_entries
    assert "Brush coat" in revise_entries[0].message
