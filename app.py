"""Campusly — smart substitute scheduling. Streamlit UI over the campusly core.

Run: streamlit run app.py
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from campusly.data import day_name, load_seed_data
from campusly.export import to_csv
from campusly.models import (
    PERIOD_TIMES,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_UNCOVERED,
    Proposal,
)
from campusly.store import DuplicateAbsenceError, Store

DEMO_DATE = dt.date(2026, 10, 26)  # a Monday
PAGES = [
    "Dashboard",
    "Report Absence",
    "Review Queue",
    "Timetable & Notices",
    "Workload & Export",
]

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


def get_store() -> Store:
    if "store" not in st.session_state:
        st.session_state.store = Store(load_seed_data())
    return st.session_state.store


def tname(store: Store, tid: str | None) -> str:
    return store.data.teachers[tid].name if tid else "—"


def cname(store: Store, cid: str) -> str:
    return store.data.classes[cid].name


def sname(store: Store, sid: str) -> str:
    return store.data.subjects[sid].name


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
    if "room-changed" in p.warnings:
        out.append('<span class="chip chip-blue">room changed</span>')
    if p.status == STATUS_UNCOVERED or not p.substitute_teacher:
        out.append('<span class="chip chip-red">uncovered</span>')
    return "".join(out)


def proposal_df(store: Store, props: list[Proposal]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Period": f"P{p.period} ({PERIOD_TIMES[p.period]})",
                "Class": cname(store, p.class_group),
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


# ----------------------------------------------------------------------------- pages


def page_dashboard(store: Store, date: dt.date) -> None:
    st.markdown(
        '<div class="hero"><h1>Campusly</h1>'
        "<p>Smart substitute scheduling · Greenfield High (fictional data)</p></div>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    c = store.counts(iso)

    cols = st.columns(4)
    stat_card(cols[0], "Absences", c["absences"], "teachers out today", "#0B2545")
    stat_card(cols[1], "Pending review", c["pending"], "awaiting your approval", "#d97706")
    stat_card(cols[2], "Approved", c["approved"], "published to timetable", "#0E7C7B")
    stat_card(cols[3], "Uncovered", c["uncovered"], "need manual handling", "#dc2626")

    st.write("")
    if c["uncovered"]:
        st.error(
            f"{c['uncovered']} class(es) still have no substitute. "
            "Open the Review Queue to handle them."
        )
    elif c["pending"]:
        st.warning(f"{c['pending']} substitute proposal(s) are waiting for approval.")
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
        st.caption("Teachers reported absent on the selected date")
        rows = [
            {
                "Teacher": tname(store, a.teacher),
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
        st.caption("Substitute proposals for the selected date")
        props = store.proposals_for(iso)
        if props:
            st.dataframe(
                proposal_df(store, props)[
                    ["Period", "Class", "Subject", "Substitute", "Status", "Flags"]
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
            st.error("Pick a weekday — school is closed on weekends.")
        else:
            busy = {a.teacher for a in store.absences if a.date == iso}
            picks = [
                s.teacher for s in store.data.slots_on(day) if s.teacher not in busy
            ][:2]
            for tid in dict.fromkeys(picks):
                try:
                    store.report_absence(tid, iso)
                except DuplicateAbsenceError:
                    pass
            store.run_allocation(iso)
            st.toast("Demo scenario loaded — proposals ready for review.")
            st.rerun()


def page_absence(store: Store, date: dt.date) -> None:
    st.title("Report Teacher Absence")
    st.markdown(
        '<p class="section-note">Pick a teacher to see their classes on the '
        "selected day, then report the absence — Campusly immediately finds "
        "substitutes and sends proposals to the Review Queue.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    day = day_name(iso)
    if day is None:
        st.warning("Selected date is a weekend — school is closed. Pick a weekday in the sidebar.")
        return

    teachers = sorted(store.data.teachers.values(), key=lambda t: t.name)
    options = {t.name: t.id for t in teachers}
    absent_on_date = {a.teacher for a in store.absences if a.date == iso}

    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.selectbox("Teacher", list(options))
    tid = options[name]
    with col2:
        st.metric("Classes that day", len([s for s in store.data.slots_on(day) if s.teacher == tid]))

    already = tid in absent_on_date
    if already:
        st.info(f"{name} is already marked absent on {iso}.")

    slots = [s for s in store.data.slots_on(day) if s.teacher == tid]
    st.subheader(f"{name}'s schedule — {day}")
    if slots:
        st.dataframe(
            pd.DataFrame(
                {
                    "Period": [f"P{s.period} ({PERIOD_TIMES[s.period]})" for s in slots],
                    "Class": [cname(store, s.class_group) for s in slots],
                    "Subject": [sname(store, s.subject) for s in slots],
                    "Room": [s.room for s in slots],
                }
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info(f"{name} has no classes on {day}.")

    if st.button("Report absence & find substitutes", type="primary", disabled=already):
        try:
            absence = store.report_absence(tid, iso)
        except DuplicateAbsenceError:
            st.error(f"{name} is already marked absent on {iso}.")
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
                        "Class": [cname(store, s.class_group) for s in affected],
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


def page_review(store: Store, date: dt.date) -> None:
    st.title("Review Queue")
    st.markdown(
        '<p class="section-note">Nothing changes in the timetable until you '
        "approve a proposal. Rejecting leaves the class flagged uncovered.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    load = store.workload(iso)
    pending = [p for p in store.proposals_for(iso) if p.status == STATUS_PENDING]
    uncovered = [p for p in store.proposals_for(iso) if p.status == STATUS_UNCOVERED]
    approved = [p for p in store.proposals_for(iso) if p.status == STATUS_APPROVED]

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
                    store.reject(p.id)
                    st.session_state.pop("confirm_reject", None)
                    st.toast("Rejected — class flagged uncovered.")
                    st.rerun()
                if mid.button("Cancel", key=f"rej-n-{p.id}"):
                    st.session_state.pop("confirm_reject", None)
                    st.rerun()
            else:
                if mid.button("Approve", key=f"ok-{p.id}", type="primary"):
                    store.approve(p.id)
                    st.toast("Approved — timetable updated.")
                    st.rerun()
                if mid.button("Reject", key=f"no-{p.id}"):
                    st.session_state["confirm_reject"] = p.id
                    st.rerun()

    if uncovered:
        st.subheader(f"Uncovered — needs manual handling ({len(uncovered)})")
        for p in uncovered:
            reason = "no free teacher" if "no-teacher-available" in p.warnings else "rejected"
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


def page_timetable(store: Store, date: dt.date) -> None:
    st.title("Timetable & Notices")
    st.markdown(
        '<p class="section-note">The published timetable for the selected day. '
        "Substitutions appear only after approval.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()
    day = day_name(iso)
    if day is None:
        st.warning("Selected date is a weekend — school is closed. Pick a weekday in the sidebar.")
        return

    all_classes = list(store.data.classes)
    picked = st.multiselect(
        "Filter classes (helps on small screens)",
        all_classes,
        default=all_classes,
        format_func=lambda c: store.data.classes[c].name,
    )
    rows = store.effective_timetable(iso)
    grid = {c: {} for c in all_classes}
    for r in rows:
        subj = sname(store, r["subject"])
        if r["status"] == "approved":
            cell = f"{subj} · {tname(store, r['teacher'])} (sub)"
        elif r["status"] in (STATUS_PENDING, STATUS_UNCOVERED):
            cell = f"{subj} · {r['status'].upper()}"
        else:
            cell = f"{subj} · {tname(store, r['teacher'])}"
        grid[r["class_group"]][r["period"]] = cell

    if not picked:
        st.info("Select at least one class to view the timetable.")
    else:
        df = pd.DataFrame(
            {
                f"P{p} ({PERIOD_TIMES[p]})": [grid[cid].get(p, "—") for cid in picked]
                for p in range(1, 7)
            },
            index=[store.data.classes[c].name for c in picked],
        ).T

        def style_cell(v: str) -> str:
            if "UNCOVERED" in v:
                return "background-color: #991b1b; color: white; font-weight: 600"
            if "PENDING" in v:
                return "background-color: #b45309; color: white"
            if "(sub)" in v:
                return "background-color: #0E7C7B; color: white; font-weight: 600"
            return ""

        st.subheader(f"Effective timetable — {day}, {iso}")
        st.dataframe(df.style.map(style_cell), width="stretch")
        st.caption("Teal = approved substitute · Amber = awaiting review · Red = uncovered")

    notices = store.notices(iso)
    st.subheader("Notices for affected classes")
    if notices:
        for n in notices:
            mark = ":red[●]" if "NO substitute" in n else ":green[●]"
            st.markdown(f"{mark} {n}")
    else:
        st.info("No notices for this date.")


def page_workload(store: Store, date: dt.date) -> None:
    st.title("Workload & Export")
    st.markdown(
        '<p class="section-note">How substitute duties are spread across staff '
        "this week, plus a CSV of the day's results.</p>",
        unsafe_allow_html=True,
    )
    iso = date.isoformat()

    load = store.workload(iso)
    st.subheader("Substitute workload this week")
    chart = pd.DataFrame(
        {
            "Teacher": [t.name for t in store.data.teachers.values()],
            "Sub periods": [load.get(t.id, 0) for t in store.data.teachers.values()],
        }
    ).set_index("Teacher")
    st.bar_chart(chart, color="#0E7C7B", horizontal=True)

    all_rows = [
        {
            "Teacher": t.name,
            "Subjects": ", ".join(sorted(sname(store, s) for s in t.subjects)),
            "Substitute periods": load.get(t.id, 0),
        }
        for t in sorted(
            store.data.teachers.values(), key=lambda t: (-load.get(t.id, 0), t.id)
        )
    ]
    st.dataframe(pd.DataFrame(all_rows), hide_index=True, width="stretch")

    st.subheader("Export")
    props = store.proposals_for(iso)
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
    st.caption("One row per affected period: class, absent teacher, substitute, status.")


# ----------------------------------------------------------------------------- main


def main() -> None:
    store = get_store()
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    with st.sidebar:
        st.header("Campusly")
        st.caption("Greenfield High · coordinator console")
        page = st.radio(
            "Navigate",
            PAGES,
            index=PAGES.index(st.session_state.page),
        )
        st.session_state.page = page
        st.divider()
        date = st.date_input("Working date", value=DEMO_DATE, min_value=dt.date(2026, 1, 1))
        pending = store.counts(date.isoformat())["pending"]
        if pending:
            st.warning(f"{pending} proposal(s) awaiting review")
        else:
            st.caption("Queue clear for this date")
        if st.button("Reset demo data"):
            st.session_state.store = Store(load_seed_data())
            st.session_state.pop("last_report", None)
            st.session_state.pop("confirm_reject", None)
            st.toast("Demo data reset.")
            st.rerun()

    {
        "Dashboard": page_dashboard,
        "Report Absence": page_absence,
        "Review Queue": page_review,
        "Timetable & Notices": page_timetable,
        "Workload & Export": page_workload,
    }[page](store, date)


main()
