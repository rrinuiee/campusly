"""In-memory application state: absences, proposals, review actions, views.

The seed timetable is immutable; approvals are layered on top to produce an
"effective timetable" for a date. Nothing mutates the published timetable
until a coordinator approves a proposal.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import itertools

from .data import (
    SEMESTERS,
    SchoolData,
    SemesterWindow,
    day_name,
    default_semester_windows,
    semester_parity,
)
from .data import active_semesters as _active_semesters
from .engine import allocate
from .generator import generate
from .models import (
    EXCHANGE_ACCEPTED,
    EXCHANGE_APPROVED,
    EXCHANGE_CANCELLED,
    EXCHANGE_DECLINED,
    EXCHANGE_PROPOSED,
    EXCHANGE_REJECTED,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_UNCOVERED,
    SUPERVISION_SUBJECT,
    TT_DISCARDED,
    TT_DRAFT,
    TT_PUBLISHED,
    Absence,
    Exchange,
    GeneratedTimetable,
    ProjectGroup,
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
        self.projects: list[ProjectGroup] = []
        self.exchanges: list[Exchange] = []
        self.tt_drafts: list[GeneratedTimetable] = []
        self.academic_year = (
            academic_year if academic_year is not None else dt.date.today().year
        )
        # Per-slot teacher overrides written by approved exchanges; the
        # base timetable stays immutable, same as for substitutions.
        self.exchange_overrides: dict[tuple[str, int, str], str] = {}
        self._seq = itertools.count(1)
        self._pg_seq = itertools.count(1)
        self._x_seq = itertools.count(1)
        # In-memory only: a fresh Store always starts from default windows.
        self.semester_windows = default_semester_windows(self.academic_year)

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

    def report_absence(
        self, teacher_id: str, date: str, reporter_department: str | None = None
    ) -> Absence:
        """Record a faculty absence. `reporter_department` scopes the action:
        None acts as Admin (any faculty); a department id acts as that
        department's coordinator and may only report its own faculty."""
        if teacher_id not in self.data.teachers:
            raise KeyError(f"unknown teacher {teacher_id}")
        if (
            reporter_department is not None
            and self.data.teachers[teacher_id].department != reporter_department
        ):
            raise PermissionError(
                "coordinators may only report absences in their own department"
            )
        if any(a.teacher == teacher_id and a.date == date for a in self.absences):
            raise DuplicateAbsenceError(f"{teacher_id} already absent on {date}")
        absence = Absence(teacher=teacher_id, date=date)
        self.absences.append(absence)
        return absence

    def uncovered_slots(self, absence: Absence) -> list[TimetableSlot]:
        """In-session periods the absent teacher was due to teach that date."""
        day = day_name(absence.date)
        if day is None:
            return []
        active = set(self.active_semesters(absence.date))
        return [
            s
            for s in self.data.slots_on(day)
            if self.effective_teacher(s) == absence.teacher
            and self.data.classes[s.class_group].semester in active
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

        # Supervision slots are never auto-allocated — flag for manual handling.
        supervision = [s for s in slots if s.subject == SUPERVISION_SUBJECT]
        slots = [s for s in slots if s.subject != SUPERVISION_SUBJECT]

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
        new = (
            allocate(
                self.data,
                slots,
                date=date,
                absent_teachers=absent_ids,
                workload=self._weekly_workload(date),
                taken=taken,
                taken_rooms=taken_rooms,
                start_seq=seq,
                exchange_overrides=self.exchange_overrides,
            )
            if slots
            else []
        )
        for s in supervision:
            new.append(
                Proposal(
                    id=f"P-{date}-{seq + len(new):03d}",
                    date=date,
                    day=s.day,
                    period=s.period,
                    class_group=s.class_group,
                    subject=s.subject,
                    absent_teacher=s.teacher,
                    room=s.room,
                    warnings=["supervision-manual-handling"],
                    status=STATUS_UNCOVERED,
                )
            )
        self.proposals.extend(new)
        return new

    # ----- subject offerings --------------------------------------------------

    def cross_department(self, slot: TimetableSlot) -> bool:
        """True when the slot's faculty home dept differs from the division's."""
        return (
            self.data.teachers[self.effective_teacher(slot)].department
            != self.data.classes[slot.class_group].department
        )

    def add_offering(
        self, class_group: str, subject: str, teacher: str, day: str, period: int
    ) -> TimetableSlot:
        """Assign `teacher` to teach `subject` to `class_group` at day/period.

        The timetable slot IS the offering record. Rejects division,
        faculty, and (implicitly) room double-booking within the division's
        semester parity.
        """
        if class_group not in self.data.classes:
            raise KeyError(f"unknown division {class_group}")
        if subject not in self.data.subjects:
            raise KeyError(f"unknown subject {subject}")
        if teacher not in self.data.teachers:
            raise KeyError(f"unknown teacher {teacher}")
        if self.data.slot_at(day, period, class_group) is not None:
            raise ValueError("division already has a class at that time")
        parity = semester_parity(self.data.classes[class_group].semester)
        if teacher in self.data.teacher_at(day, period, parity):
            raise ValueError("faculty already teaching at that time")
        room = self._division_room(class_group)
        if room is None:
            occupied = self.data.room_at(day, period, parity)
            room = next((r for r in sorted(self.data.rooms) if r not in occupied), None)
        if room is None:
            raise ValueError("no room available at that time")
        slot = TimetableSlot(day, period, class_group, subject, teacher, room)
        self.data.timetable.append(slot)
        return slot

    def reassign_offering(
        self, day: str, period: int, class_group: str, new_teacher: str
    ) -> TimetableSlot:
        """Change the faculty on an existing slot (offering reassignment)."""
        slot = self.data.slot_at(day, period, class_group)
        if slot is None:
            raise KeyError("no offering at that time for this division")
        if new_teacher not in self.data.teachers:
            raise KeyError(f"unknown teacher {new_teacher}")
        parity = semester_parity(self.data.classes[class_group].semester)
        busy = self.data.teacher_at(day, period, parity) - {slot.teacher}
        if new_teacher in busy:
            raise ValueError("faculty already teaching at that time")
        updated = dataclasses.replace(slot, teacher=new_teacher)
        self.data.timetable[self.data.timetable.index(slot)] = updated
        return updated

    def _division_room(self, class_group: str) -> str | None:
        """The division's home room (room of its first existing slot)."""
        for s in self.data.timetable:
            if s.class_group == class_group:
                return s.room
        return None

    # ----- project supervision -------------------------------------------------

    def add_project_group(
        self,
        title: str,
        class_group: str,
        supervisor: str,
        day: str,
        period: int,
        room: str,
    ) -> ProjectGroup:
        """Create a project group with a weekly supervision slot.

        Division, supervisor, and room must all be free at that time within
        the division's semester parity. The supervision slot is a timetable
        slot whose subject marker is `supervision`.
        """
        if class_group not in self.data.classes:
            raise KeyError(f"unknown division {class_group}")
        if supervisor not in self.data.teachers:
            raise KeyError(f"unknown teacher {supervisor}")
        if room not in self.data.rooms:
            raise KeyError(f"unknown room {room}")
        parity = semester_parity(self.data.classes[class_group].semester)
        if self.data.slot_at(day, period, class_group) is not None:
            raise ValueError("division already has a class at that time")
        if supervisor in self.data.teacher_at(day, period, parity):
            raise ValueError("supervisor already teaching at that time")
        if room in self.data.room_at(day, period, parity):
            raise ValueError("room already occupied at that time")
        pg = ProjectGroup(
            id=f"PG-{next(self._pg_seq):03d}",
            title=title,
            class_group=class_group,
            supervisor=supervisor,
            day=day,
            period=period,
            room=room,
        )
        self.projects.append(pg)
        self.data.timetable.append(
            TimetableSlot(
                day, period, class_group, SUPERVISION_SUBJECT, supervisor, room
            )
        )
        return pg

    def reassign_supervisor(self, project_id: str, new_supervisor: str) -> None:
        """Move a project's supervision slot to a different faculty member."""
        pg = next((p for p in self.projects if p.id == project_id), None)
        if pg is None:
            raise KeyError(f"unknown project {project_id}")
        if new_supervisor not in self.data.teachers:
            raise KeyError(f"unknown teacher {new_supervisor}")
        parity = semester_parity(self.data.classes[pg.class_group].semester)
        busy = self.data.teacher_at(pg.day, pg.period, parity) - {pg.supervisor}
        if new_supervisor in busy:
            raise ValueError("new supervisor already teaching at that time")
        slot = self.data.slot_at(pg.day, pg.period, pg.class_group)
        updated = dataclasses.replace(slot, teacher=new_supervisor)
        self.data.timetable[self.data.timetable.index(slot)] = updated
        pg.supervisor = new_supervisor

    # ----- period exchanges ----------------------------------------------------

    def effective_teacher(self, slot: TimetableSlot) -> str:
        """Who actually teaches this slot after applied exchanges."""
        return self.exchange_overrides.get(slot.key, slot.teacher)

    def teacher_slots(self, teacher_id: str) -> list[TimetableSlot]:
        """Effective weekly slots currently taught by this faculty member."""
        return [
            s for s in self.data.timetable if self.effective_teacher(s) == teacher_id
        ]

    def _slot(self, key: tuple[str, int, str], label: str) -> TimetableSlot:
        s = self.data.slot_at(*key)
        if s is None:
            raise KeyError(f"no scheduled slot for {label} at {key}")
        return s

    def _swap_conflicts(
        self, mover: str, target: TimetableSlot, vacated: TimetableSlot
    ) -> list[str]:
        """Reasons `mover` cannot take over `target`'s day/period."""
        out: list[str] = []
        parity = semester_parity(self.data.classes[target.class_group].semester)
        for s in self.data.timetable:
            if s.key == vacated.key or s.day != target.day or s.period != target.period:
                continue
            sem = self.data.classes[s.class_group].semester
            if sem and sem not in parity:
                continue
            if self.effective_teacher(s) == mover:
                out.append(
                    f"{mover} already teaches {s.class_group} "
                    f"at {target.day} period {target.period}"
                )
        for p in self.proposals:
            if (
                p.substitute_teacher == mover
                and p.status in (STATUS_PENDING, STATUS_APPROVED)
                and p.day == target.day
                and p.period == target.period
            ):
                out.append(
                    f"{mover} is committed as substitute "
                    f"at {target.day} period {target.period} on {p.date}"
                )
        return out

    def _exchange_reasons(
        self, proposer: str, sa: TimetableSlot, sb: TimetableSlot
    ) -> list[str]:
        """Every reason the swap of `sa` (proposer's) and `sb` cannot proceed.

        Covers participant double-booking, self-swaps, supervision slots,
        slots already in an open exchange, and faculty not qualified for
        the subject they would take over.
        """
        counterparty = self.effective_teacher(sb)
        reasons = self._swap_conflicts(proposer, sb, sa) + self._swap_conflicts(
            counterparty, sa, sb
        )
        if counterparty == proposer:
            reasons.append("cannot exchange slots with yourself")
        if sa.subject == SUPERVISION_SUBJECT or sb.subject == SUPERVISION_SUBJECT:
            reasons.append("supervision meetings cannot be exchanged")
        for x in self.exchanges:
            if x.status not in (EXCHANGE_PROPOSED, EXCHANGE_ACCEPTED):
                continue
            if sa.key in (x.proposer_slot, x.counterparty_slot) or sb.key in (
                x.proposer_slot,
                x.counterparty_slot,
            ):
                reasons.append(f"a slot is already part of open exchange {x.id}")
                break
        for mover, target in ((proposer, sb), (counterparty, sa)):
            if (
                target.subject != SUPERVISION_SUBJECT
                and target.subject not in self.data.teachers[mover].subjects
            ):
                reasons.append(
                    f"{self.data.teachers[mover].name} is not qualified to "
                    f"teach {self.data.subjects[target.subject].name}"
                )
        return reasons

    def exchange_options(
        self, proposer: str, proposer_slot: tuple[str, int, str]
    ) -> tuple[list[TimetableSlot], dict[tuple[str, int, str], list[str]]]:
        """Slots eligible to swap for `proposer_slot`.

        Returns (eligible slots, {excluded slot key: [reasons]}) within the
        offered slot's semester parity, so the UI can offer only feasible
        counterparty slots instead of failing at submission.
        """
        sa = self._slot(proposer_slot, "proposer")
        parity = semester_parity(self.data.classes[sa.class_group].semester)
        eligible: list[TimetableSlot] = []
        blocked: dict[tuple[str, int, str], list[str]] = {}
        for s in self.data.timetable:
            sem = self.data.classes[s.class_group].semester
            if sem and sem not in parity:
                continue
            if (
                self.effective_teacher(s) == proposer
                or s.key in self.exchange_overrides
            ):
                continue
            reasons = self._exchange_reasons(proposer, sa, s)
            if reasons:
                blocked[s.key] = reasons
            else:
                eligible.append(s)
        return eligible, blocked

    def propose_exchange(
        self,
        proposer: str,
        proposer_slot: tuple[str, int, str],
        counterparty_slot: tuple[str, int, str],
    ) -> Exchange:
        """Propose swapping `proposer`'s slot for another faculty member's.

        The swap is validated up front: double-booking, unqualified
        takeovers, supervision slots, and slots already in an open exchange
        are rejected and nothing is recorded.
        """
        if proposer not in self.data.teachers:
            raise KeyError(f"unknown teacher {proposer}")
        sa = self._slot(proposer_slot, "proposer")
        sb = self._slot(counterparty_slot, "counterparty")
        if sa.key in self.exchange_overrides or sb.key in self.exchange_overrides:
            raise ValueError("a slot in an approved exchange cannot be exchanged again")
        if self.effective_teacher(sa) != proposer:
            raise ValueError("the offered slot is not taught by the proposer")
        counterparty = self.effective_teacher(sb)
        reasons = self._exchange_reasons(proposer, sa, sb)
        conflicts = [
            r for r in reasons if "already teaches" in r or "substitute" in r
        ]
        if conflicts:
            raise ValueError("exchange would double-book: " + "; ".join(conflicts))
        if reasons:
            raise ValueError("exchange cannot proceed: " + "; ".join(reasons))
        ex = Exchange(
            id=f"X-{next(self._x_seq):03d}",
            proposer=proposer,
            counterparty=counterparty,
            proposer_slot=proposer_slot,
            counterparty_slot=counterparty_slot,
        )
        self.exchanges.append(ex)
        return ex

    def respond_exchange(
        self, exchange_id: str, accept: bool, actor: str | None = None
    ) -> None:
        """Counterparty answers a pending exchange (accept forwards to the
        coordinator, decline closes it)."""
        x = self._exchange(exchange_id)
        if x.status != EXCHANGE_PROPOSED:
            raise ValueError(f"exchange {exchange_id} is not awaiting an answer")
        if actor is not None and actor != x.counterparty:
            raise PermissionError("only the counterparty may answer an exchange")
        x.status = EXCHANGE_ACCEPTED if accept else EXCHANGE_DECLINED

    def cancel_exchange(self, exchange_id: str, actor: str | None = None) -> None:
        """Proposer withdraws an exchange the counterparty has not answered."""
        x = self._exchange(exchange_id)
        if x.status != EXCHANGE_PROPOSED:
            raise ValueError("only an unanswered exchange can be cancelled")
        if actor is not None and actor != x.proposer:
            raise PermissionError("only the proposer may cancel an exchange")
        x.status = EXCHANGE_CANCELLED

    def approve_exchange(self, exchange_id: str, department: str | None = None) -> None:
        """Coordinator approval: re-validate, then swap both slots' faculty
        atomically via effective-timetable overrides."""
        x = self._exchange(exchange_id)
        if x.status != EXCHANGE_ACCEPTED:
            raise ValueError(f"exchange {exchange_id} is not awaiting approval")
        self._require_department(
            department, self.data.teachers[x.proposer].department
        )
        try:
            sa = self._slot(x.proposer_slot, "proposer")
            sb = self._slot(x.counterparty_slot, "counterparty")
        except KeyError as e:
            raise ValueError(
                f"exchange {exchange_id} can no longer be applied: {e}"
            ) from e
        conflicts = []
        if self.effective_teacher(sa) != x.proposer:
            conflicts.append("proposer no longer teaches the offered slot")
        if self.effective_teacher(sb) != x.counterparty:
            conflicts.append("counterparty no longer teaches the offered slot")
        conflicts += self._swap_conflicts(x.proposer, sb, sa)
        conflicts += self._swap_conflicts(x.counterparty, sa, sb)
        if conflicts:
            for c in conflicts:
                if c not in x.warnings:
                    x.warnings.append(c)
            raise ValueError(
                "exchange can no longer be applied: " + "; ".join(conflicts)
            )
        self.exchange_overrides[sa.key] = x.counterparty
        self.exchange_overrides[sb.key] = x.proposer
        x.status = EXCHANGE_APPROVED

    def reject_exchange(self, exchange_id: str, department: str | None = None) -> None:
        """Coordinator rejection: closes the exchange, timetables unchanged."""
        x = self._exchange(exchange_id)
        if x.status != EXCHANGE_ACCEPTED:
            raise ValueError(f"exchange {exchange_id} is not awaiting approval")
        self._require_department(
            department, self.data.teachers[x.proposer].department
        )
        x.status = EXCHANGE_REJECTED

    def exchanges_for(self, teacher_id: str) -> list[Exchange]:
        """Every exchange this faculty member proposed or was offered."""
        return [
            x
            for x in self.exchanges
            if teacher_id in (x.proposer, x.counterparty)
        ]

    def pending_exchanges(self, department: str | None = None) -> list[Exchange]:
        """Accepted exchanges awaiting approval by the proposer's department."""
        return [
            x
            for x in self.exchanges
            if x.status == EXCHANGE_ACCEPTED
            and (
                department is None
                or self.data.teachers[x.proposer].department == department
            )
        ]

    def _exchange(self, exchange_id: str) -> Exchange:
        for x in self.exchanges:
            if x.id == exchange_id:
                return x
        raise KeyError(f"unknown exchange {exchange_id}")

    def _require_department(
        self, acting: str | None, required: str
    ) -> None:
        if acting is not None and acting != required:
            raise PermissionError(
                "coordinators may only act on their own department"
            )

    # ----- review -------------------------------------------------------------

    def department_of(self, class_group: str) -> str:
        return self.data.classes[class_group].department

    def pending(self, department: str | None = None) -> list[Proposal]:
        return [
            p
            for p in self.proposals
            if p.status == STATUS_PENDING
            and (department is None or self.department_of(p.class_group) == department)
        ]

    def approve(self, proposal_id: str, department: str | None = None) -> None:
        p = self._proposal(proposal_id)
        if p.status != STATUS_PENDING:
            raise ValueError(f"proposal {proposal_id} is not pending")
        self._require_department(department, self.department_of(p.class_group))
        p.status = STATUS_APPROVED

    def reject(self, proposal_id: str, department: str | None = None) -> None:
        p = self._proposal(proposal_id)
        if p.status != STATUS_PENDING:
            raise ValueError(f"proposal {proposal_id} is not pending")
        self._require_department(department, self.department_of(p.class_group))
        p.status = STATUS_UNCOVERED
        if "rejected" not in p.warnings:
            p.warnings.append("rejected")

    def _proposal(self, proposal_id: str) -> Proposal:
        for p in self.proposals:
            if p.id == proposal_id:
                return p
        raise KeyError(f"unknown proposal {proposal_id}")

    # ----- views ----------------------------------------------------------------

    def proposals_for(self, date: str, department: str | None = None) -> list[Proposal]:
        return sorted(
            (
                p
                for p in self.proposals
                if p.date == date
                and (department is None or self.department_of(p.class_group) == department)
            ),
            key=lambda p: (p.period, p.class_group),
        )

    def effective_timetable(self, date: str) -> list[dict]:
        """Rows for the selected date: scheduled slot plus coverage state."""
        day = day_name(date)
        if day is None:
            return []
        active = set(self.active_semesters(date))
        by_key = {(p.day, p.period, p.class_group): p for p in self.proposals_for(date)}
        rows = []
        for s in sorted(
            (
                s
                for s in self.data.slots_on(day)
                if self.data.classes[s.class_group].semester in active
            ),
            key=lambda s: (s.period, s.class_group),
        ):
            p = by_key.get(s.key)
            exchanged = s.key in self.exchange_overrides
            if p is None:
                teacher, status = self.effective_teacher(s), "scheduled"
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
                    "original_teacher": s.teacher if p or exchanged else None,
                    "status": status,
                    "exchanged": exchanged,
                    "proposal": p,
                }
            )
        return rows

    def notices(self, date: str, class_group: str | None = None) -> list[str]:
        out = []
        for p in self.proposals_for(date):
            if class_group is not None and p.class_group != class_group:
                continue
            cls = self.data.classes[p.class_group].name
            subj = (
                self.data.subjects[p.subject].name
                if p.subject in self.data.subjects
                else "Project supervision"
            )
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

    def counts(self, date: str, department: str | None = None) -> dict[str, int]:
        props = self.proposals_for(date, department=department)
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

    # ----- timetable generation ------------------------------------------------

    def semester_window_for(
        self, academic_year: int, semester: str
    ) -> SemesterWindow:
        """The semester window for a draft's year.

        Admin overrides apply only to the store's own academic year; other
        years use default windows.
        """
        if semester not in SEMESTERS:
            raise KeyError(f"unknown semester {semester}")
        if academic_year == self.academic_year:
            return self.semester_windows[semester]
        return default_semester_windows(academic_year)[semester]

    def generate_draft(
        self,
        class_group: str,
        academic_year: int,
        requirements: dict[str, int],
        assignments: dict[str, str] | None = None,
    ) -> GeneratedTimetable:
        """Generate (or regenerate) a draft timetable for a division.

        Never touches the published timetable. An existing draft for the
        same (academic_year, division) is replaced.
        """
        if class_group not in self.data.classes:
            raise KeyError(f"unknown division {class_group}")
        for sid, hours in requirements.items():
            if sid not in self.data.subjects:
                raise KeyError(f"unknown subject {sid}")
            if not isinstance(hours, int) or hours < 0:
                raise ValueError(f"invalid weekly hours for {sid}")
        assignments = assignments or {}
        for tid in assignments.values():
            if tid not in self.data.teachers:
                raise KeyError(f"unknown teacher {tid}")
        slots, violations, warnings = generate(
            self.data, class_group, requirements, assignments
        )
        draft = GeneratedTimetable(
            id=f"TT-{academic_year}-{class_group}",
            academic_year=academic_year,
            class_group=class_group,
            requirements=dict(requirements),
            assignments=dict(assignments),
            slots=slots,
            violations=violations,
            warnings=warnings,
        )
        self.tt_drafts = [d for d in self.tt_drafts if d.id != draft.id]
        self.tt_drafts.append(draft)
        return draft

    def timetable_drafts(self, status: str | None = None) -> list[GeneratedTimetable]:
        return [d for d in self.tt_drafts if status is None or d.status == status]

    def _draft(self, draft_id: str) -> GeneratedTimetable:
        for d in self.tt_drafts:
            if d.id == draft_id:
                return d
        raise KeyError(f"unknown draft {draft_id}")

    def _draft_conflicts(self, draft: GeneratedTimetable) -> list[str]:
        """Faculty/room/division clashes of draft slots against live slots.

        The division's own non-supervision slots are excluded — publishing
        replaces them — but its supervision slots stay occupied.
        """
        cg = draft.class_group
        parity = semester_parity(self.data.classes[cg].semester)
        replaceable = {
            s.key
            for s in self.data.timetable
            if s.class_group == cg and s.subject != SUPERVISION_SUBJECT
        }
        conflicts: list[str] = []
        for s in draft.slots:
            current = self.data.slot_at(s.day, s.period, cg)
            if current is not None and current.key not in replaceable:
                conflicts.append(
                    f"{s.day} P{s.period}: conflicts with a supervision slot"
                )
                continue
            for t in self.data.timetable:
                if (
                    t.day != s.day
                    or t.period != s.period
                    or t.key in replaceable
                ):
                    continue
                sem = self.data.classes[t.class_group].semester
                if sem and sem not in parity:
                    continue
                if self.effective_teacher(t) == s.teacher:
                    conflicts.append(
                        f"{s.day} P{s.period}: faculty {s.teacher} already "
                        f"teaches {t.class_group}"
                    )
                    break
                if t.room == s.room:
                    conflicts.append(
                        f"{s.day} P{s.period}: room {s.room} already used "
                        f"by {t.class_group}"
                    )
                    break
        return conflicts

    def publish_draft(self, draft_id: str, on: str) -> None:
        """Publish a draft: replace the division's non-supervision slots.

        Refuses (ValueError, nothing changed) when the draft's semester
        window is not in session on `on`, blocking violations exist, open
        proposals/exchanges or supervision conflicts would be broken, or
        the draft now conflicts with the live timetable.
        """
        draft = self._draft(draft_id)
        if draft.status != TT_DRAFT:
            raise ValueError(f"draft {draft_id} is not awaiting publication")
        cg = draft.class_group
        semester = self.data.classes[cg].semester
        window = self.semester_window_for(draft.academic_year, semester)
        d = dt.date.fromisoformat(on)
        if not (window.start <= d <= window.end):
            raise ValueError(
                f"{semester} of academic year {draft.academic_year} runs "
                f"{window.start} to {window.end}; it is not in session on "
                f"{on} and cannot be published early"
            )
        blockers = [f"unresolved violation: {v}" for v in draft.violations]
        for p in self.proposals:
            if p.class_group == cg and p.status in (STATUS_PENDING, STATUS_APPROVED):
                blockers.append(f"open substitution proposal {p.id}")
        for x in self.exchanges:
            if x.status in (EXCHANGE_PROPOSED, EXCHANGE_ACCEPTED) and cg in (
                x.proposer_slot[2],
                x.counterparty_slot[2],
            ):
                blockers.append(f"open period exchange {x.id}")
        blockers += self._draft_conflicts(draft)
        if blockers:
            raise ValueError(
                "publication blocked: " + "; ".join(sorted(set(blockers)))
            )
        remaining = [
            s
            for s in self.data.timetable
            if not (s.class_group == cg and s.subject != SUPERVISION_SUBJECT)
        ]
        removed_keys = {
            s.key
            for s in self.data.timetable
            if s.class_group == cg and s.subject != SUPERVISION_SUBJECT
        }
        self.data.timetable[:] = remaining + list(draft.slots)
        for key in removed_keys:
            self.exchange_overrides.pop(key, None)
        draft.status = TT_PUBLISHED

    def discard_draft(self, draft_id: str) -> None:
        """Drop a draft without touching anything else."""
        draft = self._draft(draft_id)
        draft.status = TT_DISCARDED
        self.tt_drafts = [d for d in self.tt_drafts if d.id != draft_id]
