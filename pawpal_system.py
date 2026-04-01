"""
pawpal_system.py - PawPal+ backend logic layer.
Classes: Task, Pet, Owner, Scheduler
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """Represents a single pet care activity."""

    title: str
    duration_minutes: int
    time: str                          # "HH:MM" 24-hour format
    priority: str = "medium"           # "low" | "medium" | "high"
    frequency: str = "once"            # "once" | "daily" | "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    notes: str = ""

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task complete and return the next occurrence if recurring."""
        self.completed = True
        if self.frequency == "daily":
            return Task(
                title=self.title,
                duration_minutes=self.duration_minutes,
                time=self.time,
                priority=self.priority,
                frequency=self.frequency,
                due_date=self.due_date + timedelta(days=1),
                notes=self.notes,
            )
        if self.frequency == "weekly":
            return Task(
                title=self.title,
                duration_minutes=self.duration_minutes,
                time=self.time,
                priority=self.priority,
                frequency=self.frequency,
                due_date=self.due_date + timedelta(weeks=1),
                notes=self.notes,
            )
        return None  # "once" tasks produce no successor

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        return (
            f"[{status}] {self.time} | {self.title} "
            f"({self.duration_minutes} min, {self.priority} priority)"
        )


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Stores pet details and a list of associated tasks."""

    name: str
    species: str                       # "dog" | "cat" | "other"
    breed: str = ""
    age_years: float = 0.0
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """Remove the first task matching the given title. Returns True if found."""
        for i, t in enumerate(self.tasks):
            if t.title.lower() == title.lower():
                self.tasks.pop(i)
                return True
        return False

    def get_pending_tasks(self) -> List[Task]:
        """Return tasks that have not been completed."""
        return [t for t in self.tasks if not t.completed]

    def __str__(self) -> str:
        return f"{self.name} ({self.species}), {len(self.tasks)} task(s)"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    """Manages one or more pets and provides aggregated access to their tasks."""

    def __init__(self, name: str, available_minutes: int = 120):
        self.name = name
        self.available_minutes = available_minutes   # daily time budget
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> bool:
        """Remove a pet by name. Returns True if found."""
        for i, p in enumerate(self.pets):
            if p.name.lower() == name.lower():
                self.pets.pop(i)
                return True
        return False

    def get_all_tasks(self) -> List[tuple[Pet, Task]]:
        """Return (pet, task) pairs for every task across all pets."""
        pairs = []
        for pet in self.pets:
            for task in pet.tasks:
                pairs.append((pet, task))
        return pairs

    def __str__(self) -> str:
        return f"Owner: {self.name} | Pets: {len(self.pets)} | Budget: {self.available_minutes} min/day"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Brain of PawPal+. Sorts, filters, and validates the daily schedule."""

    def __init__(self, owner: Owner):
        self.owner = owner

    # --- helpers ------------------------------------------------------------

    def _all_pairs(self) -> List[tuple[Pet, Task]]:
        """Return every (pet, task) pair from the owner."""
        return self.owner.get_all_tasks()

    # --- sorting ------------------------------------------------------------

    def sort_by_time(self, pairs: Optional[List[tuple[Pet, Task]]] = None) -> List[tuple[Pet, Task]]:
        """Sort (pet, task) pairs chronologically by task time."""
        source = pairs if pairs is not None else self._all_pairs()
        return sorted(source, key=lambda pt: pt[1].time)

    def sort_by_priority(self, pairs: Optional[List[tuple[Pet, Task]]] = None) -> List[tuple[Pet, Task]]:
        """Sort (pet, task) pairs by priority (high → medium → low)."""
        order = {"high": 0, "medium": 1, "low": 2}
        source = pairs if pairs is not None else self._all_pairs()
        return sorted(source, key=lambda pt: order.get(pt[1].priority, 1))

    # --- filtering ----------------------------------------------------------

    def filter_by_pet(self, pet_name: str) -> List[tuple[Pet, Task]]:
        """Return tasks belonging to the named pet."""
        return [(p, t) for p, t in self._all_pairs() if p.name.lower() == pet_name.lower()]

    def filter_pending(self) -> List[tuple[Pet, Task]]:
        """Return only incomplete tasks."""
        return [(p, t) for p, t in self._all_pairs() if not t.completed]

    def filter_completed(self) -> List[tuple[Pet, Task]]:
        """Return only completed tasks."""
        return [(p, t) for p, t in self._all_pairs() if t.completed]

    # --- conflict detection -------------------------------------------------

    def detect_conflicts(self) -> List[str]:
        """
        Check for tasks scheduled at the exact same time for the same pet.
        Returns a list of human-readable warning strings (empty if no conflicts).
        """
        warnings = []
        for pet in self.owner.pets:
            seen: dict[str, str] = {}     # time -> task title
            for task in pet.tasks:
                if task.completed:
                    continue
                if task.time in seen:
                    warnings.append(
                        f"⚠️  Conflict for {pet.name}: '{seen[task.time]}' and "
                        f"'{task.title}' both scheduled at {task.time}."
                    )
                else:
                    seen[task.time] = task.title
        return warnings

    # --- recurring task completion -------------------------------------------

    def complete_task(self, pet: Pet, task: Task) -> Optional[Task]:
        """
        Mark a task complete on the given pet. If recurring, add the next
        occurrence back to the pet and return it; otherwise return None.
        """
        successor = task.mark_complete()
        if successor:
            pet.add_task(successor)
        return successor

    # --- schedule generation ------------------------------------------------

    def build_daily_schedule(self) -> List[tuple[Pet, Task]]:
        """
        Build today's schedule: pending tasks sorted by time,
        respecting the owner's daily time budget.
        """
        pending = self.filter_pending()
        sorted_pairs = self.sort_by_time(pending)

        schedule: List[tuple[Pet, Task]] = []
        minutes_used = 0
        for pet, task in sorted_pairs:
            if minutes_used + task.duration_minutes <= self.owner.available_minutes:
                schedule.append((pet, task))
                minutes_used += task.duration_minutes
        return schedule

    # --- display ------------------------------------------------------------

    def print_schedule(self) -> None:
        """Print today's schedule to the terminal in a readable format."""
        schedule = self.build_daily_schedule()
        conflicts = self.detect_conflicts()

        print(f"\n{'='*50}")
        print(f"  📅  PawPal+ Daily Schedule for {self.owner.name}")
        print(f"{'='*50}")

        if not schedule:
            print("  No tasks scheduled for today.")
        else:
            for pet, task in schedule:
                print(f"  {task.time}  [{pet.name}]  {task.title}")
                print(f"          {task.duration_minutes} min | {task.priority} priority | {task.frequency}")
                if task.notes:
                    print(f"          Note: {task.notes}")

        total = sum(t.duration_minutes for _, t in schedule)
        print(f"\n  Total time: {total} min  (budget: {self.owner.available_minutes} min)")

        if conflicts:
            print("\n  --- Conflicts Detected ---")
            for w in conflicts:
                print(f"  {w}")
        print(f"{'='*50}\n")