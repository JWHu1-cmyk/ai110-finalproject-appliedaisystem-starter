from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


@dataclass
class CareTask:
    title: str
    category: str
    duration_minutes: int
    priority: int  # higher = more important
    completed: bool = False
    time: str = ""  # scheduled time in "HH:MM" format
    frequency: str = "once"  # "once", "daily", or "weekly"
    due_date: Optional[date] = None

    def edit(self, title: str = None, duration_minutes: int = None, priority: int = None) -> None:
        """Update task fields in place."""
        if title is not None:
            self.title = title
        if duration_minutes is not None:
            self.duration_minutes = duration_minutes
        if priority is not None:
            self.priority = priority

    def mark_complete(self) -> Optional["CareTask"]:
        """Mark this task as completed. Returns a new CareTask for the next occurrence if recurring."""
        self.completed = True
        if self.frequency == "daily":
            next_date = (self.due_date or date.today()) + timedelta(days=1)
            return CareTask(
                title=self.title, category=self.category,
                duration_minutes=self.duration_minutes, priority=self.priority,
                time=self.time, frequency=self.frequency, due_date=next_date,
            )
        elif self.frequency == "weekly":
            next_date = (self.due_date or date.today()) + timedelta(weeks=1)
            return CareTask(
                title=self.title, category=self.category,
                duration_minutes=self.duration_minutes, priority=self.priority,
                time=self.time, frequency=self.frequency, due_date=next_date,
            )
        return None

    def compare_priority(self, other: "CareTask") -> int:
        """Return positive if self has higher priority, negative if lower, 0 if equal."""
        return self.priority - other.priority


@dataclass
class Pet:
    name: str
    species: str
    notes: str = ""
    tasks: list[CareTask] = field(default_factory=list)

    def add_care_task(self, task: CareTask) -> None:
        """Append a CareTask to this pet's task list."""
        self.tasks.append(task)

    def list_tasks(self) -> list[CareTask]:
        """Return all care tasks for this pet."""
        return list(self.tasks)

    def mark_task_complete(self, task: CareTask) -> Optional[CareTask]:
        """Mark a task complete and auto-add the next occurrence if recurring."""
        next_task = task.mark_complete()
        if next_task is not None:
            self.tasks.append(next_task)
        return next_task


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def update_profile(self, name: str = None, available_minutes: int = None, preferences: dict = None) -> None:
        """Update owner profile fields."""
        if name is not None:
            self.name = name
        if available_minutes is not None:
            self.available_minutes_per_day = available_minutes
        if preferences is not None:
            self.preferences = preferences

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list[CareTask]:
        """Gather and return all tasks across all pets."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.list_tasks())
        return all_tasks


class Planner:
    def __init__(self) -> None:
        self.explanation: str = ""

    def build_daily_plan(self, owner: Owner, pet: Pet, tasks: list[CareTask] = None) -> list[CareTask]:
        """Select and order tasks into a daily plan that fits the owner's time budget.

        Sorts tasks by priority (highest first), then greedily adds tasks
        until the owner's available minutes are exhausted.
        """
        if tasks is None:
            tasks = pet.list_tasks()

        budget = owner.available_minutes_per_day
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

        plan = []
        total_minutes = 0
        skipped = []

        for task in sorted_tasks:
            if total_minutes + task.duration_minutes <= budget:
                plan.append(task)
                total_minutes += task.duration_minutes
            else:
                skipped.append(task)

        self.explanation = self._build_explanation(plan, skipped, total_minutes, budget)
        return plan

    def explain_plan(self, plan: list[CareTask]) -> str:
        """Return the stored explanation from the most recent build_daily_plan call."""
        return self.explanation

    def sort_by_time(self, tasks: list[CareTask]) -> list[CareTask]:
        """Sort tasks by their scheduled time (HH:MM format), earliest first."""
        return sorted(tasks, key=lambda t: t.time if t.time else "99:99")

    def filter_by_status(self, tasks: list[CareTask], completed: bool = False) -> list[CareTask]:
        """Filter tasks by completion status."""
        return [t for t in tasks if t.completed == completed]

    def filter_by_pet(self, owner: Owner, pet_name: str) -> list[CareTask]:
        """Filter tasks belonging to a specific pet by name."""
        for pet in owner.pets:
            if pet.name == pet_name:
                return pet.list_tasks()
        return []

    def detect_conflicts(self, tasks: list[CareTask]) -> list[str]:
        """Return warning messages for tasks that overlap in time."""
        warnings = []
        # Build list of (start_minutes, end_minutes, task) for tasks with a time
        scheduled = []
        for task in tasks:
            if not task.time or task.completed:
                continue
            parts = task.time.split(":")
            start = int(parts[0]) * 60 + int(parts[1])
            end = start + task.duration_minutes
            scheduled.append((start, end, task))

        # Sort by start time then check each pair for overlap
        scheduled.sort(key=lambda x: x[0])
        for i in range(len(scheduled)):
            for j in range(i + 1, len(scheduled)):
                s1, e1, t1 = scheduled[i]
                s2, e2, t2 = scheduled[j]
                if s2 < e1:  # overlap: task j starts before task i ends
                    warnings.append(
                        f"Conflict: '{t1.title}' ({t1.time}-{e1 // 60:02d}:{e1 % 60:02d}) "
                        f"overlaps with '{t2.title}' ({t2.time}-{e2 // 60:02d}:{e2 % 60:02d})"
                    )
                else:
                    break  # no more overlaps for task i since list is sorted
        return warnings

    def _fits_within_budget(self, tasks: list[CareTask], minutes: int) -> bool:
        """Check whether total duration of tasks fits within the given minutes."""
        return sum(t.duration_minutes for t in tasks) <= minutes

    def _build_explanation(self, plan: list[CareTask], skipped: list[CareTask],
                           used_minutes: int, budget: int) -> str:
        """Generate a human-readable explanation of the plan."""
        lines = []
        lines.append(f"Daily plan uses {used_minutes} of {budget} available minutes.")

        if plan:
            lines.append("Scheduled tasks (highest priority first):")
            for i, task in enumerate(plan, 1):
                lines.append(f"  {i}. {task.title} ({task.category}) — "
                             f"{task.duration_minutes} min, priority {task.priority}")

        if skipped:
            lines.append("Skipped (not enough time):")
            for task in skipped:
                lines.append(f"  - {task.title} ({task.category}) — "
                             f"{task.duration_minutes} min, priority {task.priority}")

        return "\n".join(lines)
