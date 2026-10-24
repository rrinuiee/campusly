"""Campusly — smart substitute scheduling. Streamlit UI over the campusly core.

Run: streamlit run app.py

Demo roles (no sign-in): Admin, Department Coordinator, Faculty, Student.
All roles share one in-memory store, so an action under one role is
immediately visible under the others.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from campusly.data import (
    SEMESTERS,
    day_name,
    default_requirements,
    load_seed_data,
    semester_parity,
)
from campusly.export import to_csv
from campusly.models import (
    DAYS,
    EXCHANGE_ACCEPTED,
    EXCHANGE_PROPOSED,
    PERIOD_TIMES,
    PERIODS,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_UNCOVERED,
    SUPERVISION_SUBJECT,
    TT_DRAFT,
    Proposal,
)
from campusly.store import DuplicateAbsenceError, Store

DEMO_DATE = dt.date(2026, 10, 26)  # a Monday

ROLE_ADMIN = "Admin"
ROLE_COORD = "Department Coordinator"
ROLE_FACULTY = "Faculty"
ROLE_STUDENT = "Student"
ROLES = [ROLE_ADMIN, ROLE_COORD, ROLE_FACULTY, ROLE_STUDENT]

ROLE_PAGES = {
    ROLE_ADMIN: [
        "Dashboard",
        "Report Absence",
        "Review Queue",
        "Timetable & Notices",
        "Workload & Export",
        "Administration",
    ],
    ROLE_COORD: [
        "Dashboard",
        "Report Absence",
        "Review Queue",
        "Exchanges",
        "Timetable & Notices",
        "Workload & Export",
    ],
    ROLE_FACULTY: ["My Timetable", "Exchanges"],
    ROLE_STUDENT: ["My Timetable"],
}

st.set_page_config(
    page_title="Campusly",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
<style>
  .hero {
    background: linear-gradient(100deg, #0B2545 0%, #0E7C7B 100%);
    color: #fff; border-radius: 14px; padding: 22px 28px; margin-bottom: 1.2rem;
  }
  .hero h1 { color: #fff; margin: 0; font-size: 1.7rem; }
  .hero p  { color: #cfeeea; margin: 4px 0 0 0; font-size: .95rem; }
  .stat-card {
    background: #fff; border: 1px solid #e3ebf2; border-radius: 12px;
    padding: 14px 18px; box-shadow: 0 1px 3px rgba(11,37,69,.10);
    border-left: 6px solid var(--accent, #0E7C7B); margin-bottom: .6rem;
  }
  .stat-label { color: #5b7290; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
  .stat-value { color: #0B2545; font-size: 1.9rem; font-weight: 800; line-height: 1.15; }
  .stat-hint  { color: #8aa0b8; font-size: .76rem; }
  .chip {
    display: inline-block; border-radius: 999px; padding: 2px 10px;
    font-size: .74rem; font-weight: 600; margin-left: 6px; vertical-align: middle;
  }
  .chip-green { background: #dcfce7; color: #166534; }
  .chip-amber { background: #fef3c7; color: #92400e; }
  .chip-red   { background: #fee2e2; color: #991b1b; }
  .chip-blue  { background: #dbeafe; color: #1e40af; }
  .section-note { color: #5b7290; font-size: .88rem; margin-top: -0.6rem; }
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------- helpers


@st.cache_resource
def get_store() -> Store:
    """One shared store for the whole app process — all sessions/roles see
    the same data. In-memory only; resets on restart."""
    return Store(load_seed_data())


def tname(store: Store, tid: str | None) -> str:
    return store.data.teachers[tid].name if tid else "—"


def cname(store: Store, cid: str) -> str:
    return store.data.classes[cid].name


def dname(store: Store, did: str) -> str:
    dept = store.data.departments.get(did)
    return dept.name if dept else did


def sname(store: Store, sid: str) -> str:
    if sid == SUPERVISION_SUBJECT:
        return "Project supervision"
    subj = store.data.subjects.get(sid)
    return subj.name if subj else sid.replace("-", " ").title()


def goto(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def stat_card(col, label: str, value, hint: str, color: str) -> None:
    col.markdown(
        f"""<div class="stat-card" style="--accent:{color}">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
        <div class="stat-hint">{hint}</div></div>""",
        unsafe_allow_html=True,
    )


def chips_for(p: Proposal, store: Store) -> str:
    """HTML chips describing suitability/warnings for a proposal."""
    out = []
    if p.substitute_teacher:
        qualified = p.subject in store.data.teachers[p.substitute_teacher].subjects
        out.append(
            '<span class="chip chip-green">subject match</span>'
            if qualified
            else '<span class="chip chip-amber">non-subject match</span>'
        )
    if "cross-department" in p.warnings:
        out.append('<span class="chip chip-amber">cross-department</span>')
    if "room-changed" in p.warnings:
        out.append('<span class="chip chip-blue">room changed</span>')
    if "supervision-manual-handling" in p.warnings:
        out.append('<span class="chip chip-blue">manual handling</span>')
    if p.status == STATUS_UNCOVERED or not p.substitute_teacher:
        out.append('<span class="chip chip-red">uncovered</span>')
    return "".join(out)


def proposal_df(store: Store, props: list[Proposal]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Period": f"P{p.period} ({PERIOD_TIMES[p.period]})",
                "Division": cname(store, p.class_group),
                "Subject": sname(store, p.subject),
                "Absent": tname(store, p.absent_teacher),
                "Substitute": tname(store, p.substitute_teacher),
                "Room": p.assigned_room or p.room,
                "Status": p.status,
                "Flags": ", ".join(p.warnings) or "—",
            }
            for p in props
        ]
    )


def week_grid(cells: dict[tuple[str, int], str]) -> pd.DataFrame:
    """Day x period grid from a {(day, period): text} mapping."""
    return pd.DataFrame(
        {day: [cells.get((day, p), "—") for p in PERIODS] for day in DAYS},
        index=[f"P{p} ({PERIOD_TIMES[p]})" for p in PERIODS],
    )


def active_divisions(store: Store, iso: str) -> list[str]:
    """Division ids whose semester is in session on the working date."""
    active = set(store.active_semesters(iso))
    return sorted(
        cid
        for cid, c in store.data.classes.items()
        if not c.semester or c.semester in active
    )


def divisions_of(store: Store, department: str, semester: str) -> list[str]:
    return sorted(
        cid
        for cid, c in store.data.classes.items()
        if c.department == department and c.semester == semester
    )


def day_overlay(store: Store, iso: str) -> dict[tuple[str, int, str], Proposal]:
    return {(p.day, p.period, p.class_group): p for p in store.proposals_for(iso)}


def slot_cell(store: Store, slot, perspective: str = "division") -> str:
    """Cell text for a base/effective timetable slot (no date overlay)."""
    if slot.subject == SUPERVISION_SUBJECT:
        text = f"Supervision · {slot.class_group} · {slot.room}"
    elif perspective == "faculty":
        text = f"{sname(store, slot.subject)} · {slot.class_group}"
    else:
        text = f"{sname(store, slot.subject)} · {tname(store, store.effective_teacher(slot))}"
    if store.cross_department(slot):
        text += " ‡"
    if slot.key in store.exchange_overrides:
        text += " ⇄"
    return text


def overlay_cell(
    store: Store, slot, p: Proposal | None, perspective: str = "division"
) -> str:
    """Cell text for a slot on the working date incl. proposal overlay."""
    base = slot_cell(store, slot, perspective)
    if p is None:
        return base
    if p.status == STATUS_APPROVED:
        return f"{sname(store, p.subject)} · {tname(store, p.substitute_teacher)} (sub)"
    return f"{sname(store, p.subject)} · {p.status.upper()}"


def style_grid_cell(v: str) -> str:
    if "UNCOVERED" in v:
        return "background-color: #991b1b; color: white; font-weight: 600"
    if "PENDING" in v:
        return "background-color: #b45309; color: white"
    if "(sub)" in v:
        return "background-color: #0E7C7B; color: white; font-weight: 600"
    return ""


def slot_label(store: Store, slot) -> str:
    return (
        f"{slot.day} P{slot.period} ({PERIOD_TIMES[slot.period]}) · "
        f"{slot.class_group} · {sname(store, slot.subject)} · "
        f"{tname(store, store.effective_teacher(slot))}"
    )


def exchange_label(store: Store, x) -> str:
    sa = store.data.slot_at(*x.proposer_slot)
    sb = store.data.slot_at(*x.counterparty_slot)
    return (
        f"{x.id}: {tname(store, x.proposer)} offers {slot_label(store, sa)} "
        f"⇄ {tname(store, x.counterparty)}'s {slot_label(store, sb)}"
    )


def projects_df(store: Store, projects) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Group": p.id,
                "Title": p.title,
                "Division": p.class_group,
                "Supervisor": tname(store, p.supervisor),
                "Meeting": f"{p.day} P{p.period} · {p.room}",
            }
            for p in projects
        ]
    )


# ----------------------------------------------------------------------------- pages


def page_dashboard(store: Store, date: dt.date, ctx: dict) -> None:
    st.markdown(
        '<div class="hero"><h1>Campusly</h1>'
        "<p>Smart substitute scheduling · Greenfield College (fictional data)</p></div>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    dept = ctx.get("dept")
    c = store.counts(iso, department=dept)
    scope = f" in {dname(store, dept)}" if dept else ""

    cols = st.columns(4)
    stat_card(cols[0], "Absences", c["absences"], "faculty out today", "#0B2545")
    stat_card(
        cols[1], "Pending review", c["pending"], f"awaiting approval{scope}", "#d97706"
    )
    stat_card(cols[2], "Approved", c["approved"], "published to timetable", "#0E7C7B")
    stat_card(cols[3], "Uncovered", c["uncovered"], "need manual handling", "#dc2626")

    st.caption(
        "Semesters in session on this date: "
        + ", ".join(store.active_semesters(iso) or ["none"])
    )
    st.write("")
    if c["uncovered"]:
        st.error(
            f"{c['uncovered']} class(es) still have no substitute{scope}. "
            "Open the Review Queue to handle them."
        )
    elif c["pending"]:
        st.warning(f"{c['pending']} substitute proposal(s) are waiting for approval{scope}.")
    elif c["absences"]:
        st.success("All affected classes are covered. Nothing left to review.")

    st.subheader("Quick actions")
    q1, q2, q3 = st.columns(3)
    if q1.button("Report Absence", width="stretch"):
        goto("Report Absence")
    if q2.button("Review Substitutes", width="stretch"):
        goto("Review Queue")
    if q3.button("View Timetable", width="stretch"):
        goto("Timetable & Notices")

    st.write("")
    left, right = st.columns(2)
    with left:
        st.subheader("Absences")
        st.caption("Faculty reported absent on the selected date")
        rows = [
            {
                "Faculty": tname(store, a.teacher),
                "Department": dname(store, store.data.teachers[a.teacher].department),
                "Date": a.date,
                "Periods affected": len(store.uncovered_slots(a)),
            }
            for a in store.absences
            if a.date == iso
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.info("No absences reported for this date.")

    with right:
        st.subheader("Activity")
        st.caption(f"Substitute proposals for the selected date{scope}")
        props = store.proposals_for(iso, department=dept)
        if props:
            st.dataframe(
                proposal_df(store, props)[
                    ["Period", "Division", "Subject", "Substitute", "Status", "Flags"]
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No substitution activity yet.")

    st.divider()
    st.caption(
        "Demo shortcut — creates two absences on the selected date and runs "
        "the allocation engine so you can try the full review flow."
    )
    if st.button("Load demo scenario (2 absences)"):
        day = day_name(iso)
        if day is None:
            st.error("Pick a weekday — college is closed on weekends.")
        else:
            active = set(store.active_semesters(iso))
            busy = {a.teacher for a in store.absences if a.date == iso}
            picks = [
                s.teacher
                for s in store.data.slots_on(day)
                if s.teacher not in busy
                and store.data.classes[s.class_group].semester in active
                and (
                    ctx["role"] != ROLE_COORD
                    or store.data.teachers[s.teacher].department == ctx["dept"]
                )
            ][:2]
            for tid in dict.fromkeys(picks):
                try:
                    store.report_absence(
                        tid, iso, reporter_department=dept if ctx["role"] == ROLE_COORD else None
                    )
                except (DuplicateAbsenceError, PermissionError):
                    pass
            store.run_allocation(iso)
            st.toast("Demo scenario loaded — proposals ready for review.")
            st.rerun()


def page_absence(store: Store, date: dt.date, ctx: dict) -> None:
    st.title("Report Faculty Absence")
    st.markdown(
        '<p class="section-note">Pick a faculty member to see their classes on '
        "the selected day, then report the absence — Campusly immediately finds "
        "substitutes and sends proposals to the Review Queue.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    day = day_name(iso)
    if day is None:
        st.warning("Selected date is a weekend — college is closed. Pick a weekday in the sidebar.")
        return

    # Coordinators may only report absences for their own department's faculty.
    dept = ctx.get("dept") if ctx["role"] == ROLE_COORD else None
    teachers = sorted(
        (
            t
            for t in store.data.teachers.values()
            if dept is None or t.department == dept
        ),
        key=lambda t: t.name,
    )
    options = {f"{t.name} ({t.id} · {dname(store, t.department)})": t.id for t in teachers}
    absent_on_date = {a.teacher for a in store.absences if a.date == iso}
    active = set(store.active_semesters(iso))

    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.selectbox("Faculty member", list(options))
    tid = options[name]
    day_slots = [
        s
        for s in store.data.slots_on(day)
        if store.effective_teacher(s) == tid
        and store.data.classes[s.class_group].semester in active
    ]
    with col2:
        st.metric("Classes that day", len(day_slots))

    already = tid in absent_on_date
    if already:
        st.info(f"{name} is already marked absent on {iso}.")

    st.subheader(f"{name}'s schedule — {day}")
    if day_slots:
        st.dataframe(
            pd.DataFrame(
                {
                    "Period": [f"P{s.period} ({PERIOD_TIMES[s.period]})" for s in day_slots],
                    "Division": [cname(store, s.class_group) for s in day_slots],
                    "Subject": [sname(store, s.subject) for s in day_slots],
                    "Room": [s.room for s in day_slots],
                }
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info(f"{name} has no in-session classes on {day}.")

    if st.button("Report absence & find substitutes", type="primary", disabled=already):
        try:
            absence = store.report_absence(tid, iso, reporter_department=dept)
        except DuplicateAbsenceError:
            st.error(f"{name} is already marked absent on {iso}.")
            return
        except PermissionError as e:
            st.error(str(e))
            return
        affected = store.uncovered_slots(absence)
        props = store.run_allocation(iso)
        st.session_state["last_report"] = {"teacher": name, "date": iso}
        if not affected:
            st.success(f"Absence recorded. {name} has no classes to cover on {day}.")
        else:
            assigned = sum(1 for p in props if p.status == STATUS_PENDING)
            st.success(
                f"Absence recorded — {len(affected)} class(es) affected: "
                f"{assigned} substitute(s) proposed, "
                f"{len(affected) - assigned} uncovered. Sent to Review Queue."
            )
            st.subheader("Affected classes")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Period": [f"P{s.period} ({PERIOD_TIMES[s.period]})" for s in affected],
                        "Division": [cname(store, s.class_group) for s in affected],
                        "Subject": [sname(store, s.subject) for s in affected],
                        "Room": [s.room for s in affected],
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            st.subheader("Proposed substitutes")
            st.dataframe(proposal_df(store, props), hide_index=True, width="stretch")
            st.caption("Approve or adjust these in the Review Queue.")


def page_review(store: Store, date: dt.date, ctx: dict) -> None:
    dept = ctx.get("dept") if ctx["role"] == ROLE_COORD else None
    st.title("Review Queue" + (f" — {dname(store, dept)}" if dept else ""))
    st.markdown(
        '<p class="section-note">Nothing changes in the timetable until you '
        "approve a proposal. Rejecting leaves the class flagged uncovered.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    load = store.workload(iso)
    props = store.proposals_for(iso, department=dept)
    pending = [p for p in props if p.status == STATUS_PENDING]
    uncovered = [p for p in props if p.status == STATUS_UNCOVERED]
    approved = [p for p in props if p.status == STATUS_APPROVED]

    if not pending and not uncovered and not approved:
        st.info("Nothing to review for this date. Report an absence first.")
        return

    if pending:
        st.subheader(f"Awaiting your decision ({len(pending)})")
    for p in pending:
        with st.container(border=True):
            head, mid = st.columns([3, 1])
            head.markdown(
                f"**{cname(store, p.class_group)} · P{p.period} "
                f"({PERIOD_TIMES[p.period]}) · {sname(store, p.subject)}**"
                f"{chips_for(p, store)}",
                unsafe_allow_html=True,
            )
            head.caption(
                f"{tname(store, p.absent_teacher)} (absent) → "
                f"**{tname(store, p.substitute_teacher)}** · "
                f"Room {p.assigned_room or p.room} · "
                f"{load.get(p.substitute_teacher, 0)} sub period(s) this week"
            )
            if st.session_state.get("confirm_reject") == p.id:
                mid.caption("Leave uncovered?")
                if mid.button("Yes, reject", key=f"rej-y-{p.id}"):
                    store.reject(p.id, department=dept)
                    st.session_state.pop("confirm_reject", None)
                    st.toast("Rejected — class flagged uncovered.")
                    st.rerun()
                if mid.button("Cancel", key=f"rej-n-{p.id}"):
                    st.session_state.pop("confirm_reject", None)
                    st.rerun()
            else:
                if mid.button("Approve", key=f"ok-{p.id}", type="primary"):
                    store.approve(p.id, department=dept)
                    st.toast("Approved — timetable updated.")
                    st.rerun()
                if mid.button("Reject", key=f"no-{p.id}"):
                    st.session_state["confirm_reject"] = p.id
                    st.rerun()

    if uncovered:
        st.subheader(f"Uncovered — needs manual handling ({len(uncovered)})")
        for p in uncovered:
            if "supervision-manual-handling" in p.warnings:
                reason = "supervision — assign manually"
            elif "no-teacher-available" in p.warnings:
                reason = "no free faculty"
            else:
                reason = "rejected"
            with st.container(border=True):
                st.markdown(
                    f"**{cname(store, p.class_group)} · P{p.period} "
                    f"({PERIOD_TIMES[p.period]}) · {sname(store, p.subject)}**"
                    f'<span class="chip chip-red">uncovered · {reason}</span>',
                    unsafe_allow_html=True,
                )
                st.caption(f"Absent: {tname(store, p.absent_teacher)} · Room {p.room}")

    if approved:
        st.subheader(f"Approved ({len(approved)})")
        for p in approved:
            st.success(
                f"{cname(store, p.class_group)} · P{p.period} {sname(store, p.subject)} — "
                f"{tname(store, p.substitute_teacher)} covering for "
                f"{tname(store, p.absent_teacher)} (Room {p.assigned_room or p.room})"
            )


def page_exchanges(store: Store, date: dt.date, ctx: dict) -> None:
    if ctx["role"] == ROLE_FACULTY:
        page_exchanges_faculty(store, date, ctx)
    else:
        page_exchanges_coordinator(store, date, ctx)


def page_exchanges_faculty(store: Store, date: dt.date, ctx: dict) -> None:
    me = ctx["faculty_id"]
    st.title("Period Exchanges")
    st.markdown(
        '<p class="section-note">Propose a swap of one of your scheduled '
        "periods for another faculty member's period. The swap only applies "
        "after the counterparty accepts and your department coordinator "
        "approves.</p>",
        unsafe_allow_html=True,
    )
    active = set(store.active_semesters(date.isoformat()))
    my_slots = sorted(
        (
            s
            for s in store.teacher_slots(me)
            if store.data.classes[s.class_group].semester in active
        ),
        key=lambda s: (DAYS.index(s.day), s.period, s.class_group),
    )
    if not my_slots:
        st.info("You have no in-session teaching slots on this date.")
        return

    st.subheader("Propose an exchange")
    own = st.selectbox(
        "Your slot", my_slots, format_func=lambda s: slot_label(store, s)
    )
    own_parity = semester_parity(store.data.classes[own.class_group].semester)
    counterparty_slots = sorted(
        (
            s
            for s in store.data.timetable
            if store.effective_teacher(s) != me
            and s.key not in store.exchange_overrides
            and store.data.classes[s.class_group].semester in own_parity
        ),
        key=lambda s: (DAYS.index(s.day), s.period, s.class_group),
    )
    other = st.selectbox(
        "Slot to swap for",
        counterparty_slots,
        format_func=lambda s: slot_label(store, s),
    )
    if st.button("Propose exchange", type="primary"):
        try:
            x = store.propose_exchange(me, own.key, other.key)
        except (KeyError, ValueError) as e:
            st.error(f"Proposal refused: {e}")
        else:
            st.toast(f"{x.id} sent to {tname(store, x.counterparty)}.")
            st.rerun()

    mine = store.exchanges_for(me)
    incoming = [x for x in mine if x.counterparty == me and x.status == EXCHANGE_PROPOSED]
    outgoing = [x for x in mine if x.proposer == me]
    answered = [x for x in mine if x.counterparty == me and x.status != EXCHANGE_PROPOSED]

    if incoming:
        st.subheader(f"Requests for you ({len(incoming)})")
        for x in incoming:
            with st.container(border=True):
                st.markdown(exchange_label(store, x))
                c1, c2 = st.columns(2)
                if c1.button("Accept", key=f"x-acc-{x.id}", type="primary"):
                    store.respond_exchange(x.id, accept=True, actor=me)
                    st.toast("Accepted — sent to the department coordinator.")
                    st.rerun()
                if c2.button("Decline", key=f"x-dec-{x.id}"):
                    store.respond_exchange(x.id, accept=False, actor=me)
                    st.toast("Declined.")
                    st.rerun()

    if outgoing:
        st.subheader("Your proposals")
        for x in sorted(outgoing, key=lambda x: x.id):
            with st.container(border=True):
                st.markdown(exchange_label(store, x) + f" — **{x.status}**")
                if x.warnings:
                    st.warning("; ".join(x.warnings))
                if x.status == EXCHANGE_PROPOSED:
                    if st.button("Cancel proposal", key=f"x-can-{x.id}"):
                        store.cancel_exchange(x.id, actor=me)
                        st.toast("Cancelled.")
                        st.rerun()

    if answered:
        st.subheader("Requests you answered")
        for x in answered:
            st.caption(exchange_label(store, x) + f" — {x.status}")

    if not incoming and not outgoing and not answered:
        st.info("No exchanges yet — propose one above.")


def page_exchanges_coordinator(store: Store, date: dt.date, ctx: dict) -> None:
    dept = ctx["dept"]
    st.title(f"Exchange Approvals — {dname(store, dept)}")
    st.markdown(
        '<p class="section-note">Accepted exchanges proposed by your '
        "department's faculty. Approval swaps both periods atomically; "
        "conflicts introduced since the proposal are re-checked.</p>",
        unsafe_allow_html=True,
    )
    pending = store.pending_exchanges(department=dept)
    if pending:
        st.subheader(f"Awaiting your decision ({len(pending)})")
        for x in pending:
            with st.container(border=True):
                st.markdown(exchange_label(store, x))
                if x.warnings:
                    st.warning("; ".join(x.warnings))
                c1, c2 = st.columns(2)
                if c1.button("Approve swap", key=f"x-ok-{x.id}", type="primary"):
                    try:
                        store.approve_exchange(x.id, department=dept)
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        st.toast("Approved — both timetables updated.")
                        st.rerun()
                if c2.button("Reject", key=f"x-no-{x.id}"):
                    store.reject_exchange(x.id, department=dept)
                    st.toast("Rejected — timetables unchanged.")
                    st.rerun()
    else:
        st.info("No accepted exchanges awaiting approval.")

    history = [
        x
        for x in store.exchanges
        if store.data.teachers[x.proposer].department == dept
        and x.status != EXCHANGE_ACCEPTED
    ]
    if history:
        st.subheader("Department exchange history")
        for x in history:
            st.caption(exchange_label(store, x) + f" — {x.status}")


def page_timetable(store: Store, date: dt.date, ctx: dict) -> None:
    st.title("Timetable & Notices")
    st.markdown(
        '<p class="section-note">The published timetable for the selected day. '
        "Substitutions appear only after approval; ⇄ marks applied exchanges, "
        "‡ marks cross-department teaching.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    day = day_name(iso)
    if day is None:
        st.warning("Selected date is a weekend — college is closed. Pick a weekday in the sidebar.")
        return

    dept_ids = sorted(
        {c.department for c in store.data.classes.values()}
        if ctx["role"] == ROLE_ADMIN
        else {ctx["dept"]}
    )
    c1, c2 = st.columns(2)
    department = c1.selectbox(
        "Department", dept_ids, format_func=lambda d: dname(store, d)
    )
    semesters = sorted(
        {c.semester for c in store.data.classes.values() if c.department == department}
    )
    active = store.active_semesters(iso)
    semester = c2.selectbox(
        "Semester",
        semesters,
        index=semesters.index(active[0]) if active and active[0] in semesters else 0,
    )
    all_divisions = divisions_of(store, department, semester)
    if semester not in active:
        st.warning(f"Semester {semester} is not in session on {iso}.")
    picked = st.multiselect("Divisions", all_divisions, default=all_divisions)

    rows = store.effective_timetable(iso)
    grid = {c: {} for c in all_divisions}
    for r in rows:
        if r["class_group"] not in grid:
            continue
        subj = sname(store, r["subject"])
        slot = store.data.slot_at(r["day"], r["period"], r["class_group"])
        marker = " ‡" if slot and store.cross_department(slot) else ""
        marker += " ⇄" if r["exchanged"] else ""
        if r["status"] == "approved":
            cell = f"{subj} · {tname(store, r['teacher'])} (sub)"
        elif r["status"] in (STATUS_PENDING, STATUS_UNCOVERED):
            cell = f"{subj} · {r['status'].upper()}"
        else:
            cell = f"{subj} · {tname(store, r['teacher'])}{marker}"
        grid[r["class_group"]][r["period"]] = cell

    if not picked:
        st.info("Select at least one division to view the timetable.")
    else:
        df = pd.DataFrame(
            {
                f"P{p} ({PERIOD_TIMES[p]})": [grid[cid].get(p, "—") for cid in picked]
                for p in PERIODS
            },
            index=picked,
        ).T

        st.subheader(f"Effective timetable — {day}, {iso}")
        st.dataframe(df.style.map(style_grid_cell), width="stretch")
        st.caption(
            "Teal = approved substitute · Amber = awaiting review · "
            "Red = uncovered · ‡ cross-department · ⇄ exchanged"
        )

    notices = [n for cid in picked for n in store.notices(iso, class_group=cid)]
    st.subheader("Notices for affected classes")
    if notices:
        for n in notices:
            mark = ":red[●]" if "NO substitute" in n else ":green[●]"
            st.markdown(f"{mark} {n}")
    else:
        st.info("No notices for this date.")


def page_my_timetable(store: Store, date: dt.date, ctx: dict) -> None:
    if ctx["role"] == ROLE_FACULTY:
        page_faculty_timetable(store, date, ctx)
    else:
        page_student_timetable(store, date, ctx)


def page_faculty_timetable(store: Store, date: dt.date, ctx: dict) -> None:
    me = ctx["faculty_id"]
    st.title(f"My Timetable — {tname(store, me)}")
    st.caption(
        f"{dname(store, store.data.teachers[me].department)} · "
        "weekly view for the semesters in session on the working date"
    )
    iso = date.isoformat()
    day = day_name(iso)
    active = set(store.active_semesters(iso))
    overlay = day_overlay(store, iso)
    my_props = store.proposals_for(iso)

    cells = {}
    for s in store.teacher_slots(me):
        if store.data.classes[s.class_group].semester not in active:
            continue
        p = overlay.get(s.key) if s.day == day else None
        cells[(s.day, s.period)] = overlay_cell(store, s, p, "faculty")

    st.subheader("Weekly timetable")
    st.dataframe(week_grid(cells).style.map(style_grid_cell), width="stretch")
    st.caption("‡ cross-department · ⇄ exchanged · overlays shown for the working date")

    covering = [
        p for p in my_props
        if p.status == STATUS_APPROVED and p.substitute_teacher == me
    ]
    if covering:
        st.subheader(f"Covering on {day}, {iso}")
        for p in covering:
            st.success(
                f"P{p.period} · {cname(store, p.class_group)} · "
                f"{sname(store, p.subject)} — covering for "
                f"{tname(store, p.absent_teacher)} (Room {p.assigned_room or p.room})"
            )

    projects = [p for p in store.projects if p.supervisor == me]
    if projects:
        st.subheader("Project groups I supervise")
        st.dataframe(projects_df(store, projects), hide_index=True, width="stretch")


def page_student_timetable(store: Store, date: dt.date, ctx: dict) -> None:
    div = ctx["division"]
    st.title(f"My Timetable — {div} (read-only)")
    iso = date.isoformat()
    day = day_name(iso)
    overlay = day_overlay(store, iso)

    cells = {}
    for d in DAYS:
        for p_ in PERIODS:
            s = store.data.slot_at(d, p_, div)
            if s is None:
                continue
            prop = overlay.get(s.key) if d == day else None
            cells[(d, p_)] = overlay_cell(store, s, prop)

    st.subheader("Weekly timetable")
    st.dataframe(week_grid(cells).style.map(style_grid_cell), width="stretch")
    st.caption("‡ cross-department · ⇄ exchanged · overlays shown for the working date")

    notices = store.notices(iso, class_group=div)
    st.subheader("Class notices")
    if notices:
        for n in notices:
            mark = ":red[●]" if "NO substitute" in n else ":green[●]"
            st.markdown(f"{mark} {n}")
    else:
        st.info("No notices for this date.")

    projects = [p for p in store.projects if p.class_group == div]
    if projects:
        st.subheader("Project groups")
        st.dataframe(projects_df(store, projects), hide_index=True, width="stretch")


def page_admin(store: Store, date: dt.date, ctx: dict) -> None:
    st.title("Administration")
    iso = date.isoformat()
    tab_cal, tab_off, tab_gen, tab_dir = st.tabs(
        [
            "Semester calendar",
            "Subject offerings & projects",
            "Generate timetable",
            "Departments & faculty",
        ]
    )

    with tab_cal:
        st.subheader("Semester windows")
        st.caption(
            "Defaults: odd semesters Jan–Jun, even semesters Jul–Dec. "
            "Overrides are in-memory and reset on restart."
        )
        rows = [
            {
                "Semester": s,
                "Start": w.start.isoformat(),
                "End": w.end.isoformat(),
                "Active on working date": s in store.active_semesters(iso),
            }
            for s, w in sorted(store.semester_windows.items())
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        c1, c2, c3 = st.columns(3)
        sem = c1.selectbox("Semester", SEMESTERS, key="ovr-sem")
        cur = store.semester_windows[sem]
        start = c2.date_input("Start", value=cur.start, key="ovr-start")
        end = c3.date_input("End", value=cur.end, key="ovr-end")
        if st.button("Apply override"):
            try:
                store.override_semester_window(sem, start, end)
            except ValueError as e:
                st.error(str(e))
            else:
                st.toast(f"{sem} window updated.")
                st.rerun()
        st.info(
            "Semesters in session on the working date: "
            + ", ".join(store.active_semesters(iso) or ["none"])
        )

    with tab_off:
        st.subheader("Add a subject offering")
        st.caption(
            "An offering assigns a faculty member to teach a subject to a "
            "division at a weekly slot; cross-department assignments are "
            "allowed and flagged ‡."
        )
        all_divs = sorted(store.data.classes)
        c1, c2, c3 = st.columns(3)
        div = c1.selectbox("Division", all_divs, key="off-div")
        subj = c2.selectbox(
            "Subject",
            sorted(store.data.subjects),
            format_func=lambda s: sname(store, s),
            key="off-subj",
        )
        tid = c3.selectbox(
            "Faculty",
            sorted(store.data.teachers),
            format_func=lambda t: f"{tname(store, t)} ({store.data.teachers[t].department})",
            key="off-tid",
        )
        c4, c5 = st.columns(2)
        day = c4.selectbox("Day", DAYS, key="off-day")
        free = [
            p for p in PERIODS if store.data.slot_at(day, p, div) is None
        ]
        period = c5.selectbox("Period", free if free else PERIODS, key="off-period")
        if not free:
            st.warning(f"{div} has no free period on {day}.")
        elif st.button("Add offering", type="primary"):
            try:
                store.add_offering(div, subj, tid, day, period)
            except (KeyError, ValueError) as e:
                st.error(str(e))
            else:
                st.toast("Offering added to the division timetable.")
                st.rerun()

        st.subheader("Division offerings")
        view_div = st.selectbox("Show division", all_divs, key="off-view")
        slots = sorted(
            (s for s in store.data.timetable if s.class_group == view_div),
            key=lambda s: (DAYS.index(s.day), s.period),
        )
        st.dataframe(
            pd.DataFrame(
                {
                    "Day": [s.day for s in slots],
                    "Period": [f"P{s.period}" for s in slots],
                    "Subject": [sname(store, s.subject) for s in slots],
                    "Faculty": [tname(store, store.effective_teacher(s)) for s in slots],
                    "Dept": [dname(store, store.data.teachers[store.effective_teacher(s)].department) for s in slots],
                    "Room": [s.room for s in slots],
                    "Cross-dept": ["‡" if store.cross_department(s) else "" for s in slots],
                }
            ),
            hide_index=True,
            width="stretch",
        )

        st.subheader("Reassign an offering")
        c1, c2 = st.columns(2)
        re_slot = c1.selectbox(
            "Slot", slots, format_func=lambda s: slot_label(store, s), key="re-slot"
        )
        new_tid = c2.selectbox(
            "New faculty",
            sorted(store.data.teachers),
            format_func=lambda t: f"{tname(store, t)} ({store.data.teachers[t].department})",
            key="re-tid",
        )
        if st.button("Reassign faculty"):
            try:
                store.reassign_offering(re_slot.day, re_slot.period, re_slot.class_group, new_tid)
            except (KeyError, ValueError) as e:
                st.error(str(e))
            else:
                st.toast("Offering reassigned.")
                st.rerun()

        st.subheader("Create a project group")
        st.caption(
            "Adds a weekly supervision slot to the division and supervisor "
            "timetables; supervision is never auto-substituted."
        )
        c1, c2 = st.columns(2)
        pg_title = c1.text_input("Project title", key="pg-title")
        pg_div = c2.selectbox("Project division", all_divs, key="pg-div")
        c1, c2, c3 = st.columns(3)
        pg_sup = c1.selectbox(
            "Supervisor",
            sorted(store.data.teachers),
            format_func=lambda t: f"{tname(store, t)} ({store.data.teachers[t].department})",
            key="pg-sup",
        )
        pg_day = c2.selectbox("Day", DAYS, key="pg-day")
        pg_free = [p for p in PERIODS if store.data.slot_at(pg_day, p, pg_div) is None]
        pg_period = c3.selectbox("Period", pg_free if pg_free else PERIODS, key="pg-period")
        pg_rooms = sorted(
            r
            for r in store.data.rooms
            if r not in store.data.room_at(
                pg_day, pg_period, semester_parity(store.data.classes[pg_div].semester)
            )
        )
        pg_room = st.selectbox("Room", pg_rooms if pg_rooms else [""], key="pg-room")
        if not pg_free:
            st.warning(f"{pg_div} has no free period on {pg_day}.")
        elif st.button("Create project group"):
            try:
                pg = store.add_project_group(
                    pg_title or "Untitled project", pg_div, pg_sup, pg_day, pg_period, pg_room
                )
            except (KeyError, ValueError) as e:
                st.error(str(e))
            else:
                st.toast(f"{pg.id} created with a weekly supervision slot.")
                st.rerun()
        if store.projects:
            st.dataframe(
                projects_df(store, store.projects), hide_index=True, width="stretch"
            )

    with tab_gen:
        st.subheader("Generate a new timetable")
        st.caption(
            "Builds a draft for a target academic year and semester. The "
            "published timetable is untouched until you publish — and a "
            "future semester's draft cannot go live early."
        )
        gen_depts = [
            d
            for d in sorted(store.data.departments)
            if any(c.department == d for c in store.data.classes.values())
        ]
        c1, c2, c3, c4 = st.columns(4)
        gen_year = int(
            c1.number_input(
                "Academic year",
                min_value=2000,
                max_value=2100,
                value=store.academic_year + 1,
                step=1,
                key="gen-year",
            )
        )
        gen_sem = c2.selectbox("Semester", SEMESTERS, key="gen-sem")
        gen_dept = c3.selectbox(
            "Department", gen_depts,
            format_func=lambda d: dname(store, d), key="gen-dept",
        )
        gen_divs = divisions_of(store, gen_dept, gen_sem)
        if not gen_divs:
            st.warning(f"No {dname(store, gen_dept)} divisions in {gen_sem}.")
        else:
            gen_div = c4.selectbox("Division", gen_divs, key="gen-div")
            window = store.semester_window_for(gen_year, gen_sem)
            st.caption(
                f"{gen_sem} of {gen_year} runs {window.start} – {window.end}."
            )

            st.subheader("Required weekly hours")
            defaults = default_requirements(gen_dept)
            subject_ids = sorted(store.data.subjects)
            cols = st.columns(4)
            requirements = {}
            for i, sid in enumerate(subject_ids):
                requirements[sid] = int(
                    cols[i % 4].number_input(
                        sname(store, sid),
                        min_value=0,
                        max_value=12,
                        value=defaults.get(sid, 0),
                        key=f"gen-h-{gen_dept}-{sid}",
                    )
                )
            requirements = {s: h for s, h in requirements.items() if h > 0}

            st.subheader("Faculty assignment (optional)")
            teacher_opts = sorted(
                store.data.teachers,
                key=lambda t: f"{store.data.teachers[t].name} ({t})",
            )
            pins = {}
            pcols = st.columns(4)
            for i, sid in enumerate(sorted(requirements)):
                choice = pcols[i % 4].selectbox(
                    sname(store, sid),
                    ["auto"] + teacher_opts,
                    format_func=lambda t: (
                        "auto"
                        if t == "auto"
                        else f"{tname(store, t)} ({t})"
                    ),
                    key=f"gen-a-{gen_dept}-{sid}",
                )
                if choice != "auto":
                    pins[sid] = choice

            if st.button("Generate draft", type="primary", key="gen-run"):
                try:
                    store.generate_draft(gen_div, gen_year, requirements, pins)
                except (KeyError, ValueError) as e:
                    st.error(str(e))
                else:
                    st.rerun()

            draft = next(
                (
                    d
                    for d in store.timetable_drafts(TT_DRAFT)
                    if d.academic_year == gen_year and d.class_group == gen_div
                ),
                None,
            )
            if draft is not None:
                st.subheader(f"Draft — {gen_div}, {gen_sem} {gen_year}")
                cells = {
                    (s.day, s.period): (
                        f"{sname(store, s.subject)}\n"
                        f"{tname(store, s.teacher)} · {s.room}"
                    )
                    for s in draft.slots
                }
                st.dataframe(
                    week_grid(cells), hide_index=True, width="stretch"
                )
                if draft.violations:
                    st.error(
                        "Unsatisfied constraints — publish is blocked:\n- "
                        + "\n- ".join(draft.violations)
                    )
                for w in draft.warnings:
                    st.warning(w)
                b1, b2 = st.columns(2)
                if b1.button("Publish timetable", key="gen-publish"):
                    try:
                        store.publish_draft(draft.id, iso)
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        st.toast(f"{gen_div} timetable published.")
                        st.rerun()
                if b2.button("Discard draft", key="gen-discard"):
                    store.discard_draft(draft.id)
                    st.rerun()

            drafts = store.timetable_drafts()
            if drafts:
                st.subheader("Drafts")
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Draft": [d.id for d in drafts],
                            "Division": [d.class_group for d in drafts],
                            "Semester": [
                                store.data.classes[d.class_group].semester
                                for d in drafts
                            ],
                            "Academic year": [d.academic_year for d in drafts],
                            "Slots": [len(d.slots) for d in drafts],
                            "Violations": [len(d.violations) for d in drafts],
                            "Status": [d.status for d in drafts],
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )

    with tab_dir:
        st.subheader("Departments")
        st.dataframe(
            pd.DataFrame(
                {
                    "Department": [dname(store, d) for d in sorted(store.data.departments)],
                    "Faculty": [
                        sum(1 for t in store.data.teachers.values() if t.department == d)
                        for d in sorted(store.data.departments)
                    ],
                    "Divisions": [
                        sum(1 for c in store.data.classes.values() if c.department == d)
                        for d in sorted(store.data.departments)
                    ],
                }
            ),
            hide_index=True,
            width="stretch",
        )
        st.subheader("Faculty")
        st.dataframe(
            pd.DataFrame(
                {
                    "Faculty": [t.name for t in sorted(store.data.teachers.values(), key=lambda t: (t.department, t.id))],
                    "ID": [t.id for t in sorted(store.data.teachers.values(), key=lambda t: (t.department, t.id))],
                    "Department": [dname(store, t.department) for t in sorted(store.data.teachers.values(), key=lambda t: (t.department, t.id))],
                    "Subjects": [", ".join(sorted(sname(store, s) for s in t.subjects)) for t in sorted(store.data.teachers.values(), key=lambda t: (t.department, t.id))],
                }
            ),
            hide_index=True,
            width="stretch",
        )


def page_workload(store: Store, date: dt.date, ctx: dict) -> None:
    dept = ctx.get("dept") if ctx["role"] == ROLE_COORD else None
    st.title("Workload & Export" + (f" — {dname(store, dept)}" if dept else ""))
    st.markdown(
        '<p class="section-note">How substitute duties are spread across staff '
        "this week, plus a CSV of the day's results.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()

    teachers = [
        t
        for t in store.data.teachers.values()
        if dept is None or t.department == dept
    ]
    load = store.workload(iso)
    st.subheader("Substitute workload this week")
    chart = pd.DataFrame(
        {
            "Faculty": [t.name for t in teachers],
            "Sub periods": [load.get(t.id, 0) for t in teachers],
        }
    ).set_index("Faculty")
    st.bar_chart(chart, color="#0E7C7B", horizontal=True)

    all_rows = [
        {
            "Faculty": t.name,
            "Department": dname(store, t.department),
            "Subjects": ", ".join(sorted(sname(store, s) for s in t.subjects)),
            "Substitute periods": load.get(t.id, 0),
        }
        for t in sorted(teachers, key=lambda t: (-load.get(t.id, 0), t.id))
    ]
    st.dataframe(pd.DataFrame(all_rows), hide_index=True, width="stretch")

    st.subheader("Export")
    props = store.proposals_for(iso, department=dept)
    if not props:
        st.info("No substitution data for this date yet — report an absence first.")
        return
    st.dataframe(proposal_df(store, props), hide_index=True, width="stretch")
    st.download_button(
        "Download CSV",
        to_csv(store, iso),
        file_name=f"campusly-substitutions-{iso}.csv",
        mime="text/csv",
        type="primary",
    )
    st.caption("One row per affected period: division, absent faculty, substitute, status.")


# ----------------------------------------------------------------------------- main


def main() -> None:
    store = get_store()
    ss = st.session_state
    ss.setdefault("page", "Dashboard")
    ss.setdefault("role", ROLE_ADMIN)

    dept_ids = sorted(store.data.departments)
    teacher_ids = sorted(store.data.teachers, key=lambda t: store.data.teachers[t].name)

    with st.sidebar:
        st.header("Campusly")
        st.caption("Greenfield College · demo roles (no sign-in)")
        ss.setdefault("dept", next(d for d in dept_ids if d != "bs"))
        ss.setdefault("faculty_id", teacher_ids[0])
        ss.setdefault("division", sorted(store.data.classes)[0])

        st.radio("View as", ROLES, key="role")
        role = ss.role
        if role == ROLE_COORD:
            st.selectbox(
                "Coordinator of", dept_ids, key="dept",
                format_func=lambda d: dname(store, d),
            )
        if role == ROLE_FACULTY:
            st.selectbox(
                "Faculty member", teacher_ids, key="faculty_id",
                format_func=lambda t: f"{tname(store, t)} ({store.data.teachers[t].department})",
            )
        st.divider()
        date = st.date_input("Working date", value=DEMO_DATE, min_value=dt.date(2026, 1, 1))
        if role == ROLE_STUDENT:
            div_options = active_divisions(store, date.isoformat())
            if not div_options:
                st.error("No semesters in session on this date.")
                return
            if ss.division not in div_options:
                ss.division = div_options[0]
            st.selectbox("Your division", div_options, key="division")

        pages = ROLE_PAGES[role]
        if ss.page not in pages:
            ss.page = pages[0]
        page = st.radio("Navigate", pages, index=pages.index(ss.page))
        ss.page = page
        st.divider()

        dept = ss.dept if role == ROLE_COORD else None
        pending = store.counts(date.isoformat(), department=dept)["pending"]
        if role == ROLE_COORD:
            pending += len(store.pending_exchanges(dept))
        if pending:
            st.warning(f"{pending} item(s) awaiting review")
        else:
            st.caption("Queue clear for this date")
        if st.button("Reset demo data"):
            get_store.clear()
            for k in ("last_report", "confirm_reject"):
                ss.pop(k, None)
            st.toast("Demo data reset.")
            st.rerun()

    ctx = {
        "role": role,
        "dept": ss.get("dept"),
        "faculty_id": ss.get("faculty_id"),
        "division": ss.get("division"),
    }
    handlers = {
        "Dashboard": page_dashboard,
        "Report Absence": page_absence,
        "Review Queue": page_review,
        "Exchanges": page_exchanges,
        "Timetable & Notices": page_timetable,
        "My Timetable": page_my_timetable,
        "Workload & Export": page_workload,
        "Administration": page_admin,
    }
    handlers[page](store, date, ctx)


main()
