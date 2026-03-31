"""
PawPal+ — Demo / testing ground
main.py

Demonstrates sorting, filtering, and recurring task automation.

"""

from datetime import date, time
from pawpal_system import Owner, Pet, Task, Scheduler, ScheduledTask

WIDTH = 62

def divider(label: str = "") -> None:
    if label:
        print(f"\n{'─' * 4} {label} {'─' * (WIDTH - len(label) - 6)}")
    else:
        print("─" * WIDTH)

def print_plan(items, title: str) -> None:
    divider(title)
    if not items:
        print("  (no results)")
        return
    for item in items:
        status = "checked" if item.task.completed else "⬜"
        print(
            f"  {status}  {item.format_slot()}"
            f"  {item.pet.name:<8}"
            f"  {item.task.name:<22}"
            f"  pri {item.task.priority}"
        )


# ---------------------------------------------------------------------------
# 1. Build data — tasks added intentionally OUT of time order
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", daily_hours=3.0, preferred_times=["morning"])

rex = Pet(name="Rex", species="Dog", age=5)
# Added in jumbled priority/window order on purpose
rex.add_task(Task("Teeth brushing",  10, priority=2, time_window="evening",   frequency="daily"))
rex.add_task(Task("Evening walk",    30, priority=4, time_window="evening",   frequency="daily"))
rex.add_task(Task("Flea treatment",   5, priority=5, time_window="any",       frequency="weekly"))
rex.add_task(Task("Morning walk",    30, priority=5, time_window="morning",   frequency="daily"))

luna = Pet(name="Luna", species="Cat", age=2)
luna.add_task(Task("Enrichment play", 20, priority=3, time_window="afternoon", frequency="daily"))
luna.add_task(Task("Litter box",      10, priority=4, time_window="any",       frequency="daily"))
luna.add_task(Task("Feeding",         10, priority=5, time_window="morning",   frequency="daily"))

owner.add_pet(rex)
owner.add_pet(luna)


# ---------------------------------------------------------------------------
# 2. Generate plan (priority-sorted by Scheduler)
# ---------------------------------------------------------------------------

scheduler = Scheduler(owner)
plan = scheduler.generate_plan()

print()
print("╔" + "═" * WIDTH + "╗")
print("║" + "  🐾  PawPal+ — Sorting & Filtering Demo".center(WIDTH) + "║")
print("╚" + "═" * WIDTH + "╝")


# ---------------------------------------------------------------------------
# 3. Raw plan (priority order — what Scheduler produced)
# ---------------------------------------------------------------------------

print_plan(plan, "Raw plan — priority order (Scheduler output)")


# ---------------------------------------------------------------------------
# 4. sort_by_time() — same tasks, re-ordered by start time
# ---------------------------------------------------------------------------

by_time = scheduler.sort_by_time()
print_plan(by_time, "sort_by_time() — chronological order")


# ---------------------------------------------------------------------------
# 5. filter_tasks(completed=False) — pending only
# ---------------------------------------------------------------------------

pending = scheduler.filter_tasks(completed=False)
print_plan(pending, "filter_tasks(completed=False) — pending only")


# ---------------------------------------------------------------------------
# 6. Mark a couple of tasks complete, then filter again
# ---------------------------------------------------------------------------

# Simulate completing the first two tasks
for item in plan[:2]:
    item.task.mark_complete()

completed = scheduler.filter_tasks(completed=True)
print_plan(completed, "filter_tasks(completed=True) — after marking 2 done")

still_pending = scheduler.filter_tasks(completed=False)
print_plan(still_pending, "filter_tasks(completed=False) — remaining tasks")


# ---------------------------------------------------------------------------
# 7. filter_tasks(pet_name=...) — tasks for one pet only
# ---------------------------------------------------------------------------

rex_tasks  = scheduler.filter_tasks(pet_name="Rex")
luna_tasks = scheduler.filter_tasks(pet_name="Luna")

print_plan(rex_tasks,  "filter_tasks(pet_name='Rex')")
print_plan(luna_tasks, "filter_tasks(pet_name='Luna')")


# ---------------------------------------------------------------------------
# 8. Combined filter — Luna's pending tasks only
# ---------------------------------------------------------------------------

luna_pending = scheduler.filter_tasks(completed=False, pet_name="Luna")
print_plan(luna_pending, "filter_tasks(completed=False, pet_name='Luna')")


