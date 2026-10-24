# Campusly

Smart academic scheduling & substitute management — hackathon MVP for the fictional **Greenfield High**.

Report a teacher absence, get deterministic substitute proposals (subject fit → workload fairness → conflicts), review & approve as coordinator, then publish timetable updates, class notices, workload stats, and a CSV export.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

Opens at http://localhost:8501. Sidebar: pick a working date (try **2026-10-26**, a Monday), then **Dashboard → "Load demo scenario"** for a ready-made flow, or drive it manually via **Report Absence → Review Queue → Timetable & Notices → Workload & Export**.

## Run tests

```bash
pytest
```

## Structure

```
campusly/
  models.py   # dataclasses: Teacher, Room, ClassGroup, TimetableSlot, Absence, Proposal
  data.py     # fictional seed dataset (12 teachers, 8 subjects, 6 classes, 9 rooms)
  engine.py   # deterministic greedy allocator (hard constraints + ranked candidates)
  store.py    # in-memory state: absences, pending/approved/uncovered, effective timetable
  export.py   # CSV export
app.py        # Streamlit UI (5 pages)
tests/        # engine + store tests (pytest)
```

## Design notes

- **Deterministic**: identical inputs always produce identical proposals (no randomness).
- **Hard constraints**: no double-booked teachers or rooms, substitutes must be free in that slot and cannot be the absent teacher.
- **Ranking**: subject-qualified first, then lowest weekly substitute workload, then teacher id.
- **Review gate**: the base timetable is immutable — approvals layer on top; rejected proposals drop back to *uncovered*.
- Spec/planning artifacts live in `openspec/changes/add-campusly-mvp/`.
