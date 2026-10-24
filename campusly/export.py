"""CSV export of a date's substitution results."""

from __future__ import annotations

import csv
import io

from .models import STATUS_UNCOVERED
from .store import Store

COLUMNS = [
    "date",
    "day",
    "period",
    "class_group",
    "subject",
    "absent_teacher",
    "substitute_teacher",
    "room",
    "status",
    "warnings",
]


def to_csv(store: Store, date: str) -> str:
    """One row per affected period on `date` (pending/approved/uncovered)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for p in store.proposals_for(date):
        w.writerow(
            [
                p.date,
                p.day,
                p.period,
                store.data.classes[p.class_group].name,
                store.data.subjects[p.subject].name,
                store.data.teachers[p.absent_teacher].name,
                (
                    store.data.teachers[p.substitute_teacher].name
                    if p.substitute_teacher
                    else "UNCOVERED"
                ),
                p.assigned_room or p.room,
                p.status,
                ";".join(p.warnings),
            ]
        )
    return buf.getvalue()
