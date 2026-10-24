"""Fictional seed dataset: Greenfield College.

Generates a consistent Mon-Fri, 6-period timetable across departments and
semesters. Every slot references existing teacher/room/division/subject ids.
Deterministic: same output every run.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .models import (
    DAYS,
    PERIODS,
    ClassGroup,
    Department,
    Room,
    Subject,
    Teacher,
    TimetableSlot,
)

SEMESTERS = [f"S{i}" for i in range(1, 9)]
ODD_SEMESTERS = ("S1", "S3", "S5", "S7")
EVEN_SEMESTERS = ("S2", "S4", "S6", "S8")


@dataclass
class SemesterWindow:
    """Date range during which a semester's divisions are active."""

    semester: str
    start: dt.date
    end: dt.date


def default_semester_windows(year: int) -> dict[str, SemesterWindow]:
    """Odd semesters run Jan 1–Jun 30; even semesters Jul 1–Dec 31."""
    windows = {}
    for s in SEMESTERS:
        if s in ODD_SEMESTERS:
            windows[s] = SemesterWindow(s, dt.date(year, 1, 1), dt.date(year, 6, 30))
        else:
            windows[s] = SemesterWindow(s, dt.date(year, 7, 1), dt.date(year, 12, 31))
    return windows


def active_semesters(
    iso_date: str, windows: dict[str, SemesterWindow] | None = None
) -> list[str]:
    """Semesters whose window contains the date, in S1..S8 order.

    Defaults to the standard windows for the date's year; pass `windows`
    to honor admin overrides.
    """
    d = dt.date.fromisoformat(iso_date)
    if windows is None:
        windows = default_semester_windows(d.year)
    return [
        s for s in SEMESTERS
        if s in windows and windows[s].start <= d <= windows[s].end
    ]


@dataclass
class SchoolData:
    subjects: dict[str, Subject]
    teachers: dict[str, Teacher]
    rooms: dict[str, Room]
    classes: dict[str, ClassGroup]
    timetable: list[TimetableSlot]
    departments: dict[str, Department] = field(default_factory=dict)

    def slots_on(self, day: str) -> list[TimetableSlot]:
        return [s for s in self.timetable if s.day == day]

    def teacher_at(
        self,
        day: str,
        period: int,
        semesters: tuple[str, ...] | None = None,
        overrides: dict[tuple[str, int, str], str] | None = None,
    ) -> set[str]:
        """Teachers with a scheduled slot at this day/period.

        Pass `semesters` to scope to one semester parity — divisions in
        the other parity are not in session at the same time. Pass
        `overrides` (slot key -> teacher) to account for applied
        exchanges.
        """
        ov = overrides or {}
        return {
            ov.get(s.key, s.teacher)
            for s in self.timetable
            if s.day == day
            and s.period == period
            and (
                semesters is None
                or not self.classes[s.class_group].semester
                or self.classes[s.class_group].semester in semesters
            )
        }

    def room_at(
        self, day: str, period: int, semesters: tuple[str, ...] | None = None
    ) -> set[str]:
        return {
            s.room
            for s in self.timetable
            if s.day == day
            and s.period == period
            and (
                semesters is None
                or not self.classes[s.class_group].semester
                or self.classes[s.class_group].semester in semesters
            )
        }

    def slot_at(
        self, day: str, period: int, class_group: str
    ) -> TimetableSlot | None:
        """The division's slot at this day/period, if any."""
        for s in self.timetable:
            if (
                s.day == day
                and s.period == period
                and s.class_group == class_group
            ):
                return s
        return None


def _departments() -> dict[str, Department]:
    rows = [
        ("bs", "Basic Science"),
        ("cse", "Computer Science & Engineering"),
        ("ece", "Electronics & Communication"),
        ("eee", "Electrical & Electronics"),
        ("me", "Mechanical Engineering"),
        ("ce", "Civil Engineering"),
    ]
    return {i: Department(i, n) for i, n in rows}


def _subjects() -> dict[str, Subject]:
    rows = [
        ("math", "Mathematics", "bs"),
        ("phy", "Physics", "bs"),
        ("chem", "Chemistry", "bs"),
        ("eng", "Communication Skills", "bs"),
        ("pe", "Physical Education", "bs"),
        ("cs", "Computer Science", "cse"),
        ("ec", "Electronics", "ece"),
        ("ee", "Electrical Engineering", "eee"),
        ("mech", "Mechanics", "me"),
        ("civil", "Civil Engineering", "ce"),
    ]
    return {i: Subject(i, n, d) for i, n, d in rows}


