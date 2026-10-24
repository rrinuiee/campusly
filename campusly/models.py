"""Domain model for Campusly.

Kept deliberately generic (class groups, subjects, rooms) so the same model
serves a school or a college timetable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = [1, 2, 3, 4, 5, 6]

PERIOD_TIMES = {
    1: "08:00–08:50",
    2: "09:00–09:50",
    3: "10:00–10:50",
    4: "11:10–12:00",
    5: "13:00–13:50",
    6: "14:00–14:50",
}

# Proposal lifecycle. A rejected proposal returns to "uncovered" so the
# period stays flagged for manual follow-up.
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_UNCOVERED = "uncovered"


@dataclass(frozen=True)
class Subject:
    id: str
    name: str


@dataclass(frozen=True)
class Teacher:
    id: str
    name: str
    subjects: frozenset[str]


@dataclass(frozen=True)
class Room:
    id: str
    name: str


@dataclass(frozen=True)
class ClassGroup:
    id: str
    name: str


@dataclass(frozen=True)
class TimetableSlot:
    """One scheduled teaching period in the weekly base timetable."""

    day: str
    period: int
    class_group: str
    subject: str
    teacher: str
    room: str

    @property
    def key(self) -> tuple[str, int, str]:
        return (self.day, self.period, self.class_group)


@dataclass(frozen=True)
class Absence:
    teacher: str
    date: str  # ISO date, e.g. "2026-10-26"


@dataclass
class Proposal:
    """A proposed (or flagged) coverage plan for one uncovered period."""

    id: str
    date: str
    day: str
    period: int
    class_group: str
    subject: str
    absent_teacher: str
    room: str
    substitute_teacher: str | None = None
    assigned_room: str | None = None
    warnings: list[str] = field(default_factory=list)
    status: str = STATUS_PENDING
