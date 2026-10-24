# Design

## Context

The college model already has every lookup a generator needs: parity-scoped `teacher_at` / `room_at` / `slot_at` on `SchoolData`, qualified-subject sets on `Teacher`, department ownership on `Subject`/`Teacher`, and a deterministic bipartite matcher (`data._match`) plus a weekly subject mix (`data._week_mix`) inside the seed builder. What's missing is a curriculum input (weekly hours per subject per division), a draft lifecycle scoped to a future academic year, and a publish path that safely replaces a division's slots.

A single `SchoolData.timetable` holds all published slots; there is no per-year timetable. That is deliberate: only one semester parity is ever in session, and publication is gated on the draft's semester window, so a future draft simply cannot go live early.

## Goals / Non-Goals

**Goals:**

- Deterministic draft generation for one (academic_year, division) at a time, with mandatory-constraint violations reported instead of hidden.
- Draft → published/discarded lifecycle that never mutates the published timetable until publish, revalidates at publish time, and refuses early publication.
- Editable curriculum defaults derived from the same department mix the seed uses.

**Non-Goals:**

- Multi-division or college-wide batch generation; global optimization; teacher preferences or load caps.
- Persistence (all state stays in-memory, matching the existing store).
- Full curriculum management UI (hour editing + optional per-subject faculty pin only).

## Decisions

- **Reusable `campusly/generator.py`**, modeled on `data._build_timetable`: expand requirements into per-subject hour placement, spread each subject's hours across days (round-robin preferred day → fallback days), and pick faculty per slot with the existing ranking style — pinned assignment first, then same-department, then lowest weekly load (existing + generated), then id. Deterministic iteration everywhere.
- **Occupancy excludes the division's own replaceable slots**: when generating for division D, D's existing non-supervision slots are treated as free (they will be replaced on publish); D's supervision slots stay occupied as fixed constraints; every other division's slots in the parity are hard occupied.
- **Draft model**: `GeneratedTimetable(id, academic_year, class_group, requirements, assignments, slots, violations, warnings, status)` with lifecycle constants `DRAFT/PUBLISHED/DISCARDED`. `violations` are blocking; `warnings` are advisory (e.g., lab placed non-consecutively, cross-department teacher).
- **Publication semantics**: publish (a) requires the working date inside the draft's semester window — store windows when the draft's year equals the store's academic year, default windows for other years; (b) refuses when blocking violations exist; (c) refuses when the division has pending/approved proposals, open exchanges, or a supervision-slot conflict introduced since generation; (d) revalidates every draft slot's faculty/room/division conflicts against the live parity timetable; then (e) atomically removes the division's non-supervision slots and inserts the draft slots, dropping now-stale exchange overrides for removed keys.
- **Lab support is data-driven**: additive `Room.kind` (default `"classroom"`) and `Subject.room_kind` (default `""`) fields; the seed types `LAB-*` rooms as `"lab"` and `GYM` as `"gym"`. A subject with `room_kind` set is only placed in a matching free room; lab subjects are placed in consecutive same-day blocks when possible, otherwise placed normally with a warning. Where no kind data exists, behavior is unchanged.
- **Curriculum source**: `data.default_requirements(department)` returns `{subject_id: weekly_hours}` factored out of `_week_mix`, so the seed and the generator share one curriculum definition. Admin edits produce the same shape, optionally with `subject → teacher` pins.
- **Alternatives considered**: a CP-SAT/ILP dependency (rejected — new dependency, overkill for V1 and the deterministic match already proves adequate); per-year timetable copies (rejected — doubles state for no benefit while parity + publish-gating already isolate years); silently dropping unplaceable hours (rejected — violates the explicit reporting requirement).

## Risks / Trade-offs

- Greedy placement can leave an hour unplaceable even when a different arrangement would fit → accepted: the hour becomes a reported violation, not a silent drop; re-running with edited hours or a faculty pin resolves it.
- Blocking publication on open proposals/exchanges can surprise an admin mid-semester → accepted: the block is reported with reasons, and publishing a future-year draft is unusual mid-activity anyway.
- Seed data marks no subject as lab-required → lab code paths are exercised by tests and by admin-created data, not by the default dataset; documented as a limitation.