def _teachers() -> dict[str, Teacher]:
    rows = [
        # Basic Science — service faculty, concentrated on first-year teaching
        ("B01", "Anitha Rao", {"math", "phy"}, "bs"),
        ("B02", "Vikram Shah", {"math"}, "bs"),
        ("B03", "Meera Iyer", {"phy", "chem"}, "bs"),
        ("B04", "Sarah Lee", {"chem", "eng"}, "bs"),
        ("B05", "James Cole", {"eng", "pe"}, "bs"),
        # Computer Science & Engineering
        ("C01", "Chen Wei", {"cs"}, "cse"),
        ("C02", "Priya Nair", {"cs", "math"}, "cse"),
        ("C03", "Elena Petrova", {"cs"}, "cse"),
        ("C04", "Arjun Das", {"cs", "phy"}, "cse"),
        ("C05", "Nina Kapoor", {"cs", "chem"}, "cse"),
        ("C06", "Rahul Verma", {"cs", "math"}, "cse"),
        ("C07", "Kavya Reddy", {"cs", "eng"}, "cse"),
        ("C08", "Sanjay Mehta", {"cs"}, "cse"),
        ("C09", "Lucia Fernandes", {"cs", "pe"}, "cse"),
        ("C10", "Pavel Novak", {"cs", "chem"}, "cse"),
        # Electronics & Communication
        ("E01", "Grace Liu", {"ec"}, "ece"),
        ("E02", "Ahmed Khan", {"ec", "eng"}, "ece"),
        ("E03", "Sofia Martins", {"ec", "math"}, "ece"),
        ("E04", "Tom Becker", {"ec", "phy"}, "ece"),
        ("E05", "Lina Torres", {"ec", "chem"}, "ece"),
        ("E06", "Hiro Tanaka", {"ec"}, "ece"),
        ("E07", "Divya Pillai", {"ec", "math"}, "ece"),
        ("E08", "Marcus Webb", {"ec", "pe"}, "ece"),
        ("E09", "Anna Schmidt", {"ec"}, "ece"),
        ("E10", "Rajesh Kulkarni", {"ec", "phy"}, "ece"),
        # Electrical & Electronics
        ("X01", "Omar Farouk", {"ee"}, "eee"),
        ("X02", "Igor Volkov", {"ee", "math"}, "eee"),
        ("X03", "Fatima Noor", {"ee", "chem"}, "eee"),
        ("X04", "Carlos Reyes", {"ee"}, "eee"),
        ("X05", "Deepa Sharma", {"ee", "eng"}, "eee"),
        ("X06", "Kenji Sato", {"ee", "phy"}, "eee"),
        ("X07", "Ingrid Beyer", {"ee"}, "eee"),
        ("X08", "Manoj Tiwari", {"ee", "math"}, "eee"),
        ("X09", "Rosa Alvarez", {"ee", "pe"}, "eee"),
        ("X10", "Viktor Petrov", {"ee", "phy"}, "eee"),
        # Mechanical Engineering
        ("M01", "Lena Fischer", {"mech"}, "me"),
        ("M02", "Yusuf Ali", {"mech", "eng"}, "me"),
        ("M03", "Kiran Bose", {"mech"}, "me"),
        ("M04", "Pedro Santos", {"mech", "pe"}, "me"),
        ("M05", "Wei Zhang", {"mech", "phy"}, "me"),
        ("M06", "Aisha Bello", {"mech", "math"}, "me"),
        ("M07", "Tomas Silva", {"mech", "chem"}, "me"),
        ("M08", "Greta Muller", {"mech"}, "me"),
        ("M09", "Harish Joshi", {"mech", "math"}, "me"),
        ("M10", "Nadia Hassan", {"mech", "chem"}, "me"),
        # Civil Engineering
        ("V01", "Bruno Costa", {"civil"}, "ce"),
        ("V02", "Mei Lin", {"civil", "math"}, "ce"),
        ("V03", "Oskar Lindqvist", {"civil", "phy"}, "ce"),
        ("V04", "Zara Ahmed", {"civil", "chem"}, "ce"),
        ("V05", "Ivan Petrenko", {"civil", "eng"}, "ce"),
        ("V06", "Leila Haddad", {"civil", "pe"}, "ce"),
        ("V07", "Suresh Patil", {"civil", "math"}, "ce"),
        ("V08", "Dana Kim", {"civil"}, "ce"),
        ("V09", "Felix Braun", {"civil", "phy"}, "ce"),
        ("V10", "Amara Osei", {"civil", "chem"}, "ce"),
    ]
    return {i: Teacher(i, n, frozenset(s), d) for i, n, s, d in rows}


