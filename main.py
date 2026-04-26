from datetime import date
from pawpal_system import CareTask, Pet, Owner, Planner

today = date.today()
owner = Owner(name="Alex", available_minutes_per_day=60)

dog = Pet(name="Buddy", species="Dog")
cat = Pet(name="Whiskers", species="Cat")
owner.add_pet(dog)
owner.add_pet(cat)

# Add tasks — intentionally create conflicts at 07:00 and 08:00
dog.add_care_task(CareTask(title="Morning walk", category="Exercise", duration_minutes=30,
                           priority=5, time="07:00", frequency="daily", due_date=today))
dog.add_care_task(CareTask(title="Feed breakfast", category="Feeding", duration_minutes=10,
                           priority=4, time="08:00", frequency="daily", due_date=today))
dog.add_care_task(CareTask(title="Brush coat", category="Grooming", duration_minutes=15,
                           priority=2, time="14:00", frequency="weekly", due_date=today))

cat.add_care_task(CareTask(title="Feed wet food", category="Feeding", duration_minutes=5,
                           priority=5, time="07:15", frequency="daily", due_date=today))
cat.add_care_task(CareTask(title="Litter box cleanup", category="Hygiene", duration_minutes=20,
                           priority=4, time="07:50", frequency="daily", due_date=today))

planner = Planner()

# --- Conflict detection: per pet ---
print("=" * 50)
print("  CONFLICT CHECK: Buddy's tasks")
print("=" * 50)
warnings = planner.detect_conflicts(dog.list_tasks())
if warnings:
    for w in warnings:
        print(f"  ⚠ {w}")
else:
    print("  No conflicts found.")

print(f"\n{'=' * 50}")
print("  CONFLICT CHECK: Whiskers' tasks")
print("=" * 50)
warnings = planner.detect_conflicts(cat.list_tasks())
if warnings:
    for w in warnings:
        print(f"  ⚠ {w}")
else:
    print("  No conflicts found.")

# --- Conflict detection: across ALL pets ---
print(f"\n{'=' * 50}")
print("  CONFLICT CHECK: All tasks across all pets")
print("=" * 50)
all_tasks = owner.get_all_tasks()
warnings = planner.detect_conflicts(all_tasks)
if warnings:
    for w in warnings:
        print(f"  ⚠ {w}")
else:
    print("  No conflicts found.")

# --- Build daily plan ---
print(f"\n{'=' * 50}")
print(f"  TODAY'S SCHEDULE for {owner.name}")
print("=" * 50)
for pet in owner.pets:
    print(f"\n--- {pet.name} ({pet.species}) ---")
    plan = planner.build_daily_plan(owner, pet)
    print(planner.explain_plan(plan))
