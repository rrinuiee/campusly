"""Timetable-generation tests: constraints, lifecycle, determinism."""

import dataclasses
import datetime as dt

import pytest

from campusly.data import SchoolData, default_requirements
from campusly.generator import generate
from campusly.models import (
    DAYS,
    PERIODS,
    SUPERVISION_SUBJECT,
    TT_DRAFT,
    TT_PUBLISHED,
    ClassGroup,
    Department,
    Room,
    Subject,
    Teacher,
    TimetableSlot,
)
from campusly.store import Store

IN_SESSION = "2026-10-26"  # Monday inside the 2026 even-semester window


def make_data(teacher_rows, room_rows, class_rows, subject_rows, slots):
    return SchoolData(
        subjects={
            sid: Subject(sid, sid, dept, kind)
            for sid, dept, kind in subject_rows
        },
        teachers={
            tid: Teacher(tid, tid, frozenset(subs), dept)
            for tid, subs, dept in teacher_rows
        },
        rooms={rid: Room(rid, rid, kind) for rid, kind in room_rows},
        classes={
            cid: ClassGroup(cid, cid, dept, sem, sec)
            for cid, dept, sem, sec in class_rows
        },
        timetable=slots,
        departments={
            "bs": Department("bs", "Basic Science"),
            "cse": Department("cse", "CSE"),
            "ece": Department("ece", "ECE"),
        },
    )


def gen_data():
    """Minimal college: two CSE S2 divisions + an ECE S4 division (all even
    parity, in session together)."""
    return make_data(
        teacher_rows=[
            ("A1", {"cs", "lab"}, "cse"),
            ("A2", {"cs", "lab"}, "cse"),
            ("B1", {"ma"}, "bs"),
            ("B2", {"ma"}, "bs"),
            ("X1", {"cs", "lab", "ma"}, "ece"),
        ],
        room_rows=[("R1", "classroom"), ("R2", "classroom"), ("LAB1", "lab")],
        class_rows=[
            ("CSE-S2-A", "cse", "S2", "A"),
            ("CSE-S2-B", "cse", "S2", "B"),
            ("ECE-S4-A", "ece", "S4", "A"),
        ],
        subject_rows=[
            ("cs", "cse", ""),
            ("ma", "bs", ""),
            ("lab", "cse", "lab"),
        ],
        slots=[
            TimetableSlot("Monday", 1, "CSE-S2-B", "cs", "A1", "R1"),
            TimetableSlot("Monday", 2, "CSE-S2-B", "ma", "B1", "R1"),
            TimetableSlot("Monday", 1, "ECE-S4-A", "cs", "X1", "R2"),
        ],
    )


# ------------------------------------------------------------ generation core


def test_hours_allocated_exactly():
    data = gen_data()
    slots, violations, _ = generate(data, "CSE-S2-A", {"cs": 3, "ma": 2})
    assert violations == []
    assert len(slots) == 5
    assert sum(1 for s in slots if s.subject == "cs") == 3
    assert sum(1 for s in slots if s.subject == "ma") == 2


def test_no_division_double_booking():
    data = gen_data()
    slots, _, _ = generate(data, "CSE-S2-A", {"cs": 10, "ma": 5})
    keys = [(s.day, s.period) for s in slots]
    assert len(keys) == len(set(keys))


def test_faculty_and_room_not_double_booked_in_parity():
    data = gen_data()
    slots, violations, _ = generate(data, "CSE-S2-A", {"cs": 12, "ma": 6})
    for s in slots:
        existing_teachers = {
            t.teacher
            for t in data.timetable
            if t.day == s.day
            and t.period == s.period
            and t.class_group != "CSE-S2-A"
        }
        assert s.teacher not in existing_teachers
        existing_rooms = {
            t.room
            for t in data.timetable
            if t.day == s.day
            and t.period == s.period
            and t.class_group != "CSE-S2-A"
        }
        assert s.room not in existing_rooms
    # and never twice inside the draft itself
    seen = set()
    for s in slots:
        assert (s.day, s.period, s.teacher) not in seen
        assert (s.day, s.period, s.room) not in seen
        seen.add((s.day, s.period, s.teacher))
        seen.add((s.day, s.period, s.room))


def test_cross_department_faculty_conflict_respected():
    # X1 teaches ECE-S4-A on Monday P1 (same parity): never placed there.
    data = gen_data()
    slots, _, _ = generate(data, "CSE-S2-A", {"cs": 8, "ma": 4})
    assert not any(
        s.day == "Monday" and s.period == 1 and s.teacher == "X1" for s in slots
    )


def test_pinned_assignment_used():
    data = gen_data()
    slots, violations, _ = generate(
        data, "CSE-S2-A", {"cs": 3}, assignments={"cs": "X1"}
    )
    assert violations == []
    assert all(s.teacher == "X1" for s in slots)


def test_unqualified_pin_flagged():
    data = gen_data()
    slots, _, warnings = generate(
        data, "CSE-S2-A", {"ma": 1}, assignments={"ma": "A1"}
    )
    assert slots[0].teacher == "A1"
    assert any("non-subject-match" in w for w in warnings)


