"""
PawPal+ — Logic Layer
pawpal_system.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import Optional, Callable
import uuid

# Time window → default start hour (24-h)
WINDOW_START: dict[str, int] = {
    "morning":   7,
    "afternoon": 12,
    "evening":   17,
    "any":       7,
}


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet care activity."""

    name: str
    duration_mins: int
    priority: int                   # 1 (lowest) – 5 (highest)
    time_window: str                # "morning" | "afternoon" | "evening" | "any"
    frequency: str                  # "daily" | "weekly" | "as_needed"
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    completed: bool = False
    due_date: Optional[date] = None

    # ------------------------------------------------------------------
    def mark_complete(self) -> "Task | None":
        """
        Mark this task completed and return a new recurring instance if
        frequency is 'daily' or 'weekly'; returns None for 'as_needed'.

        Usage
        -----
            next_task = task.mark_complete()
            if next_task:
                pet.add_task(next_task)
        """
        self.completed = True

        delta: dict[str, timedelta] = {
            "daily":  timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }

        if self.frequency not in delta:
            return None

        next_due = (self.due_date or date.today()) + delta[self.frequency]

        return Task(
            name=self.name,
            duration_mins=self.duration_mins,
            priority=self.priority,
            time_window=self.time_window,
            frequency=self.frequency,
            due_date=next_due,
            completed=False,
            # fresh task_id generated automatically by the dataclass default
        )

    def is_overdue(self) -> bool:
        """Return True if a due date is set and has passed."""
        if self.due_date is None:
            return False
        return date.today() > self.due_date

    def to_dict(self) -> dict:
        """Serialize task to a plain dictionary."""
        return {
            "task_id":      self.task_id,
            "name":         self.name,
            "duration_mins": self.duration_mins,
            "priority":     self.priority,
            "time_window":  self.time_window,
            "frequency":    self.frequency,
            "completed":    self.completed,
            "due_date":     self.due_date.isoformat() if self.due_date else None,
        }


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """A pet profile that owns a list of care tasks."""

    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    # ------------------------------------------------------------------
    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by its ID. Silent no-op if not found."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def complete_task(self, task_id: str) -> None:
        """
        Mark a task complete by ID and automatically re-queue it if it
        recurs. This is the preferred way to complete tasks — callers
        should use this instead of calling task.mark_complete() directly.
        """
        for task in self.tasks:
            if task.task_id == task_id:
                next_task = task.mark_complete()
                if next_task:
                    self.add_task(next_task)
                return

    def get_pending_tasks(self) -> list[Task]:
        """Return all tasks that are not yet completed."""
        return [t for t in self.tasks if not t.completed]


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """
    A pet owner who may have one or more pets.

    The Owner is the Scheduler's entry point: it aggregates all pets and
    exposes helpers so the Scheduler never needs to iterate pets directly.
    """

    name: str
    daily_hours: float
    preferred_times: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    # ------------------------------------------------------------------
    def get_available_minutes(self) -> int:
        """Return total available care time in minutes."""
        return int(self.daily_hours * 60)

    def set_preferred_times(self, times: list[str]) -> None:
        """Replace the owner's preferred time windows."""
        self.preferred_times = times

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def get_all_pending_tasks(self) -> list[tuple[Pet, Task]]:
        """
        Return every pending task across all pets as (pet, task) pairs.

        This is the method the Scheduler calls to retrieve its work list.
        Keeping it on Owner means the Scheduler never touches pet internals.
        """
        return [
            (pet, task)
            for pet in self.pets
            for task in pet.get_pending_tasks()
        ]


