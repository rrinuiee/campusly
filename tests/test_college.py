"""College model tests: department-scoped fields, new dataclasses, calendar."""

import datetime as dt

import pytest

from campusly.data import (
    EVEN_SEMESTERS,
    ODD_SEMESTERS,
    SEMESTERS,
    SemesterWindow,
    active_semesters,
    default_semester_windows,
    load_seed_data,
)
from campusly.store import Store
from campusly.models import (
    EXCHANGE_ACCEPTED,
    EXCHANGE_APPROVED,
    EXCHANGE_PROPOSED,
    SUPERVISION_SUBJECT,
    ClassGroup,
    Department,
    Exchange,
    ProjectGroup,
    Subject,
    Teacher,
)


def test_teacher_and_subject_department_default():
    t = Teacher("T1", "Ada", frozenset({"math"}))
    assert t.department == ""
    assert Teacher("T2", "Bob", frozenset(), department="CSE").department == "CSE"
    assert Subject("math", "Math").department == ""
    assert Subject("cs", "CS", department="CSE").department == "CSE"


def test_classgroup_division_label():
    legacy = ClassGroup("8-A", "Grade 8-A")
    assert legacy.division == "8-A"
    div = ClassGroup(
        "8-A", "Grade 8-A", department="CSE", semester="S3", section="A"
    )
    assert div.division == "CSE-S3-A"


def test_department_exchange_projectgroup_constructible():
    dept = Department("CSE", "Computer Science")
    assert dept.name == "Computer Science"
    ex = Exchange(
        id="X-1",
        proposer="T01",
        counterparty="T02",
        proposer_slot=("Monday", 4, "CSE-S3-A"),
        counterparty_slot=("Thursday", 2, "ECE-S4-B"),
    )
    assert ex.status == EXCHANGE_PROPOSED
    ex.status = EXCHANGE_ACCEPTED
    ex.status = EXCHANGE_APPROVED
    pg = ProjectGroup(
        id="PG-1", title="Smart Grid", class_group="ECE-S6-B", supervisor="T05",
        day="Friday", period=5, room="R-101",
    )
    assert pg.supervisor == "T05"
    assert SUPERVISION_SUBJECT == "supervision"


def test_default_semester_windows_shape():
    windows = default_semester_windows(2026)
    assert set(windows) == set(SEMESTERS)
    for s in ODD_SEMESTERS:
        assert windows[s].start == dt.date(2026, 1, 1)
        assert windows[s].end == dt.date(2026, 6, 30)
    for s in EVEN_SEMESTERS:
        assert windows[s].start == dt.date(2026, 7, 1)
        assert windows[s].end == dt.date(2026, 12, 31)


def test_active_semesters_resolve_odd_even():
    assert active_semesters("2026-10-26") == list(EVEN_SEMESTERS)  # October
    assert active_semesters("2026-02-10") == list(ODD_SEMESTERS)  # February
    # Window boundaries are inclusive
    assert active_semesters("2026-06-30") == list(ODD_SEMESTERS)
    assert active_semesters("2026-07-01") == list(EVEN_SEMESTERS)


def test_active_semesters_honor_overrides():
    windows = default_semester_windows(2026)
    windows["S4"] = SemesterWindow(
        "S4", dt.date(2026, 3, 1), dt.date(2026, 12, 31)
    )  # admin extends S4 into March
    assert "S4" in active_semesters("2026-03-15", windows)
    # Unoverridden call still uses defaults
    assert "S4" not in active_semesters("2026-03-15")


# ---------------------------------------------------------------- college seed


def test_seed_has_departments_faculty_divisions():
    d = load_seed_data()
    assert set(d.departments) == {"bs", "cse", "ece", "eee", "me", "ce"}
    eng_depts = {"cse", "ece", "eee", "me", "ce"}
    for dept in eng_depts:
        faculty = [t for t in d.teachers.values() if t.department == dept]
        assert 8 <= len(faculty) <= 12  # approximately ten per dept
        assert any(c.department == dept for c in d.classes.values())
    bs_faculty = [t for t in d.teachers.values() if t.department == "bs"]
    assert len(bs_faculty) == 5
    # Basic Science is a service department: faculty but no divisions
    assert not any(c.department == "bs" for c in d.classes.values())


def test_seed_division_sections_per_semester():
    d = load_seed_data()
    sections = {}
    for c in d.classes.values():
        sections.setdefault((c.department, c.semester), set()).add(c.section)
    for sem in SEMESTERS:
        assert sections[("cse", sem)] == {"A", "B", "C"}
        assert sections[("ece", sem)] == {"A", "B", "C"}
        for dept in ("eee", "me", "ce"):
            assert sections[(dept, sem)] == {"A", "B"}
    assert len(d.classes) == 96


def test_seed_referential_integrity():
    d = load_seed_data()
    for t in d.teachers.values():
        assert t.department in d.departments
        assert t.subjects <= set(d.subjects)
    for s in d.subjects.values():
        assert s.department in d.departments
    for c in d.classes.values():
        assert c.department in d.departments
        assert c.semester in SEMESTERS
        assert c.section
    for s in d.timetable:
        assert s.teacher in d.teachers
        assert s.room in d.rooms
        assert s.class_group in d.classes
        assert s.subject in d.subjects


def test_seed_no_same_parity_double_booking():
    d = load_seed_data()
    for parity in (ODD_SEMESTERS, EVEN_SEMESTERS):
        teachers_seen, rooms_seen = set(), set()
        for s in d.timetable:
            if d.classes[s.class_group].semester not in parity:
                continue
            assert (s.day, s.period, s.teacher) not in teachers_seen
            teachers_seen.add((s.day, s.period, s.teacher))
            assert (s.day, s.period, s.room) not in rooms_seen
            rooms_seen.add((s.day, s.period, s.room))


def test_seed_first_year_cross_department_teaching():
    d = load_seed_data()
    fy = [s for s in d.timetable if d.classes[s.class_group].first_year]
    assert fy
    bs_share = sum(
        1 for s in fy if d.teachers[s.teacher].department == "bs"
    ) / len(fy)
    assert bs_share >= 0.25  # Basic Science visibly teaches first year


# ------------------------------------------------------- store calendar overrides


def test_store_override_semester_window():
    store = Store(load_seed_data(), academic_year=2026)
    assert "S4" not in store.active_semesters("2026-03-15")
    store.override_semester_window("S4", dt.date(2026, 3, 1), dt.date(2026, 12, 31))
    assert "S4" in store.active_semesters("2026-03-15")


def test_store_override_validates_input():
    store = Store(load_seed_data(), academic_year=2026)
    with pytest.raises(KeyError):
        store.override_semester_window("S9", dt.date(2026, 1, 1), dt.date(2026, 6, 30))
    with pytest.raises(ValueError):
        store.override_semester_window("S2", dt.date(2026, 6, 30), dt.date(2026, 1, 1))


def test_store_overrides_reset_on_fresh_store():
    store = Store(load_seed_data(), academic_year=2026)
    store.override_semester_window("S4", dt.date(2026, 3, 1), dt.date(2026, 12, 31))
    fresh = Store(load_seed_data(), academic_year=2026)
    assert "S4" not in fresh.active_semesters("2026-03-15")
