# PawPal+ (Module 2 Project)

You are building ** reamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.



A Streamlit app that helps pet owners plan and track daily care tasks across multiple pets.
Features

Add an owner profile with daily time budget and preferred care windows
Register multiple pets and assign tasks with priority, duration, and frequency
Generate a prioritized daily schedule that respects the owner's time constraints
Mark tasks complete directly from the schedule view


Smarter Scheduling

Three algorithmic features were added in Phase 3 to make the scheduler more
robust and realistic.
Recurring tasks
Tasks with a frequency of "daily" or "weekly" automatically re-queue
themselves when completed. Calling pet.complete_task(task_id) marks the
current task done and appends a fresh copy with its due_date set to
today + 1 day (daily) or today + 7 days (weekly), calculated using
Python's timedelta. Tasks marked "as_needed" are completed and removed
with no recurrence.
Conflict detection
Scheduler.detect_conflicts() scans the generated plan for overlapping time
slots using the standard interval-overlap test:
slot A and slot B overlap when: A.start < B.end AND B.start < A.end
All times are compared as integer minutes to keep the logic simple. The method
never raises an exception — it always returns a list of plain-English warning
strings so the UI or CLI can display them gracefully.
Sorting and filtering
Two utility methods give callers flexible access to the generated plan:

sort_by_time() — returns the plan sorted chronologically by start time,
regardless of the priority order it was generated in.
filter_tasks(completed, pet_name) — returns a filtered subset of the plan
by completion status, pet name, or both combined. The original plan is never
mutated.