def test_infeasible_hours_over_week_reported():
    data = gen_data()
    slots, violations, _ = generate(data, "CSE-S2-A", {"cs": 26, "ma": 10})
    assert slots == []
    assert any("exceed" in v for v in violations)


def test_infeasible_over_week_reported():
    data = gen_data()
    slots, violations, _ = generate(data, "CSE-S2-A", {"cs": 1, "ma": 40})
    assert slots == []
    assert violations and any("exceed" in v for v in violations)


def test_pinned_busy_faculty_reports_violation():
    data = make_data(
        teacher_rows=[("A1", {"cs"}, "cse"), ("B1", {"ma"}, "bs")],
        room_rows=[("R1", "classroom"), ("R2", "classroom")],
        class_rows=[
            ("CSE-S2-A", "cse", "S2", "A"),
            ("CSE-S2-B", "cse", "S2", "B"),
        ],
        subject_rows=[("ma", "bs", "")],
        slots=[
            TimetableSlot(day, p, "CSE-S2-B", "ma", "B1", "R1")
            for day in DAYS
            for p in PERIODS
        ],
    )
    slots, violations, _ = generate(
        data, "CSE-S2-A", {"ma": 3}, assignments={"ma": "B1"}
    )
    assert slots == []
    assert violations and "not free" in violations[0]


def test_unallocated_when_faculty_pool_exhausted():
    # Only one teacher can ever teach 'cs', and they're booked every slot.
    data = make_data(
        teacher_rows=[("A1", {"cs"}, "cse")],
        room_rows=[("R1", "classroom")],
        class_rows=[
            ("CSE-S2-A", "cse", "S2", "A"),
            ("CSE-S2-B", "cse", "S2", "B"),
        ],
        subject_rows=[("cs", "cse", "")],
        slots=[
            TimetableSlot(day, p, "CSE-S2-B", "cs", "A1", "R1")
            for day in DAYS[:4]
            for p in PERIODS
        ],
    )
    slots, violations, _ = generate(data, "CSE-S2-A", {"cs": 30})
    placed = len(slots)
    assert placed + 24 == 30  # Friday is free for A1
    assert violations and all("unallocated cs" in v for v in violations)


def test_lab_subject_uses_lab_room_consecutively():
    data = gen_data()
    slots, violations, _ = generate(data, "CSE-S2-A", {"lab": 4})
    assert violations == []
    assert all(s.room == "LAB1" for s in slots)
    by_day = {}
    for s in slots:
        by_day.setdefault(s.day, []).append(s.period)
    assert any(sorted(ps) == list(range(ps[0], ps[0] + len(ps))) for ps in by_day.values())


def test_deterministic_repeat_runs():
    data = gen_data()
    req = {"cs": 8, "ma": 6, "lab": 2}
    first = generate(data, "CSE-S2-A", req)
    second = generate(data, "CSE-S2-A", dict(req))
    assert [dataclasses.asdict(s) for s in first[0]] == [
        dataclasses.asdict(s) for s in second[0]
    ]
    assert first[1:] == second[1:]


# ------------------------------------------------------------- store lifecycle


def test_default_requirements_matches_seed_mix():
    req = default_requirements("cse")
    assert req == {"cs": 8, "math": 5, "phy": 4, "chem": 4, "eng": 3, "pe": 2}


def test_generate_draft_isolated_and_replaces():
    store = Store(gen_data(), academic_year=2026)
    before = list(store.data.timetable)
    draft = store.generate_draft("CSE-S2-A", 2027, {"cs": 4, "ma": 2})
    assert draft.status == TT_DRAFT
    assert store.data.timetable == before  # nothing mutated
    again = store.generate_draft("CSE-S2-A", 2027, {"cs": 5})
    assert len(store.timetable_drafts()) == 1
    assert again.requirements == {"cs": 5}
    # a different academic year is a different draft
    store.generate_draft("CSE-S2-A", 2028, {"cs": 5})
    assert len(store.timetable_drafts()) == 2


def test_generate_draft_validates_inputs():
    store = Store(gen_data(), academic_year=2026)
    with pytest.raises(KeyError):
        store.generate_draft("NOPE", 2027, {"cs": 1})
    with pytest.raises(KeyError):
        store.generate_draft("CSE-S2-A", 2027, {"nope": 1})
    with pytest.raises(ValueError):
        store.generate_draft("CSE-S2-A", 2027, {"cs": -1})
    with pytest.raises(KeyError):
        store.generate_draft("CSE-S2-A", 2027, {"cs": 1}, {"cs": "NOPE"})


def test_publish_blocked_before_semester_window():
    store = Store(gen_data(), academic_year=2026)
    draft = store.generate_draft("CSE-S2-A", 2027, {"cs": 4})
    before = list(store.data.timetable)
    with pytest.raises(ValueError, match="not in session"):
        store.publish_draft(draft.id, IN_SESSION)
    assert store.data.timetable == before
    # in-session for 2027 S2 (Jul–Dec 2027) would be allowed
    store.publish_draft(draft.id, "2027-10-25")
    assert draft.status == TT_PUBLISHED


