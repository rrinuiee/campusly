# Design

## Context

Greenfield repo — only `openspec/` and docs exist. Constraints: Python + Streamlit, fully local on macOS, no paid APIs, deterministic allocation (spec requirement), ~7h budget. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Layered structure: pure domain/allocation core (testable without Streamlit) + thin UI layer.
- One complete demo flow: seed data → report absence → allocate → review → publish → export.
- Deterministic, unit-testable constraint engine.

**Non-Goals:**
- Real persistence (session state + in-memory store is fine for the demo), auth, multi-date optimization, notifications.

## Decisions

- **Layered package `campusly/`**: `models.py` (dataclasses: Teacher, Room, ClassGroup, TimetableSlot, Absence, Proposal), `data.py` (fictional seed dataset), `engine.py` (allocation), `store.py` (in-memory state + review actions), `export.py` (CSV). UI in `app.py` (Streamlit). Tests in `tests/`. Rationale: engine stays pure and testable; alternative of putting logic inside Streamlit callbacks was rejected as untestable.
- **Greedy deterministic allocator, not an optimizer**: for each uncovered period (sorted by period), filter candidates by hard constraints (free that period, not the absent teacher, not already assigned this run, subject to room free), then rank by score = subject-match (primary) + fewest substitutions this week (tie-break) + teacher id (final deterministic tie-break). Non-subject fallback allowed but flagged; if no candidate, mark uncovered. Rationale: a full CSP/ILP solver adds a heavy dependency and risk for zero demo benefit; greedy per-period with stable ordering is deterministic, explainable, and testable. Constraint satisfaction across same-time periods is preserved by processing periods in fixed order and marking assignments as taken.
- **State model**: proposals are stored `pending` on creation; approval mutates a derived "effective timetable" view, never the seed timetable. Rejected → period stays `uncovered`. Rationale: spec requires no timetable mutation before review; keeping the seed immutable makes the review boundary trivially correct.
- **Streamlit multipage-free single app** with sidebar navigation (Dashboard / Report Absence / Review / Timetable & Notices / Workload / Export) via `st.session_state`. Rationale: fewer files, faster to build, still polished with `st.metric`, `st.dataframe`, `st.data_editor`.
- **Seed data**: ~10 teachers across 6 subjects, ~6 class groups, ~8 rooms, Mon–Fri × 6 periods, subjects as a `set` on Teacher so "qualified" is a membership test — adaptable to colleges (rename ClassGroup → section, add lab flag later).

## Risks / Trade-offs

- [Greedy allocation can leave a period uncovered that a global solver could fill] → Acceptable: spec requires flagging uncovered periods; flagging IS the demo feature.
- [Session state resets on refresh loses demo progress] → Mitigate with a "Load demo scenario" button that replays seed + a sample absence deterministically.
- [No real persistence limits realism] → Documented non-goal; CSV export provides the tangible artifact.
