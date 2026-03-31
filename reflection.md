# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.


The design uses four core classes: Owner, Pet, Task, and Scheduler. Here's how I divided responsibilities:

Owner holds identifying info (name, available hours per day) and owns a Pet. It's a lightweight data container — no logic lives here.

Pet stores the animal's details (name, species, age) and maintains the list of Task objects. It acts as an aggregate root for the pet's care activities.

Task is the richest data class. It holds duration, priority (1–5), preferred time window (morning/afternoon/evening), frequency, and a completed flag. It doesn't schedule itself — it just describes what needs doing.

Scheduler is where all the logic lives. It takes a Pet and an Owner, runs generate_plan(), and returns an ordered list of ScheduledTask wrappers (task + assigned time slot). The separation means you can unit-test scheduling logic independently of any UI concerns.

A ScheduledTask is a small result type — it pairs a Task with a concrete start time and carries an optional reason string used by the "explain the plan" feature.





- What classes did you include, and what responsibilities did you assign to each?

Owner holds the pet owner's profile data — their name, how many hours per day they have available, and their preferred times of day. Its responsibility is purely to represent constraints on the human side of the schedule.

Pet stores the animal's identifying info (name, species, age) and maintains the master list of Task objects. It acts as the aggregate root for all care activities — you add, remove, and query tasks through the pet, not independently.

Task represents a single care activity. It stores everything needed to describe the work: duration, priority (1–5), preferred time window, frequency, and a completion flag. Crucially, Task has no scheduling logic — it only describes what needs to be done and how important it is.

Scheduler is where all the logic lives. It takes a Pet and an Owner as inputs, applies priority sorting and time-window fitting against the owner's available hours, and produces a daily plan. It also carries the explain_plan() method that generates human-readable reasoning for each placement decision.

ScheduledTask is a lightweight result type — it wraps a Task with a concrete start time, end time, and a reason string. Rather than mutating the original Task objects, the scheduler produces a fresh list of these wrappers each time a plan is generated. This keeps tasks reusable and makes the scheduler easy to test in isolation.





**b. Design changes**


- Did your design change during implementation?

Yes, the design changed in two notable ways during implementation.

- If yes, describe at least one change and why you made it.