# ---------------------------------------------------------------------------
# 9. Summary
# ---------------------------------------------------------------------------

divider()
total      = len(plan)
done       = len(scheduler.filter_tasks(completed=True))
remaining  = len(scheduler.filter_tasks(completed=False))
used_mins  = sum(i.task.duration_mins for i in plan)

print(f"  Total scheduled : {total} tasks  ({used_mins} min)")
print(f"  Completed       : {done}")
print(f"  Still pending   : {remaining}")
print(f"  Budget remaining: {owner.get_available_minutes() - used_mins} min")
divider()
print()


# ---------------------------------------------------------------------------
# 11. Conflict detection demo
# ---------------------------------------------------------------------------

print("╔" + "═" * WIDTH + "╗")
print("║" + "  Conflict Detection Demo".center(WIDTH) + "║")
print("╚" + "═" * WIDTH + "╝")

conflict_owner = Owner(name="Casey", daily_hours=4.0)
dog = Pet(name="Rex",   species="Dog", age=3)
cat = Pet(name="Mochi", species="Cat", age=1)
conflict_owner.add_pet(dog)
conflict_owner.add_pet(cat)

# Build a scheduler and manually inject two overlapping slots
conflict_scheduler = Scheduler(conflict_owner)

walk   = Task("Morning walk",    30, priority=5, time_window="morning", frequency="daily")
feed   = Task("Cat feeding",     15, priority=5, time_window="morning", frequency="daily")
groom  = Task("Dog grooming",    20, priority=3, time_window="morning", frequency="weekly")

# Deliberately overlap: walk 07:00–07:30, feeding 07:15–07:30, groom 07:00–07:20
conflict_scheduler.plan = [
    ScheduledTask(dog, walk,  time(7, 0),  time(7, 30), reason="high priority"),
    ScheduledTask(cat, feed,  time(7, 15), time(7, 30), reason="high priority"),   # overlaps walk
    ScheduledTask(dog, groom, time(7, 0),  time(7, 20), reason="same window"),     # overlaps walk
]

divider("Injected schedule (contains conflicts)")
print_plan(conflict_scheduler.plan, "All slots")

divider("Running detect_conflicts()")
conflicts = conflict_scheduler.detect_conflicts()

if conflicts:
    for w in conflicts:
        print(f"  {w}")
else:
    print("  No conflicts found.")

divider()
print(f"  {len(conflicts)} conflict(s) detected.")
divider()
print()


# ---------------------------------------------------------------------------
# 10. Recurring task demo
# ---------------------------------------------------------------------------

print("╔" + "═" * WIDTH + "╗")
print("║" + "  🔁  Recurring Task Demo".center(WIDTH) + "║")
print("╚" + "═" * WIDTH + "╝")

demo_pet = Pet(name="Biscuit", species="Dog", age=2)
demo_pet.add_task(Task("Morning walk",   30, priority=5,
                       time_window="morning", frequency="daily",
                       due_date=date.today()))
demo_pet.add_task(Task("Flea treatment",  5, priority=5,
                       time_window="any",    frequency="weekly",
                       due_date=date.today()))
demo_pet.add_task(Task("Vet check",      60, priority=3,
                       time_window="any",    frequency="as_needed"))

def show_tasks(pet: Pet, label: str) -> None:
    divider(label)
    for t in pet.tasks:
        status   = "checked" if t.completed else "⬜"
        due_str  = f"due {t.due_date}" if t.due_date else "no due date"
        print(f"  {status}  {t.name:<24}  {t.frequency:<10}  {due_str}")

show_tasks(demo_pet, "Before completing any tasks")

# Complete each task via pet.complete_task() — auto re-queues recurring ones
for task in list(demo_pet.tasks):           # snapshot so we don't iterate
    demo_pet.complete_task(task.task_id)    # new tasks appended during loop

show_tasks(demo_pet, "After completing all tasks")

divider("Explanation")
for t in demo_pet.tasks:
    if not t.completed:
        print(f"  ↻  '{t.name}' re-queued → next due {t.due_date}")
    else:
        freq_note = "(as_needed — not re-queued)" if t.frequency == "as_needed" else ""
        print(f"'{t.name}' completed {freq_note}")
divider()
print()