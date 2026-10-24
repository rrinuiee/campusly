"""Fictional seed dataset: Greenfield High.

Generates a consistent Mon-Fri, 6-period timetable. Every slot references
existing teacher/room/class/subject ids. Deterministic: same output every run.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .models import (
    DAYS,
    PERIODS,
    ClassGroup,
    Room,
    Subject,
    Teacher,
    TimetableSlot,
)


@dataclass
class SchoolData:
    subjects: dict[str, Subject]
    teachers: dict[str, Teacher]
    rooms: dict[str, Room]
    classes: dict[str, ClassGroup]
    timetable: list[TimetableSlot]

    def slots_on(self, day: str) -> list[TimetableSlot]:
        return [s for s in self.timetable if s.day == day]

    def teacher_at(self, day: str, period: int) -> set[str]:
        """Teachers with a scheduled slot at this day/period."""
        return {s.teacher for s in self.timetable if s.day == day and s.period == period}

    def room_at(self, day: str, period: int) -> set[str]:
        return {s.room for s in self.timetable if s.day == day and s.period == period}


def _subjects() -> dict[str, Subject]:
    rows = [
        ("math", "Mathematics"),
        ("eng", "English"),
        ("phy", "Physics"),
        ("chem", "Chemistry"),
        ("bio", "Biology"),
        ("hist", "History"),
        ("cs", "Computer Science"),
        ("pe", "Physical Education"),
    ]
    return {i: Subject(i, n) for i, n in rows}


def _teachers() -> dict[str, Teacher]:
    rows = [
        ("T01", "Anitha Rao", {"math"}),
        ("T02", "Vikram Shah", {"math", "phy"}),
        ("T03", "Chen Wei", {"cs", "math"}),
        ("T04", "Sarah Lee", {"phy", "chem"}),
        ("T05", "Grace Liu", {"phy"}),
        ("T06", "David Okafor", {"chem", "bio"}),
        ("T07", "Priya Nair", {"bio"}),
        ("T08", "James Cole", {"eng"}),
        ("T09", "Maria Gomez", {"eng", "hist"}),
        ("T10", "Ahmed Khan", {"hist", "pe"}),
        ("T11", "Elena Petrova", {"cs"}),
        ("T12", "Ravi Menon", {"pe"}),
    ]
    return {i: Teacher(i, n, frozenset(s)) for i, n, s in rows}


def _rooms() -> dict[str, Room]:
    ids = ["R-101", "R-102", "R-103", "R-104", "R-105", "R-106", "LAB-SCI", "LAB-CS", "GYM"]
    return {i: Room(i, i) for i in ids}


def _classes() -> dict[str, ClassGroup]:
    rows = [("8-A", "Grade 8-A"), ("8-B", "Grade 8-B"), ("9-A", "Grade 9-A"),
            ("9-B", "Grade 9-B"), ("10-A", "Grade 10-A"), ("10-B", "Grade 10-B")]
    return {i: ClassGroup(i, n) for i, n in rows}


# Weekly subject mix per class (30 slots). Counts mirror a real school load.
_WEEK_MIX = (
    ["math"] * 5 + ["eng"] * 5 + ["phy"] * 4 + ["chem"] * 4
    + ["bio"] * 4 + ["hist"] * 4 + ["cs"] * 2 + ["pe"] * 2
)

_HOME_ROOMS = {cid: f"R-10{i + 1}" for i, cid in enumerate(_classes())}


def _match(candidates: dict[str, list[str]]) -> dict[str, str]:
    """Assign each class a distinct teacher via deterministic augmenting paths.

    `candidates` maps class id -> qualified teacher ids in preference order.
    Returns class id -> teacher id. Raises RuntimeError if infeasible.
    """
    owner: dict[str, str] = {}  # teacher -> class

    def augment(cid: str, seen: set[str]) -> bool:
        for tid in candidates[cid]:
            if tid in seen:
                continue
            seen.add(tid)
            if tid not in owner or augment(owner[tid], seen):
                owner[tid] = cid
                return True
        return False

    for cid in candidates:
        if not augment(cid, set()):
            raise RuntimeError(f"no feasible teacher assignment for {cid}")
    return {cid: tid for tid, cid in owner.items()}


def _build_timetable(
    teachers: dict[str, Teacher], classes: dict[str, ClassGroup]
) -> list[TimetableSlot]:
    """Assign subjects and teachers to every (class, day, period) slot.

    Each class starts the 30-slot subject mix at a different offset so any
    given period spreads classes across subjects. Within each period a
    bipartite match gives every class a distinct qualified teacher,
    preferring the lightest assigned load so far.
    """
    slots: list[TimetableSlot] = []
    assigned_load = {tid: 0 for tid in teachers}
    rotated = {
        cid: _WEEK_MIX[i * 5 :] + _WEEK_MIX[: i * 5]
        for i, cid in enumerate(classes)
    }

    for day_index, day in enumerate(DAYS):
        for period in PERIODS:
            idx = day_index * len(PERIODS) + (period - 1)
            candidates = {
                cid: [
                    t.id
                    for t in sorted(
                        teachers.values(),
                        key=lambda t: (assigned_load[t.id], t.id),
                    )
                    if rotated[cid][idx] in t.subjects
                ]
                for cid in classes
            }
            for cid, tid in _match(candidates).items():
                assigned_load[tid] += 1
                slots.append(
                    TimetableSlot(
                        day=day,
                        period=period,
                        class_group=cid,
                        subject=rotated[cid][idx],
                        teacher=tid,
                        room=_HOME_ROOMS[cid],
                    )
                )
    return slots


def day_name(iso_date: str) -> str | None:
    """Weekday name for an ISO date, or None on weekends (no school)."""
    d = dt.date.fromisoformat(iso_date)
    return DAYS[d.weekday()] if d.weekday() < len(DAYS) else None


def load_seed_data() -> SchoolData:
    subjects = _subjects()
    teachers = _teachers()
    rooms = _rooms()
    classes = _classes()
    timetable = _build_timetable(teachers, classes)
    return SchoolData(
        subjects=subjects,
        teachers=teachers,
        rooms=rooms,
        classes=classes,
        timetable=timetable,
    )
