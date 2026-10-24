"""Engine tests: constraint enforcement, ranking, flagging, determinism."""

import dataclasses

from campusly.data import SchoolData
from campusly.engine import allocate
from campusly.models import (
    STATUS_PENDING,
    STATUS_UNCOVERED,
    ClassGroup,
    Room,
    Subject,
    Teacher,
    TimetableSlot,
)

DATE = "2026-10-26"  # Monday


def make_data(teacher_rows, room_ids, class_ids, slots):
    return SchoolData(
        subjects={
            "math": Subject("math", "Math"),
            "eng": Subject("eng", "English"),
        },
        teachers={
            tid: Teacher(tid, tid, frozenset(subs)) for tid, subs in teacher_rows
        },
        rooms={r: Room(r, r) for r in room_ids},
        classes={c: ClassGroup(c, c) for c in class_ids},
        timetable=slots,
    )


def run(data, slots, absent, workload=None, taken=None, taken_rooms=None):
    return allocate(
        data,
        slots,
        date=DATE,
        absent_teachers=absent,
        workload=workload if workload is not None else {},
        taken=taken if taken is not None else {},
        taken_rooms=taken_rooms,
    )


def test_subject_qualified_teacher_preferred():
    data = make_data(
        [("A", {"math"}), ("B", {"math"}), ("C", {"eng"}), ("D", {"eng"})],
        ["R1", "R2"],
        ["G1", "G2"],
        [
            TimetableSlot("Monday", 1, "G1", "math", "A", "R1"),
            TimetableSlot("Monday", 1, "G2", "eng", "D", "R2"),
        ],
    )
    slot = data.timetable[0]
    (p,) = run(data, [slot], absent={"A"})
    assert p.substitute_teacher == "B"
    assert p.status == STATUS_PENDING
    assert p.warnings == []


def test_workload_tiebreak_then_id():
    data = make_data(
        [("A", {"math"}), ("B", {"math"}), ("E", {"math"})],
        ["R1"],
        ["G1"],
        [TimetableSlot("Monday", 1, "G1", "math", "A", "R1")],
    )
    slot = data.timetable[0]
    (p,) = run(data, [slot], absent={"A"}, workload={"B": 3, "E": 1})
    assert p.substitute_teacher == "E"
    # Equal workload -> lowest id wins deterministically.
    (p2,) = run(data, [slot], absent={"A"}, workload={"B": 0, "E": 0})
    assert p2.substitute_teacher == "B"


def test_no_double_booking_same_period():
    data = make_data(
        [("A", {"math"}), ("F", {"math"}), ("B", {"math"}), ("C", {"eng"})],
        ["R1", "R2"],
        ["G1", "G2"],
        [
            TimetableSlot("Monday", 1, "G1", "math", "A", "R1"),
            TimetableSlot("Monday", 1, "G2", "math", "F", "R2"),
        ],
    )
    props = run(data, data.timetable, absent={"A", "F"})
    subs = {p.substitute_teacher for p in props}
    assert len(subs) == 2  # same teacher never booked twice in one period
    assert "B" in subs


def test_room_conflict_picks_alternative():
    data = make_data(
        [("A", {"math"}), ("F", {"math"}), ("B", {"math"}), ("C", {"math"})],
        ["R1", "R2", "R3"],
        ["G1", "G2"],
        [
            TimetableSlot("Monday", 1, "G1", "math", "A", "R1"),
            TimetableSlot("Monday", 1, "G2", "math", "F", "R1"),  # same room
        ],
    )
    props = run(data, data.timetable, absent={"A", "F"})
    rooms = {p.class_group: p.assigned_room for p in props}
    assert rooms["G1"] == "R1"
    assert rooms["G2"] == "R2"  # moved, not double-booked
    assert "room-changed" in props[1].warnings