# ---------------------------------------------------------------------------
# ScheduledTask
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A Task paired with a concrete time slot and scheduling reason."""

    pet: Pet
    task: Task
    start_time: time
    end_time: time
    reason: str = ""

    # ------------------------------------------------------------------
    def get_duration(self) -> int:
        """Return slot duration in minutes."""
        start_dt = timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)
        end_dt   = timedelta(hours=self.end_time.hour,   minutes=self.end_time.minute)
        return int((end_dt - start_dt).total_seconds() // 60)

    def format_slot(self) -> str:
        """Return a human-readable slot string, e.g. '08:00 – 08:30'."""
        return (
            f"{self.start_time.strftime('%H:%M')} – "
            f"{self.end_time.strftime('%H:%M')}"
        )

    def __str__(self) -> str:
        return (
            f"[{self.format_slot()}] {self.pet.name}: {self.task.name} "
            f"(priority {self.task.priority}) — {self.reason}"
        )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Generates a daily care plan from an Owner's pets and constraints.

    How it talks to Owner
    ---------------------
    The Scheduler calls owner.get_all_pending_tasks() to get a flat list of
    (Pet, Task) pairs. It never accesses owner.pets or pet.tasks directly —
    all pet/task access is mediated through Owner's public interface.
    """

    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.plan: list[ScheduledTask] = []

    # ------------------------------------------------------------------
    def generate_plan(self) -> list[ScheduledTask]:
        """
        Build and return a daily schedule.

        Algorithm
        ---------
        1. Pull all pending (pet, task) pairs from the owner.
        2. Sort by priority desc, then by preferred time window alignment.
        3. Walk through tasks; assign start times respecting time windows
           and the owner's total available minutes.
        4. Stop when the budget is exhausted.
        """
        self.reset_plan()

        pairs = self.owner.get_all_pending_tasks()
        sorted_pairs = self.sort_by_priority(pairs)

        # Track minutes consumed per window bucket
        minutes_used = 0
        # Current cursor per window (hour offset from window start)
        window_cursors: dict[str, int] = {w: 0 for w in WINDOW_START}

        budget = self.owner.get_available_minutes()

        for pet, task in sorted_pairs:
            if not self.fits_in_window(task, minutes_used, budget):
                continue

            window = task.time_window if task.time_window in WINDOW_START else "any"
            base_hour = WINDOW_START[window]

            # Prefer owner's preferred times for "any" tasks
            if window == "any" and self.owner.preferred_times:
                window = self.owner.preferred_times[0]
                base_hour = WINDOW_START.get(window, 7)

            cursor_mins = window_cursors[window]
            start_total = base_hour * 60 + cursor_mins
            end_total   = start_total + task.duration_mins

            start = time(start_total // 60, start_total % 60)
            end   = time(end_total   // 60, end_total   % 60)

            reason = self._build_reason(task, minutes_used, budget)

            self.plan.append(ScheduledTask(
                pet=pet,
                task=task,
                start_time=start,
                end_time=end,
                reason=reason,
            ))

            window_cursors[window] += task.duration_mins
            minutes_used += task.duration_mins

        return self.plan

    # ------------------------------------------------------------------
    def sort_by_priority(
        self, pairs: list[tuple[Pet, Task]]
    ) -> list[tuple[Pet, Task]]:
        """
        Sort (pet, task) pairs by:
          1. Priority descending (5 first).
          2. Overdue status (overdue tasks bubble up within same priority).
          3. Duration ascending (quick wins scheduled before long tasks at
             equal priority).
        """
        return sorted(
            pairs,
            key=lambda pt: (
                -pt[1].priority,
                not pt[1].is_overdue(),
                pt[1].duration_mins,
            ),
        )

    def fits_in_window(
        self, task: Task, minutes_used: int, budget: int
    ) -> bool:
        """
        Return True if adding this task keeps total time within the owner's
        daily budget.
        """
        return minutes_used + task.duration_mins <= budget

    def explain_plan(self) -> list[str]:
        """Return one plain-English explanation string per scheduled task."""
        return [str(st) for st in self.plan]

    def reset_plan(self) -> None:
        """Clear the current plan so a fresh one can be generated."""
        self.plan = []

    # ------------------------------------------------------------------
    # Sorting & filtering
    # ------------------------------------------------------------------

    def sort_by_time(self) -> list[ScheduledTask]:
        """
        Return plan sorted ascending by start_time ("HH:MM").
        Uses a lambda key on start_time so "07:00" < "12:00" < "17:30".
        """
        return sorted(
            self.plan,
            key=lambda st: (st.start_time.hour, st.start_time.minute),
        )

    def filter_tasks(
        self,
        completed: bool | None = None,
        pet_name: str | None = None,
    ) -> list[ScheduledTask]:
        """
        Filter the current plan by completion status, pet name, or both.

        Parameters
        ----------
        completed : bool | None
            True  → only completed tasks
            False → only pending tasks
            None  → no filter on status
        pet_name : str | None
            Case-insensitive pet name to match. None → all pets.

        Returns a new list; self.plan is never mutated.
        """
        results = self.plan

        if completed is not None:
            results = [s for s in results if s.task.completed == completed]

        if pet_name is not None:
            results = [
                s for s in results
                if s.pet.name.lower() == pet_name.lower()
            ]

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_reason(self, task: Task, used: int, budget: int) -> str:
        parts = []
        if task.priority == 5:
            parts.append("top priority")
        elif task.priority >= 4:
            parts.append("high priority")
        if task.is_overdue():
            parts.append("overdue")
        remaining = budget - used
        parts.append(f"{remaining} min remaining in budget")
        return "; ".join(parts) if parts else "fits within daily schedule"


# ---------------------------------------------------------------------------
# Quick smoke-test  (python pawpal_system.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Build sample data
    owner = Owner(name="Alex", daily_hours=2.0, preferred_times=["morning"])

    dog = Pet(name="Biscuit", species="Dog", age=3)
    dog.add_task(Task("Morning walk",    30, priority=5, time_window="morning",   frequency="daily"))
    dog.add_task(Task("Evening walk",    30, priority=4, time_window="evening",   frequency="daily"))
    dog.add_task(Task("Flea medication", 5,  priority=5, time_window="any",       frequency="weekly"))
    dog.add_task(Task("Teeth brushing",  10, priority=3, time_window="evening",   frequency="daily"))

    cat = Pet(name="Mochi", species="Cat", age=2)
    cat.add_task(Task("Feeding",         10, priority=5, time_window="morning",   frequency="daily"))
    cat.add_task(Task("Litter box",      10, priority=4, time_window="any",       frequency="daily"))
    cat.add_task(Task("Enrichment play", 20, priority=3, time_window="afternoon", frequency="daily"))

    owner.add_pet(dog)
    owner.add_pet(cat)

    # Generate and print plan
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    print(f"\n=== Daily Plan for {owner.name} ===")
    print(f"Budget: {owner.get_available_minutes()} min\n")
    for item in plan:
        print(item)

    print("\n--- Explanation ---")
    for line in scheduler.explain_plan():
        print(line)