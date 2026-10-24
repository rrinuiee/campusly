"""Deterministic greedy substitute allocator.

For each uncovered period (processed in a fixed order):
  1. Filter candidates by hard constraints - teacher must be free in that
     slot, cannot be the absent teacher, cannot already hold a substitution
     in the same slot this run.
  2. Rank survivors: subject-qualified first, then lightest weekly
     substitution workload, then teacher id (stable tie-break).
  3. Assign a room: keep the slot's room if free, else take the first free
     room; if none, the period is flagged uncovered.

No randomness anywhere - identical inputs always yield identical proposals.
"""

from __future__ import annotations

from .data import SchoolData
from .models import STATUS_PENDING, STATUS_UNCOVERED, Proposal, TimetableSlot


def allocate(
    data: SchoolData,
    slots: list[TimetableSlot],
    date: str,
    absent_teachers: set[str],
    workload: dict[str, int],
    taken: dict[tuple[str, int], set[str]],
    taken_rooms: dict[tuple[str, int], set[str]] | None = None,
    start_seq: int = 1,
) -> list[Proposal]:
    """Produce one Proposal per slot.

    `workload` maps teacher id -> substitutions already taken this week;
    it is updated in place as assignments are made. `taken` maps
    (day, period) -> teacher ids already committed as substitutes (this run
    plus earlier pending/approved proposals). `taken_rooms` likewise tracks
    rooms committed by earlier proposals.
    """
    if taken_rooms is None:
        taken_rooms = {}
    proposals: list[Proposal] = []
    seq = start_seq

    for slot in sorted(slots, key=lambda s: (s.period, s.class_group)):
        key = (slot.day, slot.period)
        busy = data.teacher_at(slot.day, slot.period) | taken.get(key, set()) | absent_teachers
        candidates = [
            t for t in data.teachers.values()
            if t.id not in busy and t.id != slot.teacher
        ]
        # Stable ranking: subject match desc, workload asc, id asc.
        candidates.sort(
            key=lambda t: (
                slot.subject not in t.subjects,
                workload.get(t.id, 0),
                t.id,
            )
        )

        warnings: list[str] = []
        substitute = candidates[0].id if candidates else None
        if substitute and slot.subject not in data.teachers[substitute].subjects:
            warnings.append("non-subject-match")

        assigned_room = _pick_room(data, slot, taken_rooms.get(key, set())) if substitute else None
        if substitute and assigned_room != slot.room:
            warnings.append("room-changed")

        if substitute is None:
            warnings.append("no-teacher-available")
        elif assigned_room is None:
            warnings.append("no-room-available")
            substitute = None

        status = STATUS_PENDING if substitute else STATUS_UNCOVERED
        proposals.append(
            Proposal(
                id=f"P-{date}-{seq:03d}",
                date=date,
                day=slot.day,
                period=slot.period,
                class_group=slot.class_group,
                subject=slot.subject,
                absent_teacher=slot.teacher,
                room=slot.room,
                substitute_teacher=substitute,
                assigned_room=assigned_room,
                warnings=warnings,
                status=status,
            )
        )
        seq += 1

        if substitute:
            taken.setdefault(key, set()).add(substitute)
            taken_rooms.setdefault(key, set()).add(assigned_room)
            workload[substitute] = workload.get(substitute, 0) + 1

    return proposals


def _pick_room(data: SchoolData, slot: TimetableSlot, taken: set[str]) -> str | None:
    """Original room unless another proposal took it, else first free room."""
    if slot.room not in taken:
        return slot.room
    occupied = data.room_at(slot.day, slot.period) | taken
    for rid in sorted(data.rooms):
        if rid not in occupied:
            return rid
    return None
