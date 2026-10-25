# Tasks

## 1. Exchange rules

- [x] 1.1 Add `Store._exchange_reasons` collecting every blocker (self-swap, double-booking, supervision slots, open exchange on either slot, missing qualification) and reuse it in `propose_exchange` while preserving existing error messages.
- [x] 1.2 Add `Store.exchange_options(proposer, proposer_slot)` returning eligible counterparty slots and per-slot exclusion reasons for the UI.
- [x] 1.3 Make `approve_exchange` fail cleanly (`ValueError`) when a referenced slot no longer exists.

## 2. Faculty & coordinator UI

- [x] 2.1 Rework the faculty exchange page: pick own slot → eligible-option select with full slot details → propose; show excluded-count feedback.
- [x] 2.2 Show both periods and the next required action on every exchange card (faculty incoming/outgoing/history and coordinator queue).

## 3. Curriculum validation

- [x] 3.1 Guard `default_requirements` against departments with no default curriculum.
- [x] 3.2 Add a sweep test generating for every division (all departments × S1–S8 × sections): exact hours, parity-scoped clash freedom, determinism.
- [x] 3.3 Add exchange regression tests (duplicate, unqualified, supervision, eligible options, stale-slot approval) and rerun the full suite plus strict OpenSpec validation.
