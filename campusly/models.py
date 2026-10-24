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

# Exchange lifecycle: proposed -> accepted -> approved, with declined,
# cancelled, and rejected as terminal states.
EXCHANGE_PROPOSED = "proposed"
EXCHANGE_ACCEPTED = "accepted"
EXCHANGE_APPROVED = "approved"
EXCHANGE_DECLINED = "declined"
EXCHANGE_CANCELLED = "cancelled"
EXCHANGE_REJECTED = "rejected"

# Subject marker for project-supervision timetable slots.
SUPERVISION_SUBJECT = "supervision"

# Generated-timetable lifecycle: draft -> published | discarded.
TT_DRAFT = "draft"
TT_PUBLISHED = "published"
TT_DISCARDED = "discarded"


@dataclass(frozen=True)
class Subject:
    id: str
    name: str
    department: str = ""
    room_kind: str = ""  # e.g. "lab"/"gym"; "" means any teaching room


@dataclass(frozen=True)
class Department:
    id: str
    name: str


@dataclass(frozen=True)
class Teacher:
    id: str
    name: str
    subjects: frozenset[str]
    department: str = ""


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    kind: str = "classroom"


@dataclass(frozen=True)
class ClassGroup:
    """A division: a student group scoped by department, semester, section."""

    id: str
    name: str
    department: str = ""
    semester: str = ""
    section: str = ""

    @property
    def division(self) -> str:
        """Scoped label like 'CSE-S3-A'; falls back to id for unscoped groups."""
        if self.department or self.semester or self.section:
            return f"{self.department}-{self.semester}-{self.section}"
        return self.id

    @property
    def first_year(self) -> bool:
        """True for first-year divisions (semesters S1 and S2)."""
        return self.semester in {"S1", "S2"}


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


@dataclass
class Exchange:
    """A proposed swap of two scheduled teaching periods between faculty."""

    id: str
    proposer: str  # Faculty A
    counterparty: str  # Faculty B
    proposer_slot: tuple[str, int, str]  # (day, period, class_group)
    counterparty_slot: tuple[str, int, str]
    status: str = EXCHANGE_PROPOSED
    warnings: list[str] = field(default_factory=list)


@dataclass
class GeneratedTimetable:
    """A generated draft timetable for one division and academic year.

    `violations` are unsatisfied mandatory constraints (unallocated hours,
    clashes) that block publication; `warnings` are unmet preferences and
    flags (non-consecutive labs, cross-department faculty) that do not.
    """

    id: str
    academic_year: int
    class_group: str
    requirements: dict[str, int]
    assignments: dict[str, str]
    slots: list[TimetableSlot]
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = TT_DRAFT


@dataclass
class ProjectGroup:
    """A student project group within a division, with a faculty supervisor."""

    id: str
    title: str
    class_group: str  # division id
    supervisor: str  # faculty id
    day: str = ""
    period: int = 0
    room: str = ""
