# PawPal+ LLM Care Coach Model Card

## System Overview

PawPal+ uses an LLM Agentic Care Coach to help pet owners review care tasks and generate a suggested daily schedule. The LLM recommends an order for incomplete tasks and writes a short explanation, while Python code validates the response, enforces time-budget rules, checks conflicts, revises unsafe recommendations, and records an audit log.

The system is intended for low-stakes pet care planning support. It should not be treated as veterinary, medical, or emergency advice.

## AI Collaboration Reflection

AI helped throughout the project by brainstorming the agentic workflow, rewriting the README, designing reliability tests, and suggesting how to keep API keys out of Git. A helpful suggestion was to prefer a structured JSON response from the LLM when possible. That made the agent easier to test because the code can parse `task_order`, reject unknown task titles, and map recommendations back to real `CareTask` objects.

One flawed suggestion was an early idea to make the care coach fully deterministic and call it "agentic" without using an LLM. That would have been easier to test, but it did not match the project direction once I decided I wanted a real LLM-powered feature. The final design keeps the LLM, but limits its authority with Python guardrails.

## Limitations and Biases

The LLM may overvalue tasks that sound urgent or emotionally important, even when the structured priority score says otherwise. It may also reflect general assumptions about pet care that do not fit every animal, household, culture, budget, or schedule.

The system only knows the information entered by the user. It does not know the pet's full health history, veterinary instructions, local weather, owner mobility, or emergency context. Because of that, the recommendation can be incomplete or inappropriate if the input tasks are missing important details.

The planner also uses simplified logic. It fits tasks into a time budget and checks overlapping time slots, but it does not optimize across every possible schedule combination or understand real-world travel time, task dependencies, or pet-specific medical risk.

## Misuse and Prevention

This AI could be misused if someone treats it as professional veterinary guidance or uses it to decide whether to skip medication, urgent care, or other health-critical tasks. It could also be misused if a user enters unsafe or misleading task names and trusts the LLM explanation without review.

To reduce that risk, the app keeps the AI in a recommendation role. The LLM cannot create new tasks, rename tasks, or directly mutate the schedule. Python guardrails reject unknown task titles in structured responses, invalid priorities, invalid task durations, and missing API configuration. If the LLM returns normal text instead of JSON, the app uses that text as the explanation and falls back to priority-based ordering for the actual schedule. The app also shows an audit log so the human user can review what the agent did before following the recommendation.

## Reliability and Testing Results

The latest local test run passed **35 out of 35 automated tests**. These tests cover the original PawPal+ planner plus the LLM Care Coach workflow.

The AI reliability tests use a fake LLM client, which makes the tests repeatable and avoids depending on a live API response. The tests verify that the agent:

- Uses the LLM's task order before applying the time budget.
- Rejects unknown task titles returned by the LLM.
- Accepts natural-language LLM responses and falls back to priority ordering.
- Rejects malformed structured task-order responses that contain unknown task titles.
- Rejects blank or missing LLM explanations.
- Rejects non-positive owner budgets, non-positive task durations, and priorities outside `1..5`.
- Avoids calling the LLM when there are no incomplete tasks.
- Revises conflicting schedules by removing lower-priority conflicting tasks.

What surprised me most was how often an LLM may prefer a conversational answer even when asked for structure. The final design handles both cases: structured JSON can influence task order, while natural-language responses become explanations and the schedule falls back to deterministic priority ordering.

## Human Oversight

The final recommendation is meant to be reviewed by a human. The user can compare the AI recommendation against the task list, skipped tasks, conflict warnings, and audit log. This is important because the AI may not understand context that was never entered into the app.

## Responsible Use

Use PawPal+ as a planning assistant, not as a replacement for judgment or professional advice. For medication, illness, injury, emergencies, or behavior concerns, users should follow veterinary guidance and use the app only to organize tasks that have already been decided by a responsible human.
