# Campusly

Smart academic scheduling & substitute management for the fictional **Greenfield College** — a six-department engineering college (CSE, ECE, EEE, ME, CE + Basic Science).

Report a faculty absence, get deterministic substitute proposals (subject fit → same department → workload fairness → conflicts), review & approve as a department coordinator, then publish timetable updates, class notices, workload stats, and a CSV export. Faculty can also propose period exchanges that flow through counterparty acceptance and coordinator approval.

## College features

- **Departments & divisions**: five engineering departments each with divisions scoped as `DEPT-Semester-Section` (e.g. `CSE-S3-A`), plus Basic Science service faculty who preferentially teach first-year divisions (cross-department teaching is flagged `‡`).
- **Academic calendar**: semesters S1–S8; odd semesters run Jan–Jun and even semesters Jul–Dec. Only one parity is in session at a time. Admins can override any semester's date range (in-memory, resets on restart).
- **Demo roles** (no sign-in — demo only, not access control): **Admin** sees everything incl. calendar overrides, subject offerings, and project groups; **Department Coordinator** is scoped to one department (absence reporting, substitution and exchange approvals); **Faculty** see their own timetable, project groups, and exchanges; **Student** gets a read-only division view. All roles share one in-memory store.
- **Substitute allocation**: an absence uncovers every slot the faculty teaches across all departments (including supervision meetings); the allocator ranks candidates subject-match → same-department → weekly workload → id, never double-books across departments, and flags cross-department substitutes.
- **Period exchanges**: a faculty member proposes swapping one of their slots for another faculty member's slot → the counterparty accepts/declines → the proposer's department coordinator approves/rejects. Approval re-checks conflicts and atomically swaps both slots (`⇄` in timetable views).
- **Project supervision**: project groups get a weekly supervision slot on the division and supervisor timetables; an absent supervisor is flagged uncovered for manual handling, never auto-substituted.

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

Opens at http://localhost:8501. In the sidebar, pick a **role** (try Admin), a working date (try **2026-10-26**, a Monday — even semesters in session), then **Dashboard → "Load demo scenario"** for a ready-made flow, or drive it manually: **Report Absence → Review Queue → Timetable & Notices → Workload & Export**. Switch to **Department Coordinator** to see a department-scoped queue, or **Faculty → Exchanges** to propose a period swap (accept it as the counterparty faculty, then approve as that department's coordinator). Student view shows a division's weekly timetable, notices, and project groups.

## Run tests

```bash
pytest
```

## Structure

```
campusly/
  models.py   # dataclasses: Department, Teacher, Room, ClassGroup (division),
              # TimetableSlot, Absence, Proposal, Exchange, ProjectGroup
  data.py     # fictional college seed (~55 faculty, 96 divisions, S1–S8 parity
              # timetables) + semester-window calendar
  engine.py   # deterministic greedy allocator (hard constraints + ranked candidates)
  store.py    # shared in-memory state: absences, proposals, exchanges, offerings,
              # project groups, calendar overrides, effective timetable
  export.py   # CSV export
app.py        # Streamlit UI (role-scoped pages)
tests/        # engine + store + college tests (pytest)
```

## Design notes

- **Deterministic**: identical inputs always produce identical proposals (no randomness).
- **Hard constraints**: no double-booked faculty or rooms within a semester parity (odd/even semesters are never in session together); substitutes must be free in that slot and cannot be the absent faculty member.
- **Ranking**: subject-qualified first, then same-department as the division, then lowest weekly substitute workload, then faculty id.
- **Review gate**: the base timetable is immutable — approved substitutions and exchanges layer on top as per-slot overrides; rejected items drop back to *uncovered*.
- **Exchange safety**: proposals that would double-book either participant are refused up front; approval re-validates against substitutions committed meanwhile.
- Spec/planning artifacts live in `openspec/changes/expand-college-wide/` (MVP spec in `openspec/changes/add-campusly-mvp/`).