def test_uncovered_when_no_teacher_free():
    data = make_data(
        [("A", {"math"}), ("B", {"math"})],
        ["R1", "R2"],
        ["G1", "G2"],
        [
            TimetableSlot("Monday", 1, "G1", "math", "A", "R1"),
            TimetableSlot("Monday", 1, "G2", "math", "B", "R2"),  # B busy
        ],
    )
    (p,) = run(data, [data.timetable[0]], absent={"A"})
    assert p.status == STATUS_UNCOVERED
    assert p.substitute_teacher is None
    assert "no-teacher-available" in p.warnings


def test_non_subject_fallback_flagged():
    data = make_data(
        [("A", {"math"}), ("C", {"eng"}), ("D", {"eng"})],
        ["R1", "R2"],
        ["G1", "G2"],
        [
            TimetableSlot("Monday", 1, "G1", "math", "A", "R1"),
            TimetableSlot("Monday", 1, "G2", "eng", "D", "R2"),
        ],
    )
    (p,) = run(data, [data.timetable[0]], absent={"A"})
    assert p.substitute_teacher == "C"  # only free teacher
    assert "non-subject-match" in p.warnings


def _college_data(teacher_rows, class_rows, slots):
    """Fixture with department-scoped teachers and divisions (semester S2)."""
    return SchoolData(
        subjects={
            "cs": Subject("cs", "CS", "cse"),
            "ec": Subject("ec", "EC", "ece"),
        },
        teachers={
            tid: Teacher(tid, tid, frozenset(subs), dept)
            for tid, subs, dept in teacher_rows
        },
        rooms={r: Room(r, r) for r in ("R1", "R2")},
        classes={
            cid: ClassGroup(cid, cid, dept, "S2", "A")
            for cid, dept in class_rows
        },
        timetable=slots,
    )


def test_same_department_substitute_preferred():
    # Both qualified and free: same-department wins over lower id.
    data = _college_data(
        [("A", {"cs"}, "cse"), ("Z", {"cs"}, "cse"), ("A0", {"cs"}, "ece")],
        [("G1", "cse")],
        [TimetableSlot("Monday", 1, "G1", "cs", "A", "R1")],
    )
    (p,) = run(data, data.timetable, absent={"A"})
    assert p.substitute_teacher == "Z"
    assert "cross-department" not in p.warnings


def test_cross_department_substitute_flagged():
    data = _college_data(
        [("A", {"cs"}, "cse"), ("A0", {"cs"}, "ece")],
        [("G1", "cse")],
        [TimetableSlot("Monday", 1, "G1", "cs", "A", "R1")],
    )
    (p,) = run(data, data.timetable, absent={"A"})
    assert p.substitute_teacher == "A0"
    assert "cross-department" in p.warnings


def test_busy_in_other_department_excluded():
    # F teaches an ECE division at Monday P1 — cannot cover the CSE slot.
    data = _college_data(
        [("A", {"cs"}, "cse"), ("B", {"cs"}, "cse"), ("F", {"cs"}, "ece")],
        [("G1", "cse"), ("G2", "ece")],
        [
            TimetableSlot("Monday", 1, "G1", "cs", "A", "R1"),
            TimetableSlot("Monday", 1, "G2", "ec", "F", "R2"),
        ],
    )
    (p,) = run(data, [data.timetable[0]], absent={"A"})
    assert p.substitute_teacher == "B"


def test_deterministic_repeat_runs():
    data = make_data(
        [("A", {"math"}), ("B", {"math"}), ("C", {"eng"}), ("E", {"math"})],
        ["R1", "R2"],
        ["G1", "G2"],
        [
            TimetableSlot("Monday", 1, "G1", "math", "A", "R1"),
            TimetableSlot("Monday", 2, "G1", "eng", "C", "R1"),
            TimetableSlot("Monday", 1, "G2", "eng", "C", "R2"),
        ],
    )
    slots = data.timetable[:2]
    first = run(data, slots, absent={"A", "C"})
    second = run(data, slots, absent={"A", "C"})
    assert [dataclasses.asdict(p) for p in first] == [
        dataclasses.asdict(p) for p in second
    ]