def test_publish_replaces_division_slots_preserving_supervision():
    store = Store(gen_data(), academic_year=2026)
    # Give the division existing slots + a supervision meeting.
    store.data.timetable.append(
        TimetableSlot("Tuesday", 3, "CSE-S2-A", "cs", "A1", "R1")
    )
    pg = store.add_project_group("P", "CSE-S2-A", "A2", "Wednesday", 5, "R1")
    draft = store.generate_draft("CSE-S2-A", 2026, {"cs": 4, "ma": 2})
    assert not draft.violations
    # supervision slot is never part of the generated draft
    assert not any(
        s.day == "Wednesday" and s.period == 5 for s in draft.slots
    )
    store.publish_draft(draft.id, IN_SESSION)
    slots = [s for s in store.data.timetable if s.class_group == "CSE-S2-A"]
    assert (pg.day, pg.period) in [(s.day, s.period) for s in slots]
    assert all(s.subject == SUPERVISION_SUBJECT or s in draft.slots for s in slots)


def test_publish_revalidation_blocks_new_conflict():
    store = Store(gen_data(), academic_year=2026)
    draft = store.generate_draft("CSE-S2-A", 2026, {"cs": 4})
    target = draft.slots[0]
    # Book the draft's teacher elsewhere at the same slot after generation.
    store.data.timetable.append(
        TimetableSlot(
            target.day, target.period, "CSE-S2-B", "cs", target.teacher, "R2"
        )
    )
    with pytest.raises(ValueError, match="already teaches"):
        store.publish_draft(draft.id, IN_SESSION)


def test_publish_blocked_by_open_workflows():
    store = Store(gen_data(), academic_year=2026)
    # Pending proposal for this division blocks publication.
    store.data.timetable.append(
        TimetableSlot("Monday", 3, "CSE-S2-A", "cs", "A1", "R1")
    )
    store.report_absence("A1", IN_SESSION)
    store.run_allocation(IN_SESSION)
    draft = store.generate_draft("CSE-S2-A", 2026, {"cs": 4})
    with pytest.raises(ValueError, match="proposal"):
        store.publish_draft(draft.id, IN_SESSION)


def test_publish_blocked_by_open_exchange():
    store = Store(gen_data(), academic_year=2026)
    store.data.timetable.append(
        TimetableSlot("Tuesday", 1, "CSE-S2-A", "cs", "A1", "R1")
    )
    x = store.propose_exchange(
        "A1", ("Tuesday", 1, "CSE-S2-A"), ("Monday", 2, "CSE-S2-B")
    )
    draft = store.generate_draft("CSE-S2-A", 2026, {"cs": 4})
    with pytest.raises(ValueError, match="exchange"):
        store.publish_draft(draft.id, IN_SESSION)


def test_publish_blocked_by_violations():
    store = Store(gen_data(), academic_year=2026)
    draft = store.generate_draft("CSE-S2-A", 2026, {"cs": 40})
    assert draft.violations
    with pytest.raises(ValueError, match="unresolved violation"):
        store.publish_draft(draft.id, IN_SESSION)


def test_discard_draft_leaves_no_trace():
    store = Store(gen_data(), academic_year=2026)
    before = list(store.data.timetable)
    draft = store.generate_draft("CSE-S2-A", 2027, {"cs": 4})
    store.discard_draft(draft.id)
    assert store.timetable_drafts() == []
    assert store.data.timetable == before
    with pytest.raises(KeyError):
        store.publish_draft(draft.id, IN_SESSION)


def test_semester_window_for_year_scoping():
    store = Store(gen_data(), academic_year=2026)
    store.override_semester_window("S2", dt.date(2026, 3, 1), dt.date(2026, 12, 31))
    assert store.semester_window_for(2026, "S2").start == dt.date(2026, 3, 1)
    # Other years ignore the override
    assert store.semester_window_for(2027, "S2").start == dt.date(2027, 7, 1)
    with pytest.raises(KeyError):
        store.semester_window_for(2027, "S9")


def test_generation_respects_parity_isolation():
    # A teacher busy in the ODD parity does not constrain even-parity slots.
    data = make_data(
        teacher_rows=[("A1", {"cs"}, "cse")],
        room_rows=[("R1", "classroom")],
        class_rows=[
            ("CSE-S2-A", "cse", "S2", "A"),
            ("CSE-S3-A", "cse", "S3", "A"),
        ],
        subject_rows=[("cs", "cse", "")],
        slots=[
            TimetableSlot(day, p, "CSE-S3-A", "cs", "A1", "R1")
            for day in DAYS
            for p in PERIODS
        ],
    )
    slots, violations, _ = generate(data, "CSE-S2-A", {"cs": 30})
    assert violations == []
    assert len(slots) == 30
    assert all(s.teacher == "A1" for s in slots)
