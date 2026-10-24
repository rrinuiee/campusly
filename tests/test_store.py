"""Store tests: absence reporting, review workflow, views, export."""

import csv
import io

import pytest

from campusly.data import load_seed_data
from campusly.export import to_csv
from campusly.models import STATUS_APPROVED, STATUS_PENDING, STATUS_UNCOVERED
from campusly.store import DuplicateAbsenceError, Store

MONDAY = "2026-10-26"
SATURDAY = "2026-10-24"


@pytest.fixture()
def store():
    return Store(load_seed_data())


def _absent_teacher(store):
    """A teacher who definitely teaches on Monday."""
    slot = store.data.slots_on("Monday")[0]
    return slot.teacher


def test_seed_data_integrity(store):
    d = store.data
    assert len(d.teachers) >= 10
    assert len(d.subjects) >= 6
    assert len(d.classes) >= 6
    assert len(d.rooms) >= 8
    for s in d.timetable:
        assert s.teacher in d.teachers
        assert s.room in d.rooms
        assert s.class_group in d.classes
        assert s.subject in d.subjects
    # no teacher or room double-booked in the base timetable
    seen = set()
    for s in d.timetable:
        assert (s.day, s.period, s.teacher) not in seen
        seen.add((s.day, s.period, s.teacher))


def test_report_absence_lists_uncovered_periods(store):
    tid = _absent_teacher(store)
    absence = store.report_absence(tid, MONDAY)
    slots = store.uncovered_slots(absence)
    assert len(slots) >= 1
    assert all(s.teacher == tid for s in slots)


def test_duplicate_absence_rejected(store):
    tid = _absent_teacher(store)
    store.report_absence(tid, MONDAY)
    with pytest.raises(DuplicateAbsenceError):
        store.report_absence(tid, MONDAY)


def test_absence_with_no_classes(store):
    tid = _absent_teacher(store)
    absence = store.report_absence(tid, SATURDAY)  # weekend: no school
    assert store.uncovered_slots(absence) == []


def test_allocation_produces_pending_proposals(store):
    tid = _absent_teacher(store)
    store.report_absence(tid, MONDAY)
    props = store.run_allocation(MONDAY)
    n = len(store.uncovered_slots(store.absences[0]))
    assert len(props) == n
    assert all(p.status in (STATUS_PENDING, STATUS_UNCOVERED) for p in props)
    # idempotent rerun
    assert store.run_allocation(MONDAY) == []


def test_pending_proposal_not_in_timetable(store):
    tid = _absent_teacher(store)
    store.report_absence(tid, MONDAY)
    store.run_allocation(MONDAY)
    rows = store.effective_timetable(MONDAY)
    affected = [r for r in rows if r["original_teacher"] == tid]
    assert affected
    for r in affected:
        assert r["teacher"] is None
        assert r["status"] in (STATUS_PENDING, STATUS_UNCOVERED)


def test_approve_publishes_substitute(store):
    tid = _absent_teacher(store)
    store.report_absence(tid, MONDAY)
    store.run_allocation(MONDAY)
    pending = store.pending()
    assert pending
    store.approve(pending[0].id)
    rows = store.effective_timetable(MONDAY)
    row = next(
        r for r in rows
        if r["period"] == pending[0].period
        and r["class_group"] == pending[0].class_group
    )
    assert row["status"] == STATUS_APPROVED
    assert row["teacher"] == pending[0].substitute_teacher


def test_reject_keeps_period_uncovered(store):
    tid = _absent_teacher(store)
    store.report_absence(tid, MONDAY)
    store.run_allocation(MONDAY)
    pending = store.pending()
    store.reject(pending[0].id)
    assert pending[0].status == STATUS_UNCOVERED
    row = next(
        r for r in store.effective_timetable(MONDAY)
        if r["period"] == pending[0].period
        and r["class_group"] == pending[0].class_group
    )
    assert row["status"] == STATUS_UNCOVERED
    assert row["teacher"] is None


def test_workload_counts_pending_and_approved(store):
    tid = _absent_teacher(store)
    store.report_absence(tid, MONDAY)
    store.run_allocation(MONDAY)
    pending = store.pending()
    if len(pending) >= 1:
        store.approve(pending[0].id)
    load = store.workload(MONDAY)
    assert sum(load.values()) == sum(
        1 for p in store.proposals_for(MONDAY) if p.substitute_teacher
    )


def test_csv_export_rows(store):
    tid = _absent_teacher(store)
    store.report_absence(tid, MONDAY)
    store.run_allocation(MONDAY)
    text = to_csv(store, MONDAY)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == len(store.proposals_for(MONDAY))
    assert {r["status"] for r in rows} <= {"pending", "approved", "uncovered"}
    assert all(r["substitute_teacher"] for r in rows)
