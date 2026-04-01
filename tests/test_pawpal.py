"""
tests/test_pawpal.py - Automated tests for PawPal+ system.
Run with: python -m pytest
"""

import pytest
from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_pet():
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task(title="Evening walk", duration_minutes=30, time="18:00", priority="high", frequency="daily"))
    pet.add_task(Task(title="Morning walk", duration_minutes=20, time="07:30", priority="high", frequency="daily"))
    pet.add_task(Task(title="Medication",   duration_minutes=5,  time="08:00", priority="high", frequency="weekly"))
    return pet

@pytest.fixture
def sample_owner(sample_pet):
    owner = Owner(name="Jordan", available_minutes=120)
    owner.add_pet(sample_pet)
    return owner

@pytest.fixture
def scheduler(sample_owner):
    return Scheduler(sample_owner)


# ── Task tests ───────────────────────────────────────────────────────────────

def test_mark_complete_sets_flag():
    """mark_complete() should set completed = True."""
    task = Task(title="Walk", duration_minutes=20, time="08:00", frequency="once")
    task.mark_complete()
    assert task.completed is True

def test_mark_complete_once_returns_none():
    """A 'once' task should not generate a successor."""
    task = Task(title="Vet visit", duration_minutes=60, time="10:00", frequency="once")
    result = task.mark_complete()
    assert result is None

def test_daily_recurrence_next_day():
    """Completing a daily task should create a successor due tomorrow."""
    today = date.today()
    task = Task(title="Morning walk", duration_minutes=20, time="07:30", frequency="daily", due_date=today)
    successor = task.mark_complete()
    assert successor is not None
    assert successor.due_date == today + timedelta(days=1)
    assert successor.completed is False
    assert successor.title == "Morning walk"

def test_weekly_recurrence_next_week():
    """Completing a weekly task should create a successor due in 7 days."""
    today = date.today()
    task = Task(title="Grooming", duration_minutes=30, time="09:00", frequency="weekly", due_date=today)
    successor = task.mark_complete()
    assert successor is not None
    assert successor.due_date == today + timedelta(weeks=1)


# ── Pet tests ─────────────────────────────────────────────────────────────────

def test_add_task_increases_count(sample_pet):
    """Adding a task should increase the pet's task count by 1."""
    before = len(sample_pet.tasks)
    sample_pet.add_task(Task(title="New task", duration_minutes=10, time="12:00"))
    assert len(sample_pet.tasks) == before + 1

def test_remove_task(sample_pet):
    """Removing a task by title should decrease count and return True."""
    before = len(sample_pet.tasks)
    result = sample_pet.remove_task("Medication")
    assert result is True
    assert len(sample_pet.tasks) == before - 1

def test_remove_nonexistent_task(sample_pet):
    """Removing a task that does not exist should return False."""
    result = sample_pet.remove_task("Nonexistent task")
    assert result is False

def test_get_pending_tasks(sample_pet):
    """get_pending_tasks should exclude completed tasks."""
    sample_pet.tasks[0].completed = True
    pending = sample_pet.get_pending_tasks()
    assert all(not t.completed for t in pending)
    assert len(pending) == len(sample_pet.tasks) - 1


# ── Sorting tests ─────────────────────────────────────────────────────────────

def test_sort_by_time_is_chronological(scheduler):
    """sort_by_time should return tasks in HH:MM order."""
    sorted_pairs = scheduler.sort_by_time()
    times = [task.time for _, task in sorted_pairs]
    assert times == sorted(times)

def test_sort_by_priority_order(scheduler):
    """sort_by_priority should put high-priority tasks first."""
    sorted_pairs = scheduler.sort_by_priority()
    priorities = [task.priority for _, task in sorted_pairs]
    order = {"high": 0, "medium": 1, "low": 2}
    ranks = [order[p] for p in priorities]
    assert ranks == sorted(ranks)


# ── Filtering tests ───────────────────────────────────────────────────────────

def test_filter_by_pet_returns_correct_pet(sample_owner):
    """filter_by_pet should only return tasks for the named pet."""
    luna = Pet(name="Luna", species="cat")
    luna.add_task(Task(title="Feed Luna", duration_minutes=5, time="07:00"))
    sample_owner.add_pet(luna)
    s = Scheduler(sample_owner)
    results = s.filter_by_pet("Luna")
    assert all(pet.name == "Luna" for pet, _ in results)

def test_filter_pending_excludes_completed(scheduler, sample_pet):
    """filter_pending should not include completed tasks."""
    sample_pet.tasks[0].completed = True
    pending = scheduler.filter_pending()
    assert all(not t.completed for _, t in pending)


# ── Conflict detection ────────────────────────────────────────────────────────

def test_no_conflict_different_times(scheduler):
    """Tasks at different times should produce no conflicts."""
    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) == 0

def test_conflict_same_time_same_pet():
    """Two tasks at identical times for the same pet should trigger a warning."""
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task(title="Walk",      duration_minutes=20, time="08:00"))
    pet.add_task(Task(title="Breakfast", duration_minutes=5,  time="08:00"))
    owner = Owner(name="Alex")
    owner.add_pet(pet)
    s = Scheduler(owner)
    conflicts = s.detect_conflicts()
    assert len(conflicts) == 1
    assert "Rex" in conflicts[0]

def test_no_conflict_same_time_different_pets():
    """Two pets with tasks at the same time should NOT conflict with each other."""
    pet1 = Pet(name="A", species="dog")
    pet2 = Pet(name="B", species="cat")
    pet1.add_task(Task(title="Walk",  duration_minutes=20, time="08:00"))
    pet2.add_task(Task(title="Feed",  duration_minutes=5,  time="08:00"))
    owner = Owner(name="Owner")
    owner.add_pet(pet1)
    owner.add_pet(pet2)
    s = Scheduler(owner)
    assert len(s.detect_conflicts()) == 0


# ── Schedule generation ───────────────────────────────────────────────────────

def test_schedule_respects_time_budget():
    """build_daily_schedule should not exceed the owner's available_minutes."""
    pet = Pet(name="Max", species="dog")
    for i in range(10):
        pet.add_task(Task(title=f"Task {i}", duration_minutes=20, time=f"{8+i:02d}:00"))
    owner = Owner(name="Busy", available_minutes=60)
    owner.add_pet(pet)
    s = Scheduler(owner)
    schedule = s.build_daily_schedule()
    total = sum(t.duration_minutes for _, t in schedule)
    assert total <= 60

def test_schedule_excludes_completed():
    """Completed tasks should not appear in the daily schedule."""
    pet = Pet(name="Pip", species="cat")
    done_task = Task(title="Done", duration_minutes=10, time="09:00", completed=True)
    todo_task = Task(title="Todo", duration_minutes=10, time="10:00")
    pet.add_task(done_task)
    pet.add_task(todo_task)
    owner = Owner(name="Owner", available_minutes=120)
    owner.add_pet(pet)
    s = Scheduler(owner)
    titles = [t.title for _, t in s.build_daily_schedule()]
    assert "Done" not in titles
    assert "Todo" in titles

def test_empty_pet_has_no_schedule():
    """An owner with a pet that has no tasks should return an empty schedule."""
    pet = Pet(name="Empty", species="dog")
    owner = Owner(name="Quiet", available_minutes=120)
    owner.add_pet(pet)
    s = Scheduler(owner)
    assert s.build_daily_schedule() == []