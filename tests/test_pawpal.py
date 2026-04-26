from datetime import date, timedelta
from pawpal_system import CareTask, Pet, Owner, Planner


# --- Happy path tests ---

def test_mark_complete_changes_status():
    """Verify that calling mark_complete() changes the task's completed status."""
    task = CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Verify that adding a task to a Pet increases that pet's task count."""
    pet = Pet(name="Buddy", species="Dog")
    assert len(pet.list_tasks()) == 0

    pet.add_care_task(CareTask(title="Feed", category="Feeding", duration_minutes=10, priority=4))
    assert len(pet.list_tasks()) == 1

    pet.add_care_task(CareTask(title="Walk", category="Exercise", duration_minutes=20, priority=3))
    assert len(pet.list_tasks()) == 2


def test_sort_by_time_returns_chronological_order():
    """Verify tasks are returned earliest-first when sorted by time."""
    planner = Planner()
    tasks = [
        CareTask(title="Afternoon groom", category="Grooming", duration_minutes=15, priority=2, time="14:00"),
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5, time="07:00"),
        CareTask(title="Lunch feed", category="Feeding", duration_minutes=10, priority=4, time="12:00"),
    ]
    sorted_tasks = planner.sort_by_time(tasks)
    assert [t.time for t in sorted_tasks] == ["07:00", "12:00", "14:00"]


def test_daily_recurrence_creates_next_day_task():
    """Confirm marking a daily task complete creates a new task for tomorrow."""
    today = date.today()
    task = CareTask(title="Morning walk", category="Exercise", duration_minutes=30,
                    priority=5, frequency="daily", due_date=today)
    next_task = task.mark_complete()

    assert task.completed is True
    assert next_task is not None
    assert next_task.completed is False
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.frequency == "daily"
    assert next_task.title == "Morning walk"


def test_weekly_recurrence_creates_next_week_task():
    """Confirm marking a weekly task complete creates a new task 7 days later."""
    today = date.today()
    task = CareTask(title="Brush coat", category="Grooming", duration_minutes=15,
                    priority=2, frequency="weekly", due_date=today)
    next_task = task.mark_complete()

    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_one_time_task_returns_none_on_complete():
    """Confirm a one-time task does not spawn a next occurrence."""
    task = CareTask(title="Vet visit", category="Health", duration_minutes=60,
                    priority=5, frequency="once")
    next_task = task.mark_complete()
    assert next_task is None


def test_conflict_detection_flags_overlapping_tasks():
    """Verify the planner detects two tasks that overlap in time."""
    planner = Planner()
    tasks = [
        CareTask(title="Morning walk", category="Exercise", duration_minutes=30, priority=5, time="07:00"),
        CareTask(title="Feed cat", category="Feeding", duration_minutes=10, priority=4, time="07:15"),
    ]
    warnings = planner.detect_conflicts(tasks)
    assert len(warnings) == 1
    assert "Morning walk" in warnings[0]
    assert "Feed cat" in warnings[0]


def test_conflict_detection_exact_same_time():
    """Verify two tasks at the exact same time are flagged as a conflict."""
    planner = Planner()
    tasks = [
        CareTask(title="Walk dog", category="Exercise", duration_minutes=20, priority=5, time="08:00"),
        CareTask(title="Feed cat", category="Feeding", duration_minutes=10, priority=4, time="08:00"),
    ]
    warnings = planner.detect_conflicts(tasks)
    assert len(warnings) == 1


# --- Edge case tests ---

def test_build_plan_with_no_tasks():
    """Verify the planner handles a pet with zero tasks gracefully."""
    owner = Owner(name="Alex", available_minutes_per_day=60)
    pet = Pet(name="Buddy", species="Dog")
    planner = Planner()

    plan = planner.build_daily_plan(owner, pet)
    assert plan == []
    assert "0 of 60" in planner.explain_plan(plan)


def test_build_plan_respects_time_budget():
    """Verify the planner does not exceed the owner's available minutes."""
    owner = Owner(name="Alex", available_minutes_per_day=30)
    pet = Pet(name="Buddy", species="Dog")
    pet.add_care_task(CareTask(title="Long walk", category="Exercise", duration_minutes=25, priority=5))
    pet.add_care_task(CareTask(title="Grooming", category="Grooming", duration_minutes=20, priority=3))

    planner = Planner()
    plan = planner.build_daily_plan(owner, pet)

    total = sum(t.duration_minutes for t in plan)
    assert total <= 30
    assert len(plan) == 1  # only the walk fits


def test_conflict_detection_no_conflicts():
    """Verify no warnings when tasks don't overlap."""
    planner = Planner()
    tasks = [
        CareTask(title="Walk", category="Exercise", duration_minutes=30, priority=5, time="07:00"),
        CareTask(title="Feed", category="Feeding", duration_minutes=10, priority=4, time="08:00"),
    ]
    warnings = planner.detect_conflicts(tasks)
    assert warnings == []


