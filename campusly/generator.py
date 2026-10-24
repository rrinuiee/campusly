"""Deterministic timetable generator for one division and academic year.

Placement mirrors the seed builder's approach: each required subject hour is
spread across days, and every slot picks a qualified faculty member ranked by
same-department, then lightest weekly load, then id. Mandatory constraints
(division, faculty, and room clashes within the semester parity, plus
subject qualification unless an explicit assignment overrides it) are never
violated — hours that cannot be placed are reported as violations instead.

The division's own non-supervision slots are treated as replaceable: they do
not occupy faculty, rooms, or periods during generation, because publishing
the draft replaces them. Its supervision slots are preserved and stay busy.
"""

from __future__ import annotations

from .data import SchoolData, semester_parity
from .models import DAYS, PERIODS, SUPERVISION_SUBJECT, TimetableSlot


def generate(
    data: SchoolData,
    class_group: str,
    requirements: dict[str, int],
    assignments: dict[str, str] | None = None,
) -> tuple[list[TimetableSlot], list[str], list[str]]:
    """Generate a weekly timetable draft for `class_group`.

    `requirements` maps subject id -> required weekly hours; `assignments`
    optionally pins a faculty id per subject (overrides qualification).
    Returns (slots, violations, warnings): violations block publication,
    warnings are advisory.
    """
    assignments = assignments or {}
    cg = data.classes[class_group]
    parity = semester_parity(cg.semester)

    violations: list[str] = []
    warnings: list[str] = []
    for sid in requirements:
        if sid not in data.subjects:
            violations.append(f"unknown subject {sid!r} in requirements")
    if violations:
        return [], violations, warnings
    total = sum(requirements.values())
    capacity = len(DAYS) * len(PERIODS)
    if total > capacity:
        violations.append(
            f"required hours ({total}) exceed the {capacity}-period week"
        )
        return [], violations, warnings

    # Occupancy: every slot in the same parity except the division's own
    # replaceable (non-supervision) slots, which the draft will replace.
    replaceable = {
        s.key
        for s in data.timetable
        if s.class_group == class_group and s.subject != SUPERVISION_SUBJECT
    }
    division_busy = {
        (s.day, s.period)
        for s in data.timetable
        if s.class_group == class_group and s.subject == SUPERVISION_SUBJECT
    }
    busy_teacher: dict[tuple[str, int], set[str]] = {}
    busy_room: dict[tuple[str, int], set[str]] = {}
    load = {tid: 0 for tid in data.teachers}
    for s in data.timetable:
        if s.key in replaceable:
            continue
        sem = data.classes[s.class_group].semester
        if sem and sem not in parity:
            continue
        busy_teacher.setdefault((s.day, s.period), set()).add(s.teacher)
        busy_room.setdefault((s.day, s.period), set()).add(s.room)
        load[s.teacher] = load.get(s.teacher, 0) + 1

    home_room = next(
        (s.room for s in data.timetable if s.class_group == class_group), None
    )
    placed: dict[tuple[str, int], TimetableSlot] = {}
    per_day = {sid: {d: 0 for d in DAYS} for sid in requirements}

    def pick_teacher(subject: str, day: str, period: int) -> str | None:
        busy = busy_teacher.get((day, period), set())
        pin = assignments.get(subject)
        if pin:
            return pin if pin not in busy else None
        cands = [
            t for t in data.teachers.values()
            if subject in t.subjects and t.id not in busy
        ]
        cands.sort(
            key=lambda t: (t.department != cg.department, load.get(t.id, 0), t.id)
        )
        return cands[0].id if cands else None

    def teacher_at_both(subject: str, day: str, p1: int, p2: int) -> str | None:
        busy = (
            busy_teacher.get((day, p1), set()) | busy_teacher.get((day, p2), set())
        )
        pin = assignments.get(subject)
        if pin:
            return pin if pin not in busy else None
        cands = [
            t for t in data.teachers.values()
            if subject in t.subjects and t.id not in busy
        ]
        cands.sort(
            key=lambda t: (t.department != cg.department, load.get(t.id, 0), t.id)
        )
        return cands[0].id if cands else None

    def pick_room(subject: str, day: str, period: int) -> str | None:
        occupied = busy_room.get((day, period), set())
        kind = data.subjects[subject].room_kind
        if kind:
            return next(
                (
                    r.id
                    for r in sorted(data.rooms.values(), key=lambda r: r.id)
                    if r.kind == kind and r.id not in occupied
                ),
                None,
            )
        if home_room and home_room not in occupied:
            return home_room
        free = sorted(r for r in data.rooms if r not in occupied)
        return next(
            (r for r in free if data.rooms[r].kind == "classroom"),
            free[0] if free else None,
        )

    def room_at_both(subject: str, day: str, p1: int, p2: int) -> str | None:
        occupied = (
            busy_room.get((day, p1), set()) | busy_room.get((day, p2), set())
        )
        kind = data.subjects[subject].room_kind
        free = [
            r.id
            for r in sorted(data.rooms.values(), key=lambda r: r.id)
            if r.id not in occupied and (not kind or r.kind == kind)
        ]
        if kind:
            return free[0] if free else None
        if home_room and home_room not in occupied:
            return home_room
        return next(
            (r for r in free if data.rooms[r].kind == "classroom"),
            free[0] if free else None,
        )

    def commit(subject: str, day: str, period: int, teacher: str, room: str) -> None:
        placed[(day, period)] = TimetableSlot(
            day, period, class_group, subject, teacher, room
        )
        busy_teacher.setdefault((day, period), set()).add(teacher)
        busy_room.setdefault((day, period), set()).add(room)
        load[teacher] = load.get(teacher, 0) + 1
        per_day[subject][day] += 1

    def day_order(subject: str) -> list[str]:
        return sorted(DAYS, key=lambda d: (per_day[subject][d], DAYS.index(d)))

    def place_single(subject: str) -> str | None:
        """Place one hour of `subject`; return a failure reason or None."""
        saw_slot = saw_room = False
        for day in day_order(subject):
            for period in PERIODS:
                if (day, period) in division_busy or (day, period) in placed:
                    continue
                saw_slot = True
                teacher = pick_teacher(subject, day, period)
                if teacher is None:
                    continue
                room = pick_room(subject, day, period)
                if room is None:
                    saw_room = True
                    continue
                commit(subject, day, period, teacher, room)
                return None
        if not saw_slot:
            return "division has no free period left"
        if saw_room:
            kind = data.subjects[subject].room_kind or "teaching"
            return f"no free {kind} room in any free period"
        if subject in assignments:
            return f"assigned faculty {assignments[subject]} is not free in any free period"
        return "no qualified faculty free in any free period"

    def place_pair(subject: str) -> bool:
        """Place two consecutive same-day periods of `subject`."""
        for day in day_order(subject):
            for period in PERIODS[:-1]:
                keys = ((day, period), (day, period + 1))
                if any(k in division_busy or k in placed for k in keys):
                    continue
                teacher = teacher_at_both(subject, day, period, period + 1)
                if teacher is None:
                    continue
                room = room_at_both(subject, day, period, period + 1)
                if room is None:
                    continue
                commit(subject, day, period, teacher, room)
                commit(subject, day, period + 1, teacher, room)
                return True
        return False

    # Hardest-first: room-constrained subjects, then most hours, then id.
    order = sorted(
        requirements,
        key=lambda s: (not data.subjects[s].room_kind, -requirements[s], s),
    )
    remaining = dict(requirements)

    # Lab-style subjects first take consecutive same-day pairs where possible.
    for sid in order:
        if not data.subjects[sid].room_kind:
            continue
        while remaining[sid] >= 2 and place_pair(sid):
            remaining[sid] -= 2
        if remaining[sid] >= 2:
            warnings.append(f"lab-non-consecutive: {sid}")

    for sid in order:
        while remaining[sid] > 0:
            reason = place_single(sid)
            if reason is not None:
                violations.append(f"unallocated {sid} x{remaining[sid]}: {reason}")
                break
            remaining[sid] -= 1

    # Advisory flags on the finished draft.
    for slot in placed.values():
        t = data.teachers[slot.teacher]
        if t.department != cg.department:
            warnings.append(f"cross-department: {slot.teacher} teaches {slot.subject}")
        if slot.subject in assignments and slot.subject not in t.subjects:
            warnings.append(f"non-subject-match: {slot.teacher} assigned {slot.subject}")

    slots = sorted(
        placed.values(), key=lambda s: (DAYS.index(s.day), s.period)
    )
    return slots, violations, sorted(set(warnings))
