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
from campusly.data import SchoolData, semester_parity
from campusly.models import SUPERVISION_SUBJECT, STATUS_UNCOVERED
from campusly.store import Store

MONDAY = "2026-10-26"


def _free_slot(store, class_group, day=None):
    """First (day, period) where the division has no class."""
    for d in ([day] if day else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]):
        for period in range(1, 7):
            if store.data.slot_at(d, period, class_group) is None:
                return d, period
    raise AssertionError("division has no free period")


def _free_teacher(store, day, period, parity, exclude=()):
    busy = store.data.teacher_at(day, period, parity) | set(exclude)
    return next(t.id for t in store.data.teachers.values() if t.id not in busy)
from campusly.models import (
    EXCHANGE_ACCEPTED,
    EXCHANGE_APPROVED,
    EXCHANGE_CANCELLED,
    EXCHANGE_DECLINED,
    EXCHANGE_PROPOSED,
    EXCHANGE_REJECTED,
    SUPERVISION_SUBJECT,
    ClassGroup,
    Department,
    Exchange,
    ProjectGroup,
    Room,
    Subject,
    Teacher,
    TimetableSlot,
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


def test_seed_divisions_have_free_periods():
    d = load_seed_data()
    day, period = _free_slot(Store(d), "CSE-S2-A")
    assert d.slot_at(day, period, "CSE-S2-A") is None


# -------------------------------------------------------- subject offerings


def test_add_offering_creates_division_slot():
    store = Store(load_seed_data())
    day, period = _free_slot(store, "CSE-S2-A")
    tid = _free_teacher(store, day, period, semester_parity("S2"))
    slot = store.add_offering("CSE-S2-A", "cs", tid, day, period)
    assert store.data.slot_at(day, period, "CSE-S2-A") is slot
    assert slot.subject == "cs" and slot.teacher == tid


def test_add_offering_rejects_conflicts():
    store = Store(load_seed_data())
    occupied = next(
        s for s in store.data.slots_on("Monday")
        if store.data.classes[s.class_group].semester in EVEN_SEMESTERS
    )
    with pytest.raises(ValueError, match="division already"):
        store.add_offering(occupied.class_group, "math", "B02", occupied.day, occupied.period)
    day, period = _free_slot(store, "CSE-S2-A")
    busy = next(iter(store.data.teacher_at(day, period, semester_parity("S2"))))
    with pytest.raises(ValueError, match="faculty already"):
        store.add_offering("CSE-S2-A", "cs", busy, day, period)


def test_reassign_offering_updates_and_validates():
    store = Store(load_seed_data())
    day, period = _free_slot(store, "CSE-S2-A")
    parity = semester_parity("S2")
    t1 = _free_teacher(store, day, period, parity)
    store.add_offering("CSE-S2-A", "cs", t1, day, period)
    t2 = _free_teacher(store, day, period, parity)
    store.reassign_offering(day, period, "CSE-S2-A", t2)
    assert store.data.slot_at(day, period, "CSE-S2-A").teacher == t2
    busy = next(iter(store.data.teacher_at(day, period, parity) - {t2}))
    with pytest.raises(ValueError):
        store.reassign_offering(day, period, "CSE-S2-A", busy)


def test_cross_department_flag():
    store = Store(load_seed_data())
    cross = next(s for s in store.data.timetable if store.cross_department(s))
    assert (
        store.data.teachers[cross.teacher].department
        != store.data.classes[cross.class_group].department
    )
    home = next(
        s for s in store.data.timetable
        if store.data.classes[s.class_group].department == "cse"
        and store.data.teachers[s.teacher].department == "cse"
    )
    assert not store.cross_department(home)


# ------------------------------------------------------- project supervision


def test_add_project_group_creates_supervision_slot():
    store = Store(load_seed_data())
    day, period = _free_slot(store, "ECE-S4-B")
    parity = semester_parity("S4")
    sup = _free_teacher(store, day, period, parity)
    room = next(
        r for r in store.data.rooms
        if r not in store.data.room_at(day, period, parity)
    )
    pg = store.add_project_group("Smart Grid", "ECE-S4-B", sup, day, period, room)
    assert pg.supervisor == sup
    slot = store.data.slot_at(day, period, "ECE-S4-B")
    assert slot.subject == SUPERVISION_SUBJECT and slot.teacher == sup


def test_add_project_group_rejects_conflicts():
    store = Store(load_seed_data())
    day, period = _free_slot(store, "ECE-S4-B")
    parity = semester_parity("S4")
    busy_sup = next(iter(store.data.teacher_at(day, period, parity)))
    free_room = next(
        r for r in store.data.rooms
        if r not in store.data.room_at(day, period, parity)
    )
    with pytest.raises(ValueError, match="supervisor"):
        store.add_project_group("X", "ECE-S4-B", busy_sup, day, period, free_room)
    busy_room = next(iter(store.data.room_at(day, period, parity)))
    free_sup = _free_teacher(store, day, period, parity)
    with pytest.raises(ValueError, match="room"):
        store.add_project_group("X", "ECE-S4-B", free_sup, day, period, busy_room)
    busy_div = store.data.slot_at("Monday", 1, "ECE-S4-B")
    if busy_div:
        with pytest.raises(ValueError, match="division"):
            store.add_project_group("X", "ECE-S4-B", "B02", "Monday", 1, free_room)


def test_reassign_supervisor_moves_slot():
    store = Store(load_seed_data())
    day, period = _free_slot(store, "ME-S6-A")
    parity = semester_parity("S6")
    sup = _free_teacher(store, day, period, parity)
    room = next(
        r for r in store.data.rooms
        if r not in store.data.room_at(day, period, parity)
    )
    pg = store.add_project_group("Y", "ME-S6-A", sup, day, period, room)
    new_sup = _free_teacher(store, day, period, parity, exclude={sup})
    store.reassign_supervisor(pg.id, new_sup)
    assert pg.supervisor == new_sup
    assert store.data.slot_at(day, period, "ME-S6-A").teacher == new_sup


def test_supervisor_absence_flagged_for_manual_handling():
    store = Store(load_seed_data())
    day, period = _free_slot(store, "ECE-S4-B", day="Monday")
    parity = semester_parity("S4")
    sup = _free_teacher(store, day, period, parity)
    room = next(
        r for r in store.data.rooms
        if r not in store.data.room_at(day, period, parity)
    )
    pg = store.add_project_group("Z", "ECE-S4-B", sup, day, period, room)
    store.report_absence(pg.supervisor, MONDAY)
    props = store.run_allocation(MONDAY)
    flagged = [p for p in props if p.subject == SUPERVISION_SUBJECT]
    assert flagged
    assert all(
        p.status == STATUS_UNCOVERED and "supervision-manual-handling" in p.warnings
        for p in flagged
    )


# ------------------------------------------------ scoping, parity, shared store


def test_department_scoped_queries():
    store = Store(load_seed_data())
    assert store.department_of("CSE-S2-A") == "cse"
    active = set(store.active_semesters(MONDAY))
    slot = next(
        s for s in store.data.slots_on("Monday")
        if store.data.classes[s.class_group].semester in active
        and store.data.classes[s.class_group].department == "cse"
    )
    store.report_absence(slot.teacher, MONDAY)
    store.run_allocation(MONDAY)
    cse_pending = store.pending(department="cse")
    assert cse_pending
    assert all(
        store.data.classes[p.class_group].department == "cse" for p in cse_pending
    )
    assert all(
        store.data.classes[p.class_group].department == "ece"
        for p in store.proposals_for(MONDAY, department="ece")
    )


def test_absence_reporter_department_scoping():
    store = Store(load_seed_data())
    cse_tid = next(t.id for t in store.data.teachers.values() if t.department == "cse")
    with pytest.raises(PermissionError):
        store.report_absence(cse_tid, MONDAY, reporter_department="ece")
    store.report_absence(cse_tid, MONDAY, reporter_department="cse")
    store2 = Store(load_seed_data())
    store2.report_absence(cse_tid, MONDAY)  # admin (None) is unrestricted


def test_uncovered_and_timetable_scoped_to_active_semesters():
    store = Store(load_seed_data())
    active = set(store.active_semesters(MONDAY))
    slot = next(
        s for s in store.data.slots_on("Monday")
        if store.data.classes[s.class_group].semester in active
    )
    absence = store.report_absence(slot.teacher, MONDAY)
    assert store.uncovered_slots(absence)
    assert all(
        store.data.classes[s.class_group].semester in active
        for s in store.uncovered_slots(absence)
    )
    rows = store.effective_timetable(MONDAY)
    assert rows
    assert all(store.data.classes[r["class_group"]].semester in active for r in rows)


def test_shared_store_instance():
    import app

    assert app.get_store() is app.get_store()


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


# ------------------------------------------------------------- period exchange


def _exchange_data():
    """Minimal college for exchange tests: all divisions in semester S2
    (even parity, in session on MONDAY)."""
    subjects = {
        "cs": Subject("cs", "Computer Science", "cse"),
        "ma": Subject("ma", "Mathematics", "bs"),
    }
    teachers = {
        "A1": Teacher("A1", "A1", frozenset({"cs"}), "cse"),
        "B1": Teacher("B1", "B1", frozenset({"ma"}), "cse"),
        "A2": Teacher("A2", "A2", frozenset({"cs"}), "ece"),
        "B2": Teacher("B2", "B2", frozenset({"ma"}), "ece"),
        "X1": Teacher("X1", "X1", frozenset({"cs"}), "cse"),
    }
    rooms = {r: Room(r, r) for r in ("R1", "R2", "R3")}
    classes = {
        cid: ClassGroup(cid, cid, dept, "S2", sec)
        for cid, dept, sec in (
            ("CSE-S2-A", "cse", "A"),
            ("CSE-S2-B", "cse", "B"),
            ("ECE-S2-A", "ece", "A"),
        )
    }
    timetable = [
        TimetableSlot("Monday", 1, "CSE-S2-A", "cs", "A1", "R1"),
        TimetableSlot("Tuesday", 2, "CSE-S2-A", "ma", "B1", "R1"),
        TimetableSlot("Monday", 3, "ECE-S2-A", "cs", "A2", "R2"),
        TimetableSlot("Monday", 1, "ECE-S2-A", "ma", "B2", "R2"),
        TimetableSlot("Tuesday", 4, "ECE-S2-A", "ma", "B2", "R2"),
        TimetableSlot("Monday", 1, "CSE-S2-B", "cs", "X1", "R3"),
    ]
    departments = {
        "bs": Department("bs", "Basic Science"),
        "cse": Department("cse", "CSE"),
        "ece": Department("ece", "ECE"),
    }
    return SchoolData(
        subjects=subjects,
        teachers=teachers,
        rooms=rooms,
        classes=classes,
        timetable=timetable,
        departments=departments,
    )


SLOT_A = ("Monday", 1, "CSE-S2-A")   # taught by A1 (cse)
SLOT_B = ("Monday", 3, "ECE-S2-A")   # taught by A2 (ece)


def _timetable_row(store, day, period, class_group, date=MONDAY):
    return next(
        r
        for r in store.effective_timetable(date)
        if r["day"] == day and r["period"] == period
        and r["class_group"] == class_group
    )


def test_exchange_full_lifecycle():
    store = Store(_exchange_data())
    x = store.propose_exchange("A1", SLOT_A, SLOT_B)
    assert x.status == EXCHANGE_PROPOSED
    assert x.counterparty == "A2"
    # Nothing changes before approval
    assert _timetable_row(store, *SLOT_A)["teacher"] == "A1"
    assert _timetable_row(store, *SLOT_B)["teacher"] == "A2"

    store.respond_exchange(x.id, accept=True, actor="A2")
    assert x.status == EXCHANGE_ACCEPTED
    assert store.pending_exchanges(department="cse") == [x]
    assert store.pending_exchanges(department="ece") == []
    # Accepted but unapproved is still invisible in timetables
    assert _timetable_row(store, *SLOT_A)["teacher"] == "A1"

    store.approve_exchange(x.id, department="cse")
    assert x.status == EXCHANGE_APPROVED
    row_a = _timetable_row(store, *SLOT_A)
    row_b = _timetable_row(store, *SLOT_B)
    assert row_a["teacher"] == "A2" and row_a["exchanged"]
    assert row_a["original_teacher"] == "A1"
    assert row_b["teacher"] == "A1" and row_b["exchanged"]
    # Faculty weekly timetables reflect the swap
    assert [s.key for s in store.teacher_slots("A2")] == [SLOT_A]
    assert SLOT_B in [s.key for s in store.teacher_slots("A1")]


def test_exchange_propose_rejects_double_booking():
    store = Store(_exchange_data())
    # B2 already teaches Monday P1 — cannot take over A1's Monday-P1 slot.
    with pytest.raises(ValueError, match="double-book"):
        store.propose_exchange("A1", SLOT_A, ("Tuesday", 4, "ECE-S2-A"))
    assert store.exchanges == []
    # Not your own slot / not yourself
    with pytest.raises(ValueError, match="not taught by the proposer"):
        store.propose_exchange("B1", SLOT_A, SLOT_B)
    with pytest.raises(ValueError, match="yourself"):
        store.propose_exchange(
            "B1", ("Tuesday", 2, "CSE-S2-A"), ("Tuesday", 2, "CSE-S2-A")
        )
    with pytest.raises(KeyError):
        store.propose_exchange("A1", ("Friday", 6, "CSE-S2-A"), SLOT_B)


def test_exchange_decline_and_cancel():
    store = Store(_exchange_data())
    x = store.propose_exchange("A1", SLOT_A, SLOT_B)
    with pytest.raises(PermissionError):
        store.respond_exchange(x.id, accept=True, actor="A1")  # not counterparty
    store.respond_exchange(x.id, accept=False, actor="A2")
    assert x.status == EXCHANGE_DECLINED
    assert _timetable_row(store, *SLOT_A)["teacher"] == "A1"

    y = store.propose_exchange("A1", SLOT_A, SLOT_B)
    with pytest.raises(PermissionError):
        store.cancel_exchange(y.id, actor="A2")  # not proposer
    store.cancel_exchange(y.id, actor="A1")
    assert y.status == EXCHANGE_CANCELLED

    z = store.propose_exchange("A1", SLOT_A, SLOT_B)
    store.respond_exchange(z.id, accept=True)
    with pytest.raises(ValueError):
        store.cancel_exchange(z.id, actor="A1")  # too late to cancel


def test_exchange_coordinator_scoping_and_reject():
    store = Store(_exchange_data())
    x = store.propose_exchange("A1", SLOT_A, SLOT_B)
    store.respond_exchange(x.id, accept=True)
    with pytest.raises(PermissionError):
        store.approve_exchange(x.id, department="ece")
    store.reject_exchange(x.id, department="cse")
    assert x.status == EXCHANGE_REJECTED
    assert _timetable_row(store, *SLOT_A)["teacher"] == "A1"
    assert _timetable_row(store, *SLOT_B)["teacher"] == "A2"
    with pytest.raises(ValueError):
        store.approve_exchange(x.id)  # rejected is terminal


def test_exchange_late_conflict_refused():
    store = Store(_exchange_data())
    x = store.propose_exchange("A1", SLOT_A, SLOT_B)
    store.respond_exchange(x.id, accept=True)
    # Meanwhile A2 is committed as substitute at Monday P1 (X1 absent).
    store.report_absence("X1", MONDAY)
    props = store.run_allocation(MONDAY)
    (p,) = [p for p in props if p.class_group == "CSE-S2-B"]
    assert p.substitute_teacher == "A2"  # only free cs-qualified faculty
    assert "cross-department" in p.warnings
    store.approve(p.id)
    with pytest.raises(ValueError, match="substitute"):
        store.approve_exchange(x.id, department="cse")
    assert x.status == EXCHANGE_ACCEPTED
    assert x.warnings
    assert _timetable_row(store, *SLOT_A)["teacher"] == "A1"  # swap not applied


def test_exchange_overrides_affect_uncovered_and_busy():
    store = Store(_exchange_data())
    x = store.propose_exchange("A1", SLOT_A, SLOT_B)
    store.respond_exchange(x.id, accept=True)
    store.approve_exchange(x.id)
    # After the swap an absent A2 uncovers A1's old slot, not their old one.
    absence = store.report_absence("A2", MONDAY)
    assert [s.key for s in store.uncovered_slots(absence)] == [SLOT_A]
    # And A1 (now at Monday P3) is free to substitute at Monday P1.
    props = store.run_allocation(MONDAY)
    (p,) = [p for p in props if p.class_group == "CSE-S2-A"]
    assert p.substitute_teacher == "A1"


def test_exchange_duplicate_slot_refused():
    store = Store(_exchange_data())
    store.propose_exchange("A1", SLOT_A, SLOT_B)
    # A second proposal involving SLOT_A (or SLOT_B) is stale/duplicate.
    with pytest.raises(ValueError, match="open exchange"):
        store.propose_exchange("X1", ("Monday", 1, "CSE-S2-B"), SLOT_B)
    assert len(store.exchanges) == 1


def test_exchange_unqualified_swap_refused():
    store = Store(_exchange_data())
    # A1 (cs) would take over B1's ma slot; neither is qualified crosswise.
    with pytest.raises(ValueError, match="not qualified"):
        store.propose_exchange("A1", SLOT_A, ("Tuesday", 2, "CSE-S2-A"))
    assert store.exchanges == []


def test_exchange_supervision_slot_refused():
    store = Store(_exchange_data())
    # B1 supervises a project group — its supervision slot is off-limits.
    store.add_project_group("P", "ECE-S2-A", "B1", "Wednesday", 4, "R2")
    sup = ("Wednesday", 4, "ECE-S2-A")
    with pytest.raises(ValueError, match="supervision"):
        store.propose_exchange("B1", sup, SLOT_B)
    with pytest.raises(ValueError, match="supervision"):
        store.propose_exchange("A1", SLOT_A, sup)


def test_exchange_options_only_eligible():
    store = Store(_exchange_data())
    eligible, blocked = store.exchange_options("A1", SLOT_A)
    # A1 is only qualified for cs, so only cs slots qualify: A2's Mon-P3
    # slot, and X1's Mon-P1 slot (swapping same-time slots is conflict-free).
    assert {s.key for s in eligible} == {SLOT_B, ("Monday", 1, "CSE-S2-B")}
    assert ("Tuesday", 2, "CSE-S2-A") in blocked   # unqualified both ways
    assert ("Monday", 1, "ECE-S2-A") in blocked    # B2 busy + unqualified


def test_exchange_approval_on_removed_slot_fails_cleanly():
    store = Store(_exchange_data())
    x = store.propose_exchange("A1", SLOT_A, SLOT_B)
    store.respond_exchange(x.id, accept=True)
    store.data.timetable[:] = [
        s for s in store.data.timetable if s.key != SLOT_A
    ]
    with pytest.raises(ValueError, match="can no longer be applied"):
        store.approve_exchange(x.id)
    assert x.status == EXCHANGE_ACCEPTED


def test_reject_proposal_scoped_to_department():
    store = Store(_exchange_data())
    store.report_absence("X1", MONDAY)
    store.run_allocation(MONDAY)
    p = next(p for p in store.pending(department="cse"))
    with pytest.raises(PermissionError):
        store.approve(p.id, department="ece")
    store.approve(p.id, department="cse")