def _rooms() -> dict[str, Room]:
    ids = [f"R-{101 + i}" for i in range(96)] + [
        "LAB-CS",
        "LAB-ECE",
        "LAB-EE",
        "LAB-ME",
        "LAB-CE",
        "LAB-SCI",
        "GYM",
    ]
    return {i: Room(i, i) for i in ids}


# Section letters per department per semester.
_SECTIONS = {"cse": "ABC", "ece": "ABC", "eee": "AB", "me": "AB", "ce": "AB"}


def _classes() -> dict[str, ClassGroup]:
    """Divisions: every section of every engineering department, S1–S8.

    Basic Science is a service department and has no divisions.
    """
    out = {}
    for dept, sections in _SECTIONS.items():
        for sem in SEMESTERS:
            for sec in sections:
                cid = f"{dept.upper()}-{sem}-{sec}"
                out[cid] = ClassGroup(
                    id=cid,
                    name=cid,
                    department=dept,
                    semester=sem,
                    section=sec,
                )
    return out


# Each engineering department's core subject.
_CORE_SUBJECT = {"cse": "cs", "ece": "ec", "eee": "ee", "me": "mech", "ce": "civil"}


# Marker for free (non-teaching) periods inside a weekly mix.
FREE_PERIOD = "free"


def _week_mix(dept: str) -> list[str]:
    """30-slot weekly mix: department core, service subjects, free periods."""
    return (
        [_CORE_SUBJECT[dept]] * 8 + ["math"] * 5 + ["phy"] * 4
        + ["chem"] * 4 + ["eng"] * 3 + ["pe"] * 2 + [FREE_PERIOD] * 4
    )


_HOME_ROOMS = {cid: f"R-{101 + i}" for i, cid in enumerate(_classes())}


def semester_parity(semester: str) -> tuple[str, ...]:
    """The parity group a semester belongs to (its in-session cohort).

    Unknown/empty semesters conservatively resolve to all semesters.
    """
    if semester in ODD_SEMESTERS:
        return ODD_SEMESTERS
    if semester in EVEN_SEMESTERS:
        return EVEN_SEMESTERS
    return tuple(SEMESTERS)


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
    """Assign subjects and faculty to every (division, day, period) slot.

    Timetables are built per semester parity (odd / even): only one parity
    is in session at a time, so faculty and rooms may appear in both
    parities' timetables at the same day/period without conflict. Within a
    parity, each division starts its department's 30-slot mix at a rotated
    offset so any given period spreads divisions across subjects, and a
    bipartite match gives every division a distinct qualified faculty
    member, preferring the lightest assigned load so far. First-year
    divisions prefer Basic Science faculty, making first-year
    cross-department teaching explicit.
    """
    slots: list[TimetableSlot] = []
    assigned_load = {tid: 0 for tid in teachers}

    for parity in (ODD_SEMESTERS, EVEN_SEMESTERS):
        parity_classes = {
            cid: c for cid, c in classes.items() if c.semester in parity
        }
        # Rotate each division's mix by a stride coprime with 30 so
        # same-subject demand stays within the qualified faculty pool.
        rotated = {
            cid: (mix := _week_mix(c.department))[(i * 7) % 30 :]
            + mix[: (i * 7) % 30]
            for i, (cid, c) in enumerate(parity_classes.items())
        }

        for day_index, day in enumerate(DAYS):
            for period in PERIODS:
                idx = day_index * len(PERIODS) + (period - 1)
                candidates = {
                    cid: [
                        t.id
                        for t in sorted(
                            teachers.values(),
                            key=lambda t, c=c: (
                                c.first_year and t.department != "bs",
                                assigned_load[t.id],
                                t.id,
                            ),
                        )
                        if rotated[cid][idx] in t.subjects
                    ]
                    for cid, c in parity_classes.items()
                    if rotated[cid][idx] != FREE_PERIOD
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
    departments = _departments()
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
        departments=departments,
    )