First, Owner was extended to hold a list of Pet objects rather than a
single one. The original UML modeled a one-to-one relationship, but the
scenario called for a "busy pet owner" who realistically has more than one
animal. Adding owner.pets: list[Pet] and an add_pet() method made the
model more realistic without breaking any existing logic.
Second, a complete_task() method was added to Pet rather than having
callers invoke task.mark_complete() directly. This was necessary once
recurring tasks were introduced — the re-queuing logic (creating the next
occurrence and appending it to the pet's task list) needed a home, and Pet
was the right place because it owns the task list. Putting it in Scheduler
would have given the scheduler write access to pet internals, which violated
the encapsulation goal.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

The scheduler considers three constraints:

Time budget — the owner's daily_hours caps the total minutes that can
be scheduled. No task is added to the plan if it would exceed this limit.
Priority — tasks ranked 1–5 by the owner are sorted descending so
high-priority tasks are always placed first.
Time window preference — each task declares a preferred window (morning,
afternoon, evening, or any), and the scheduler assigns start times from the
matching window's base hour.

- How did you decide which constraints mattered most?


Priority was treated as the primary constraint because it directly encodes the
owner's intent. Time budget is a hard ceiling — exceeding it would make the
plan impossible to follow. Time window is a soft preference that improves
usability without affecting correctness.


**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

The scheduler uses a greedy algorithm: it places the highest-priority task
first and keeps going until the budget runs out. This means it can sometimes
leave small gaps that a smarter algorithm could fill.
For example, if 35 minutes remain and a 30-minute walk (priority 4) and two
10-minute tasks (priority 3) are pending, the greedy scheduler picks the walk,
leaving only 5 minutes — enough for one small task but not both. An optimal
packer might skip the walk and fit both 10-minute tasks instead, completing
more total work.

- Why is that tradeoff reasonable for this scenario?

This tradeoff is reasonable here because the owner explicitly set priorities.
Skipping a priority-4 task to fit two priority-3 tasks would violate the
owner's stated preferences. Simplicity and predictability matter more than
maximum task throughput for a daily pet care tool.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

AI was used at every stage of the project:

Design — generating the initial UML class skeleton and discussing which
class should own which responsibility (e.g. whether complete_task belonged
on Pet or Scheduler).
Implementation — fleshing out method bodies, writing the interval overlap
formula for conflict detection, and implementing timedelta arithmetic for
recurring tasks.
Refactoring — asking for more Pythonic alternatives to existing methods
and evaluating whether the suggestions were actually improvements.
Debugging — diagnosing the Git push errors caused by divergent branch
histories.


- What kinds of prompts or questions were most helpful?

The most useful prompts were specific and grounded in existing code — for
example: "Based on the skeletons in pawpal_system.py, how should the
Scheduler retrieve all tasks from the Owner's pets?" Open-ended prompts like
"how do I make this better" produced generic advice; file-specific prompts
produced actionable code.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

When asked to simplify sort_by_priority(), the AI suggested replacing
sorted() with .sort() to save one line. The suggestion was not accepted
because .sort() mutates the input list in place, while sorted() returns a
new list and leaves the original unchanged. The non-mutation behaviour is
important for testability — a test can call sort_by_priority() and still
inspect the original list afterward. The AI's version was more concise but
introduced a subtle side effect that could cause hard-to-trace bugs. The
original was kept and the reasoning was documented in reflection.md.

- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

Eight behaviors were tested in tests/test_pawpal.py:

mark_complete() flips completed from False to True
add_task() increases the pet's task count by exactly one
get_pending_tasks() excludes completed tasks
remove_task() decreases the task count
Scheduler never schedules more minutes than the owner's budget
Scheduler always places higher-priority tasks before lower-priority ones
get_available_minutes() correctly converts hours to minutes
format_slot() returns the expected "HH:MM – HH:MM" string

- Why were these tests important?
The budget and priority-order tests are the most important because they verify
the two guarantees the scheduler is built around. If either broke silently
after a refactor, the output would look correct but be wrong.

**b. Confidence**

- How confident are you that your scheduler works correctly?

Confidence is moderate-to-high for the happy path. The core scheduling loop,
sorting, filtering, and recurring task logic all pass their tests and produce
correct terminal output in main.py.

- What edge cases would you test next if you had more time?

Edge cases that would be tested next with more time:

A task whose duration_mins exactly equals the remaining budget (boundary
condition on fits_in_window)
An owner with daily_hours = 0 (should produce an empty plan, not crash)
Two tasks with identical priority, duration, and time window (tie-breaking
behaviour is currently undefined)
A pet with no tasks (should not affect the plan or raise an error)
Recurring tasks completing across a month boundary (e.g. January 31 + 1 day)



---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

The separation between the data layer (Task, Pet, Owner) and the logic
layer (Scheduler) worked well throughout the project. Every time a new
feature was added — recurring tasks, conflict detection, sorting — there was a
clear, obvious place to put it without touching unrelated code. The unit tests
were also easy to write because each class had a single, well-defined
responsibility.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

The time window system is too rigid. Right now, "morning" always starts at
07:00 and "afternoon" always starts at 12:00, with no overlap detection between
windows. A better design would let the owner set their own window boundaries
and would detect when two windows overlap in the available hours. The conflict
detection feature exposes this gap — it's possible to inject overlapping
ScheduledTask objects that generate_plan() itself would never produce,
which means the detection is tested against manually crafted data rather than
real scheduler output.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

The most important thing learned was that AI tools are most useful as a
thinking partner rather than a code generator. The best interactions were
conversations — describing a design decision, getting a concrete suggestion,
and then reasoning about whether the suggestion actually fit the constraints.
Accepting AI output without reading it carefully introduced subtle bugs (like
the in-place sort mutation). The skill is not in prompting AI to write code;
it is in knowing enough to evaluate what it writes.

