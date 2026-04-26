from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

from dotenv import load_dotenv

from pawpal_system import CareTask, Owner, Pet, Planner


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


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
    pass


class AgentGuardrailError(ValueError):
    pass


class OpenAILLMClient:
    def __init__(self, model: str | None = None, load_env: bool = True):
        if load_env:
            load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AgentConfigurationError("OPENAI_API_KEY is required to use the AI Care Coach.")

        from openai import OpenAI

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")
        self.client = OpenAI(api_key=api_key)

    def complete(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=500,
        )
        return response.output_text


class CareCoachAgent:
    def __init__(self, planner: Planner, llm_client: LLMClient):
        self.planner = planner
        self.llm_client = llm_client

    def recommend(self, owner: Owner, pet: Pet) -> AgentRecommendation:
        log: list[AgentLogEntry] = []
        self._run_guardrails(owner, pet)
        log.append(AgentLogEntry("guardrails", "Owner budget and task fields passed validation.", "ok"))

        incomplete_tasks = self.planner.filter_by_status(pet.list_tasks(), completed=False)
        if not incomplete_tasks:
            log.append(AgentLogEntry("check", "No incomplete tasks need scheduling.", "ok"))
            return AgentRecommendation(
                summary="No incomplete tasks need scheduling right now.",
                plan=[],
                skipped=[],
                warnings=[],
                log=log,
                llm_explanation="No tasks were sent to the LLM because everything is complete.",
            )

        prompt = self._build_prompt(owner, pet, incomplete_tasks)
        llm_text = self.llm_client.complete(prompt)
        task_order, explanation = self._parse_llm_response(llm_text, incomplete_tasks)
        log.append(AgentLogEntry("plan", "LLM returned a task order and explanation.", "ok"))

        ordered_tasks = self._ordered_tasks(task_order, incomplete_tasks)
        plan, skipped = self._fit_to_budget(ordered_tasks, owner.available_minutes_per_day)
        log.append(
            AgentLogEntry(
                "act",
                f"Built budgeted plan with {len(plan)} task(s) and {len(skipped)} skipped.",
                "ok",
            )
        )

        warnings = self.planner.detect_conflicts(plan)
        log.append(self._conflict_log_entry(warnings))
        if warnings:
            plan, skipped, warnings, removed_titles = self._revise_conflicts(plan, skipped)
            if removed_titles:
                log.append(
                    AgentLogEntry(
                        "revise",
                        "Removed lower-priority conflicting task(s): " + ", ".join(removed_titles),
                        "ok",
                    )
                )

        summary = self._build_summary(len(plan), len(skipped), len(warnings))
        return AgentRecommendation(
            summary=summary,
            plan=plan,
            skipped=skipped,
            warnings=warnings,
            log=log,
            llm_explanation=explanation,
        )

    def _run_guardrails(self, owner: Owner, pet: Pet) -> None:
        if owner.available_minutes_per_day <= 0:
            raise AgentGuardrailError("Owner available minutes per day must be positive.")

        for task in pet.list_tasks():
            if task.duration_minutes <= 0:
                raise AgentGuardrailError(f"Task '{task.title}' duration must be positive.")
            if task.priority < 1 or task.priority > 5:
                raise AgentGuardrailError(f"Task '{task.title}' priority must be between 1 and 5.")

    def _build_prompt(self, owner: Owner, pet: Pet, tasks: list[CareTask]) -> str:
        lines = [
            "You are an AI pet care coach helping order today's incomplete tasks.",
            "Return only JSON with this shape: {\"task_order\": [\"exact task title\"], \"explanation\": \"brief reason\"}.",
            "Use only exact task titles from the task list. Do not invent or rename tasks.",
            f"Owner: {owner.name}",
            f"Available minutes: {owner.available_minutes_per_day}",
            f"Pet: {pet.name} ({pet.species})",
            f"Pet notes: {pet.notes or 'none'}",
            "Tasks:",
        ]
        for task in tasks:
            lines.append(
                "- "
                f"title={task.title}; category={task.category}; duration_minutes={task.duration_minutes}; "
                f"priority={task.priority}; time={task.time or 'unscheduled'}; frequency={task.frequency}"
            )
        return "\n".join(lines)

    def _parse_llm_response(self, llm_text: str, tasks: list[CareTask]) -> tuple[list[str], str]:
        try:
            payload = json.loads(llm_text)
        except json.JSONDecodeError as exc:
            raise AgentGuardrailError("LLM response must be valid JSON.") from exc

        task_order = payload.get("task_order")
        if not isinstance(task_order, list) or not all(isinstance(title, str) for title in task_order):
            raise AgentGuardrailError("LLM response must include task_order as a list of task titles.")

        explanation = payload.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            raise AgentGuardrailError("LLM response must include a non-blank explanation.")

        known_titles = {task.title for task in tasks}
        unknown_titles = [title for title in task_order if title not in known_titles]
        if unknown_titles:
            raise AgentGuardrailError("Unknown task title returned by LLM: " + ", ".join(unknown_titles))

        return task_order, explanation.strip()

    def _ordered_tasks(self, task_order: list[str], tasks: list[CareTask]) -> list[CareTask]:
        by_title = {task.title: task for task in tasks}
        ordered = [by_title[title] for title in task_order]
        ordered_titles = set(task_order)
        ordered.extend(task for task in tasks if task.title not in ordered_titles)
        return ordered

    def _fit_to_budget(self, tasks: list[CareTask], budget: int) -> tuple[list[CareTask], list[CareTask]]:
        plan = []
        skipped = []
        total_minutes = 0

        for task in tasks:
            if total_minutes + task.duration_minutes <= budget:
                plan.append(task)
                total_minutes += task.duration_minutes
            else:
                skipped.append(task)

        return plan, skipped

    def _conflict_log_entry(self, warnings: list[str]) -> AgentLogEntry:
        if warnings:
            return AgentLogEntry("check", f"Found {len(warnings)} conflict warning(s).", "warning")
        return AgentLogEntry("check", "No conflicts found.", "ok")

    def _revise_conflicts(
        self, plan: list[CareTask], skipped: list[CareTask]
    ) -> tuple[list[CareTask], list[CareTask], list[str], list[str]]:
        revised_plan = list(plan)
        revised_skipped = list(skipped)
        removed_titles = []
        warnings = self.planner.detect_conflicts(revised_plan)

        while warnings and revised_plan:
            task_to_remove = min(revised_plan, key=lambda task: task.priority)
            revised_plan.remove(task_to_remove)
            revised_skipped.append(task_to_remove)
            removed_titles.append(task_to_remove.title)
            warnings = self.planner.detect_conflicts(revised_plan)

        return revised_plan, revised_skipped, warnings, removed_titles

    def _build_summary(self, plan_count: int, skipped_count: int, warning_count: int) -> str:
        task_word = "task" if plan_count == 1 else "tasks"
        if warning_count:
            return (
                f"Recommended {plan_count} {task_word}; {skipped_count} skipped; "
                f"{warning_count} conflict warning(s) need review."
            )
        return f"Recommended {plan_count} {task_word}; {skipped_count} skipped; no conflicts found."
