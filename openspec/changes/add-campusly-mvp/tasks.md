# Tasks

## 1. Project setup

- [x] 1.1 Create `campusly/` package, `tests/`, `app.py`, `requirements.txt` (streamlit, pytest); verify `pip install -r requirements.txt` and `pytest --collect-only` succeed
- [x] 1.2 Define domain dataclasses in `campusly/models.py` (Teacher, Room, ClassGroup, TimetableSlot, Absence, Proposal) and verify the module imports cleanly

## 2. Seed data + absence reporting

- [x] 2.1 Implement `campusly/data.py` fictional dataset (≥10 teachers, ≥6 subjects, ≥6 class groups, ≥8 rooms, Mon–Fri × 6-period timetable); verify a load function returns it and every timetable slot references existing ids
- [x] 2.2 Implement absence reporting in `campusly/store.py` (record absence, reject duplicates, derive uncovered periods for the date); verify with pytest covering record/duplicate/zero-class cases

## 3. Allocation engine

- [x] 3.1 Implement `campusly/engine.py` greedy deterministic allocator (hard constraints: free teacher, not absent, no double-booking, free room; score = subject match → workload → teacher id); verify pytest covers subject preference, workload tie-break, no double-booking, room conflict
- [x] 3.2 Add uncovered-flagging and non-subject-match warning on proposals; verify pytest covers flag-when-none-free and identical-output-on-repeat (determinism)

## 4. Review workflow + store

- [x] 4.1 Implement pending/approve/reject in `campusly/store.py` so approval mutates only the effective timetable and rejection keeps the period uncovered; verify pytest covers approve-publishes, reject-keeps-uncovered, pending-not-in-timetable

## 5. Streamlit UI

- [x] 5.1 Build `app.py` dashboard with metric cards (absences, pending, uncovered, approved) and fictional-data sidebar navigation; verify `streamlit run app.py` launches and dashboard renders counts correctly
- [x] 5.2 Add Report Absence page (teacher + date select → shows uncovered periods → runs allocation); verify an absence produces the expected pending proposals in-session
- [x] 5.3 Add Review page (pending list with warnings, approve/reject buttons); verify approve/reject updates state and timetable view
- [x] 5.4 Add Timetable & Notices page (effective timetable grid for selected date, uncovered flags, per-class notices); verify approved subs appear and uncovered periods are marked
- [x] 5.5 Add Workload page + `campusly/export.py` CSV download covering approved/pending/uncovered rows; verify CSV parses and contains one row per affected period

## 6. Verification

- [x] 6.1 Run `pytest` — all tests pass; run the app end-to-end through the full demo flow once
- [x] 6.2 Add a brief `README.md` with run instructions (`streamlit run app.py`, `pytest`) and verify commands work as written

## Workflow follow-up

- Archive the change after review requirements are satisfied (`openspec archive add-campusly-mvp`).
- Verify the archived result with `openspec list` / `openspec list --specs`.
