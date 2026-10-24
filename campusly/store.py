"""In-memory application state: absences, proposals, review actions, views.

The seed timetable is immutable; approvals are layered on top to produce an
"effective timetable" for a date. Nothing mutates the published timetable
until a coordinator approves a proposal.
"""

from __future__ import annotations

import datetime as dt
import itertools

from .data import (
    SEMESTERS,
    SchoolData,
    SemesterWindow,
    day_name,
    default_semester_windows,
)
from .data import active_semesters as _active_semesters
from .engine import allocate
from .models import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_UNCOVERED,
    Absence,
    Proposal,
    TimetableSlot,
)


class DuplicateAbsenceError(ValueError):
    pass


class Store:
    def __init__(self, data: SchoolData, academic_year: int | None = None):
        self.data = data
        self.absences: list[Absence] = []
        self.proposals: list[Proposal] = []
        self._seq = itertools.count(1)
        # In-memory only: a fresh Store always starts from default windows.
        self.semester_windows = default_semester_windows(
            academic_year if academic_year is not None else dt.date.today().year
        )

    # ----- academic calendar ---------------------------------------------------

    def override_semester_window(
        self, semester: str, start: dt.date, end: dt.date
    ) -> None:
        """Admin override of a semester's date range (not persisted)."""
        if semester not in SEMESTERS:
            raise KeyError(f"unknown semester {semester}")
        if end < start:
            raise ValueError("semester window ends before it starts")
        self.semester_windows[semester] = SemesterWindow(semester, start, end)

    def active_semesters(self, date: str) -> list[str]:
        return _active_semesters(date, self.semester_windows)

    # ----- absence reporting -------------------------------------------------

    def report_absence(self, teacher_id: str, date: str) -> Absence:
        if teacher_id not in self.data.teachers:
            raise KeyError(f"unknown teacher {teacher_id}")
        if any(a.teacher == teacher_id and a.date == date for a in self.absences):
            raise DuplicateAbsenceError(f"{teacher_id} already absent on {date}")
        absence = Absence(teacher=teacher_id, date=date)
        self.absences.append(absence)
        return absence

    def uncovered_slots(self, absence: Absence) -> list[TimetableSlot]:
        """Scheduled periods the absent teacher was due to teach that date."""
        day = day_name(absence.date)
        if day is None:
            return []
        return [
            s for s in self.data.slots_on(day) if s.teacher == absence.teacher
        ]

    # ----- allocation ---------------------------------------------------------

    def run_allocation(self, date: str) -> list[Proposal]:
        """Create pending proposals for every still-uncovered slot on `date`.

        Slots that already have a pending or approved proposal are skipped,
        so reruns are idempotent and only fill newly uncovered periods.
        """
        day = day_name(date)
        absences = [a for a in self.absences if a.date == date]
        if day is None or not absences:
            return []

        covered_keys = {(p.day, p.period, p.class_group) for p in self.proposals}
        slots = [
            s
            for a in absences
            for s in self.uncovered_slots(a)
            if s.key not in covered_keys
        ]
        if not slots:
            return []

        # Seed "taken" from existing pending/approved assignments so a new
        # absence can't steal a substitute already committed this date.
        taken: dict[tuple[str, int], set[str]] = {}
        taken_rooms: dict[tuple[str, int], set[str]] = {}
        for p in self.proposals:
            if p.status in (STATUS_PENDING, STATUS_APPROVED) and p.substitute_teacher:
                taken.setdefault((p.day, p.period), set()).add(p.substitute_teacher)
                if p.assigned_room:
                    taken_rooms.setdefault((p.day, p.period), set()).add(p.assigned_room)

        absent_ids = {a.teacher for a in absences}
        seq = max((int(p.id.rsplit("-", 1)[1]) for p in self.proposals), default=0) + 1
        new = allocate(
            self.data,
            slots,
            date=date,
            absent_teachers=absent_ids,
            workload=self._weekly_workload(date),
            taken=taken,
            taken_rooms=taken_rooms,
            start_seq=seq,
        )
        self.proposals.extend(new)
        return new

    # ----- review -------------------------------------------------------------

    def pending(self) -> list[Proposal]:
        return [p for p in self.proposals if p.status == STATUS_PENDING]

    def approve(self, proposal_id: str) -> None:
        p = self._proposal(proposal_id)
        if p.status != STATUS_PENDING:
            raise ValueError(f"proposal {proposal_id} is not pending")
        p.status = STATUS_APPROVED

    def reject(self, proposal_id: str) -> None:
        p = self._proposal(proposal_id)
        if p.status != STATUS_PENDING:
            raise ValueError(f"proposal {proposal_id} is not pending")
        p.status = STATUS_UNCOVERED
        if "rejected" not in p.warnings:
            p.warnings.append("rejected")

    def _proposal(self, proposal_id: str) -> Proposal:
        for p in self.proposals:
            if p.id == proposal_id:
                return p
        raise KeyError(f"unknown proposal {proposal_id}")

    # ----- views ----------------------------------------------------------------

    def proposals_for(self, date: str) -> list[Proposal]:
        return sorted(
            (p for p in self.proposals if p.date == date),
            key=lambda p: (p.period, p.class_group),
        )

    def effective_timetable(self, date: str) -> list[dict]:
        """Rows for the selected date: scheduled slot plus coverage state."""
        day = day_name(date)
        if day is None:
            return []
        by_key = {(p.day, p.period, p.class_group): p for p in self.proposals_for(date)}
        rows = []
        for s in sorted(
            self.data.slots_on(day), key=lambda s: (s.period, s.class_group)
        ):
            p = by_key.get(s.key)
            if p is None:
                teacher, status = s.teacher, "scheduled"
            elif p.status == STATUS_APPROVED:
                teacher, status = p.substitute_teacher, "approved"
            else:
                teacher, status = None, p.status  # pending / uncovered
            rows.append(
                {
                    "day": s.day,
                    "period": s.period,
                    "class_group": s.class_group,
                    "subject": s.subject,
                    "room": (p.assigned_room if p and p.status == STATUS_APPROVED else s.room),
                    "teacher": teacher,
                    "original_teacher": s.teacher if p else None,
                    "status": status,
                    "proposal": p,
                }
            )
        return rows

    def notices(self, date: str) -> list[str]:
        out = []
        for p in self.proposals_for(date):
            cls = self.data.classes[p.class_group].name
            subj = self.data.subjects[p.subject].name
            orig = self.data.teachers[p.absent_teacher].name
            if p.status == STATUS_APPROVED:
                sub = self.data.teachers[p.substitute_teacher].name
                out.append(
                    f"{cls} — Period {p.period} {subj}: {sub} covers for {orig} (Room {p.assigned_room})."
                )
            elif p.status == STATUS_UNCOVERED:
                out.append(
                    f"{cls} — Period {p.period} {subj}: NO substitute found for {orig}'s class."
                )
        return out

    def counts(self, date: str) -> dict[str, int]:
        props = self.proposals_for(date)
        return {
            "absences": sum(1 for a in self.absences if a.date == date),
            "pending": sum(1 for p in props if p.status == STATUS_PENDING),
            "approved": sum(1 for p in props if p.status == STATUS_APPROVED),
            "uncovered": sum(1 for p in props if p.status == STATUS_UNCOVERED),
        }

    def _weekly_workload(self, date: str) -> dict[str, int]:
        target = dt.date.fromisoformat(date).isocalendar()[:2]
        load: dict[str, int] = {}
        for p in self.proposals:
            if p.substitute_teacher and p.status in (STATUS_PENDING, STATUS_APPROVED):
                if dt.date.fromisoformat(p.date).isocalendar()[:2] == target:
                    load[p.substitute_teacher] = load.get(p.substitute_teacher, 0) + 1
        return load

    def workload(self, date: str) -> dict[str, int]:
        return self._weekly_workload(date)
