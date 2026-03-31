"""
PawPal+ — Unit tests
tests/test_pawpal.py

Run with:  python -m pytest
"""

import pytest
from pawpal_system import Owner, Pet, Task, Scheduler


# ---------------------------------------------------------------------------
# Fixtures — reusable sample objects
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_task():
    return Task(
        name="Morning walk",
        duration_mins=30,
        priority=5,
        time_window="morning",
        frequency="daily",
    )

@pytest.fixture
def sample_pet():
    return Pet(name="Rex", species="Dog", age=3)

@pytest.fixture
def sample_owner(sample_pet):
    owner = Owner(name="Jordan", daily_hours=2.0, preferred_times=["morning"])
    owner.add_pet(sample_pet)
    return owner


# ---------------------------------------------------------------------------
# Required tests (as specified in the brief)
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status(sample_task):
    """Calling mark_complete() should flip completed from False to True."""
    assert sample_task.completed is False
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_add_task_increases_count(sample_pet, sample_task):
    """Adding a task to a Pet should increase its task list length by 1."""
    before = len(sample_pet.tasks)
    sample_pet.add_task(sample_task)
    assert len(sample_pet.tasks) == before + 1


# ---------------------------------------------------------------------------
# Extra tests — cover more of the core logic
# ---------------------------------------------------------------------------

def test_get_pending_tasks_excludes_completed(sample_pet):
    """get_pending_tasks() should not return completed tasks."""
    t1 = Task("Walk",    30, 5, "morning", "daily")
    t2 = Task("Feeding", 10, 4, "morning", "daily")
    t2.mark_complete()
    sample_pet.add_task(t1)
    sample_pet.add_task(t2)

    pending = sample_pet.get_pending_tasks()
    assert t1 in pending
    assert t2 not in pending


def test_remove_task_decreases_count(sample_pet, sample_task):
    """remove_task() should drop the task from the pet's list."""
    sample_pet.add_task(sample_task)
    before = len(sample_pet.tasks)
    sample_pet.remove_task(sample_task.task_id)
    assert len(sample_pet.tasks) == before - 1


def test_scheduler_respects_budget():
    """Scheduler should not schedule more minutes than the owner's budget."""
    owner = Owner(name="Alex", daily_hours=0.5)   # only 30 min
    pet = Pet(name="Biscuit", species="Dog", age=2)
    pet.add_task(Task("Walk",      30, 5, "morning", "daily"))
    pet.add_task(Task("Play",      20, 4, "afternoon", "daily"))
    pet.add_task(Task("Grooming",  15, 3, "any", "weekly"))
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()
    total = sum(item.task.duration_mins for item in plan)
    assert total <= owner.get_available_minutes()


def test_scheduler_orders_by_priority():
    """Higher-priority tasks should appear earlier in the plan."""
    owner = Owner(name="Sam", daily_hours=2.0)
    pet = Pet(name="Mochi", species="Cat", age=1)
    pet.add_task(Task("Low task",  10, 1, "any", "daily"))
    pet.add_task(Task("High task", 10, 5, "any", "daily"))
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()
    priorities = [item.task.priority for item in plan]
    assert priorities == sorted(priorities, reverse=True)


def test_owner_get_available_minutes():
    """get_available_minutes() should convert daily_hours to minutes correctly."""
    owner = Owner(name="Lee", daily_hours=1.5)
    assert owner.get_available_minutes() == 90


def test_task_to_dict_contains_required_keys(sample_task):
    """to_dict() should include all expected keys."""
    d = sample_task.to_dict()
    for key in ("task_id", "name", "duration_mins", "priority",
                "time_window", "frequency", "completed", "due_date"):
        assert key in d


def test_scheduled_task_format_slot():
    """format_slot() should return a correctly formatted time range string."""
    from datetime import time as t
    from pawpal_system import ScheduledTask
    pet  = Pet("Rex", "Dog", 3)
    task = Task("Walk", 30, 5, "morning", "daily")
    st   = ScheduledTask(pet=pet, task=task,
                         start_time=t(8, 0), end_time=t(8, 30))
    assert st.format_slot() == "08:00 – 08:30"