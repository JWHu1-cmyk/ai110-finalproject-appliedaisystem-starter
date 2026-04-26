# PawPal+ Final Project

**PawPal+** is a Streamlit-powered pet care planner that helps pet owners organize daily care tasks, detect schedule conflicts, and generate a priority-based daily plan that fits within the owner's available time.

## Original Project Summary

My original project from Modules 1-3 was **PawPal+**, a pet care scheduling assistant for busy owners. Its original goal was to model owners, pets, and care tasks using object-oriented design, then use that model to create a clear daily plan based on task priority, duration, scheduled time, and the owner's available minutes. By the end of the original project, PawPal+ could add and edit pet care tasks, sort them chronologically, filter by completion status or pet, detect overlapping time slots, create recurring daily or weekly follow-up tasks, and explain why certain tasks were scheduled or skipped.

## Final Project Overview

This final project builds on the original PawPal+ system by keeping the scheduling logic separated from the user interface and presenting the planner through an interactive Streamlit app. The app lets a user manage owner and pet information, add care tasks, review filtered and sorted task lists, identify conflicts, mark tasks complete, and generate a daily schedule with a human-readable explanation.

The core logic lives in `pawpal_system.py`, while `app.py` provides the Streamlit interface. A separate `main.py` file demonstrates the same system from the command line, and the test suite verifies the planner's main behaviors.

## Features

- **Owner and pet profiles**: Store the owner's name, daily time budget, and pet information.
- **Task management**: Add care tasks with title, category, duration, priority, time, and recurrence frequency.
- **Priority-based planning**: Selects the highest-priority tasks first while staying within the owner's available minutes.
- **Chronological sorting**: Displays scheduled tasks by `HH:MM` time, with unscheduled tasks moved to the end.
- **Filtering**: Shows all, incomplete, or completed tasks, and supports filtering tasks by pet in the backend.
- **Recurring tasks**: Automatically creates the next daily or weekly occurrence when a recurring task is marked complete.
- **Conflict detection**: Flags overlapping scheduled tasks before the user generates a final daily plan.
- **Plan explanation**: Explains how many minutes were used, which tasks were scheduled, and which tasks were skipped because of the time budget.

## Repository Structure

```text
.
├── app.py              # Streamlit user interface
├── main.py             # Command-line demo
├── pawpal_system.py    # Core classes and planner logic
├── tests/              # Automated tests
├── demo.png            # App screenshot
├── reflection.md       # Project reflection
├── pawpal_uml.mmd      # UML source
├── pawpal_uml.svg      # UML diagram
├── uml_final.png       # Final UML image
└── requirements.txt    # Python dependencies
```

## Getting Started

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run app.py
```

You can also run the command-line demo:

```bash
python main.py
```

## Testing

Run the full test suite:

```bash
python -m pytest
```

Run tests with verbose output:

```bash
python -m pytest -v
```

The current test suite includes 20 automated tests covering sorting, recurring task generation, conflict detection, daily plan budget handling, task filtering, task editing, pet task aggregation, and recurring follow-up creation.

## Confidence Level

**Confidence: 5/5**

The core scheduling logic is covered by automated tests, including happy paths and meaningful edge cases. The most important behaviors are verified: tasks are sorted correctly, recurring tasks generate the next occurrence, completed tasks are excluded from conflict checks, daily plans stay within the owner's time budget, and filters return the expected tasks.