def test_pet_mark_task_complete_adds_recurring_task():
    """Verify Pet.mark_task_complete auto-adds the next occurrence."""
    pet = Pet(name="Buddy", species="Dog")
    task = CareTask(title="Walk", category="Exercise", duration_minutes=30,
                    priority=5, frequency="daily", due_date=date.today())
    pet.add_care_task(task)

    assert len(pet.tasks) == 1
    pet.mark_task_complete(task)
    assert len(pet.tasks) == 2
    assert pet.tasks[1].completed is False
    assert pet.tasks[1].due_date == date.today() + timedelta(days=1)


def test_sort_by_time_handles_missing_time():
    """Verify tasks without a time are sorted to the end."""
    planner = Planner()
    tasks = [
        CareTask(title="No time", category="Other", duration_minutes=10, priority=3),
        CareTask(title="Early", category="Exercise", duration_minutes=20, priority=5, time="06:00"),
    ]
    sorted_tasks = planner.sort_by_time(tasks)
    assert sorted_tasks[0].title == "Early"
    assert sorted_tasks[1].title == "No time"


def test_filter_by_status_returns_only_incomplete():
    """Verify filter_by_status returns only incomplete tasks by default."""
    planner = Planner()
    t1 = CareTask(title="Walk", category="Exercise", duration_minutes=30, priority=5)
    t2 = CareTask(title="Feed", category="Feeding", duration_minutes=10, priority=4, completed=True)
    t3 = CareTask(title="Groom", category="Grooming", duration_minutes=15, priority=2)

    incomplete = planner.filter_by_status([t1, t2, t3], completed=False)
    assert len(incomplete) == 2
    assert all(not t.completed for t in incomplete)

    completed = planner.filter_by_status([t1, t2, t3], completed=True)
    assert len(completed) == 1
    assert completed[0].title == "Feed"


def test_filter_by_pet_returns_correct_tasks():
    """Verify filter_by_pet returns tasks only for the named pet."""
    planner = Planner()
    owner = Owner(name="Alex", available_minutes_per_day=120)

    dog = Pet(name="Buddy", species="Dog")
    dog.add_care_task(CareTask(title="Walk", category="Exercise", duration_minutes=30, priority=5))

    cat = Pet(name="Whiskers", species="Cat")
    cat.add_care_task(CareTask(title="Feed", category="Feeding", duration_minutes=10, priority=4))

    owner.add_pet(dog)
    owner.add_pet(cat)

    buddy_tasks = planner.filter_by_pet(owner, "Buddy")
    assert len(buddy_tasks) == 1
    assert buddy_tasks[0].title == "Walk"


def test_filter_by_pet_unknown_name_returns_empty():
    """Verify filter_by_pet returns empty list for a pet name that doesn't exist."""
    planner = Planner()
    owner = Owner(name="Alex", available_minutes_per_day=60)
    result = planner.filter_by_pet(owner, "Ghost")
    assert result == []


def test_conflict_detection_ignores_completed_tasks():
    """Verify completed tasks are excluded from conflict detection."""
    planner = Planner()
    tasks = [
        CareTask(title="Walk", category="Exercise", duration_minutes=30, priority=5, time="07:00", completed=True),
        CareTask(title="Feed", category="Feeding", duration_minutes=10, priority=4, time="07:15"),
    ]
    warnings = planner.detect_conflicts(tasks)
    assert warnings == []


def test_edit_task_updates_fields():
    """Verify CareTask.edit updates only the specified fields."""
    task = CareTask(title="Walk", category="Exercise", duration_minutes=30, priority=3)
    task.edit(title="Long walk", priority=5)
    assert task.title == "Long walk"
    assert task.priority == 5
    assert task.duration_minutes == 30  # unchanged


def test_owner_get_all_tasks_aggregates_across_pets():
    """Verify Owner.get_all_tasks returns tasks from all pets."""
    owner = Owner(name="Alex", available_minutes_per_day=120)
    dog = Pet(name="Buddy", species="Dog")
    dog.add_care_task(CareTask(title="Walk", category="Exercise", duration_minutes=30, priority=5))
    cat = Pet(name="Whiskers", species="Cat")
    cat.add_care_task(CareTask(title="Feed", category="Feeding", duration_minutes=10, priority=4))
    cat.add_care_task(CareTask(title="Litter", category="Cleaning", duration_minutes=5, priority=3))
    owner.add_pet(dog)
    owner.add_pet(cat)

    all_tasks = owner.get_all_tasks()
    assert len(all_tasks) == 3


def test_build_plan_prioritizes_higher_priority_tasks():
    """Verify the planner selects higher-priority tasks first when budget is limited."""
    owner = Owner(name="Alex", available_minutes_per_day=35)
    pet = Pet(name="Buddy", species="Dog")
    pet.add_care_task(CareTask(title="Low", category="Other", duration_minutes=20, priority=1))
    pet.add_care_task(CareTask(title="High", category="Exercise", duration_minutes=20, priority=5))
    pet.add_care_task(CareTask(title="Mid", category="Feeding", duration_minutes=20, priority=3))

    planner = Planner()
    plan = planner.build_daily_plan(owner, pet)

    assert len(plan) == 1
    assert plan[0].title == "High"
