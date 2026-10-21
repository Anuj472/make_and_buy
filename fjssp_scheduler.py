"""Flexible Job Shop scheduler (modules M3 + M4 of the integrated plan).

M3 - master data / calendar helpers:
    * machine_group(): derives the group from the machine id (CNC_MILL_3 -> CNC_MILL)
    * map_to_real_schedule(): projects working minutes onto the shop calendar

M4 - Flexible Job Shop (FJSSP) engine on Google OR-Tools CP-SAT:
    * every routing step may run on any active machine of the same group
    * flexible=False reproduces the old behaviour (step pinned to its routing machine)
"""
import datetime
import math
import re

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

# Shop calendar (moved here from app.py so it is configured in one place)
WORK_START_HOUR = 8
WORK_MINUTES_PER_DAY = 600   # 08:00 - 18:00
WORK_DAYS_PER_WEEK = 6       # Monday - Saturday


def machine_group(machine_id):
    """CNC_MILL_3 -> CNC_MILL, CNC_MILL -> CNC_MILL."""
    return re.sub(r"_\d+$", "", str(machine_id))


def build_machine_groups(df_machines, down_machines=None):
    """Return {group: [machine_id, ...]} for all machines that are not down."""
    down = set(down_machines or [])
    groups = {}
    for m_id in df_machines["machine_id"]:
        if m_id in down:
            continue
        groups.setdefault(machine_group(m_id), []).append(m_id)
    return groups


def next_monday_8am(today=None):
    today = today or datetime.datetime.today()
    days_ahead = 7 - today.weekday()
    return (today + datetime.timedelta(days=days_ahead)).replace(
        hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)


_WEEKMASK = "1" * WORK_DAYS_PER_WEEK + "0" * (7 - WORK_DAYS_PER_WEEK)


def due_in_working_minutes(due_date, base_time):
    """Working minutes from base_time until the end of the working day of due_date.
    Negative if the due date is already before the schedule start."""
    due = pd.Timestamp(due_date).date()
    base = pd.Timestamp(base_time).date()
    days = int(np.busday_count(base, due, weekmask=_WEEKMASK))
    if np.is_busday(due, weekmask=_WEEKMASK) and due >= base:
        days += 1          # include the due day itself (due by 18:00)
    return days * WORK_MINUTES_PER_DAY


def working_minute_to_datetime(minute, base_time):
    """Calendar timestamp of a working minute (an end at 600 means 18:00 that day)."""
    if minute <= 0:
        return base_time
    working_day, min_in_day = divmod(minute, WORK_MINUTES_PER_DAY)
    if min_in_day == 0:
        working_day, min_in_day = working_day - 1, WORK_MINUTES_PER_DAY
    weeks, dow = divmod(working_day, WORK_DAYS_PER_WEEK)
    return base_time + datetime.timedelta(days=weeks * 7 + dow, minutes=min_in_day)


def start_minute_to_datetime(minute, base_time):
    """Calendar timestamp of a start at a working minute (600 means 08:00 next working day)."""
    working_day, min_in_day = divmod(minute, WORK_MINUTES_PER_DAY)
    weeks, dow = divmod(working_day, WORK_DAYS_PER_WEEK)
    return base_time + datetime.timedelta(days=weeks * 7 + dow, minutes=min_in_day)


def datetime_to_working_minute(dt, base_time):
    """Inverse of the above: working minutes from base_time to dt (negative if dt is earlier)."""
    dt = pd.Timestamp(dt).to_pydatetime()
    days = int(np.busday_count(base_time.date(), dt.date(), weekmask=_WEEKMASK))
    mid = 0
    if np.is_busday(dt.date(), weekmask=_WEEKMASK):
        day_start = dt.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
        mid = min(max((dt - day_start).total_seconds() / 60, 0), WORK_MINUTES_PER_DAY)
    return days * WORK_MINUTES_PER_DAY + int(round(mid))


# ---- Time fences (agreed with the shop: week 1 frozen, weeks 2-4 slushy, week 5+ liquid)
FROZEN_DAYS = 7
SLUSHY_DAYS = 28


def fence_zone(start_dt, base_time, frozen_days=FROZEN_DAYS, slushy_days=SLUSHY_DAYS):
    """Frozen / Slushy / Liquid by planned start relative to the plan start."""
    start_dt = pd.Timestamp(start_dt).to_pydatetime()
    if start_dt < base_time + datetime.timedelta(days=frozen_days):
        return "Frozen"
    if start_dt < base_time + datetime.timedelta(days=slushy_days):
        return "Slushy"
    return "Liquid"


# Penalties used when re-planning against a published baseline
FROZEN_SHIFT_PENALTY = 1000   # per minute a frozen operation is pushed later
SLUSHY_CHANGE_PENALTY = 60    # per slushy operation moved to another machine


def map_to_real_schedule(start_working_min, duration_mins, start_date):
    """Split a task given in working minutes into calendar segments (one per working day)."""
    segments = []
    remaining = duration_mins
    current = start_working_min
    while remaining > 0:
        working_day = current // WORK_MINUTES_PER_DAY
        min_in_day = current % WORK_MINUTES_PER_DAY
        weeks = working_day // WORK_DAYS_PER_WEEK
        day_of_week = working_day % WORK_DAYS_PER_WEEK

        real_start = (start_date
                      + datetime.timedelta(days=weeks * 7 + day_of_week)
                      + datetime.timedelta(minutes=min_in_day))
        seg = min(remaining, WORK_MINUTES_PER_DAY - min_in_day)
        segments.append({"start": real_start,
                         "end": real_start + datetime.timedelta(minutes=seg),
                         "duration": seg})
        remaining -= seg
        current += seg
    return segments


def solve_fjssp(make_orders, df_routings, df_machines, objective="makespan",
                flexible=True, down_machines=None, time_limit=30.0, workers=8,
                base_time=None, baseline=None):
    """Schedule in-house orders.

    make_orders : DataFrame with Order_ID, Item_ID, Make_In_House_Qty and either
                  Due_Date (calendar date, preferred) or Delivery_Period_Days.
                  Optional LD_Weight (rupees per week late) for objective="ld".
    objective   : "makespan", "tardiness" or "ld" (LD-weighted tardiness)
    flexible    : True  -> any active machine in the routing machine's group
                  False -> only the routing machine (legacy behaviour)
    down_machines : machine ids excluded from scheduling
    base_time   : schedule start (default next Monday 08:00)
    baseline    : previously published plan (Order, Op_Seq, Machine, Planned_Start,
                  Planned_End). When given, time fences are applied relative to base_time:
                    finished      -> dropped
                    in progress   -> same machine, remaining time, starts at once
                    Frozen        -> same machine, may only move later (heavy penalty)
                    Slushy        -> any machine in group, penalty per machine change
                    Liquid / new  -> free
                  A frozen/in-progress machine that is now down is released (logged).

    Returns dict(status, makespan, total_tardiness, tasks=DataFrame, unschedulable=[...],
                 fence=dict(counts, overrides)). Times are working minutes from base_time.
    """
    base_time = base_time or next_monday_8am()
    groups = build_machine_groups(df_machines, down_machines)
    down = set(down_machines or [])
    speed = {}
    if "speed_factor" in df_machines.columns:
        speed = dict(zip(df_machines["machine_id"], df_machines["speed_factor"].fillna(1.0)))

    model = cp_model.CpModel()
    jobs = []
    unschedulable = []

    # previous published plan, keyed by (order, op_seq)
    prev = {}
    if baseline is not None and len(baseline):
        for b in baseline.itertuples():
            ps = datetime_to_working_minute(b.Planned_Start, base_time)
            pe = datetime_to_working_minute(b.Planned_End, base_time)
            prev[(b.Order, int(b.Op_Seq))] = {
                "machine": b.Machine, "ps": ps, "pe": pe,
                "zone": fence_zone(b.Planned_Start, base_time)}
    counts = {"Finished": 0, "In progress": 0, "Frozen": 0, "Slushy": 0, "Liquid": 0, "New": 0}
    overrides = []

    # ---- collect operations and their candidate machines -------------------
    for _, order in make_orders.iterrows():
        qty = order["Make_In_House_Qty"]
        item_ops = df_routings[df_routings["item_id"] == order["Item_ID"]] \
            .sort_values("operation_sequence")
        ops = []
        for _, task in item_ops.iterrows():
            seq = int(task["operation_sequence"])
            base_hours = task["setup_hours"] + task["run_hours_per_unit"] * qty
            routed = task["machine_id"]
            if flexible:
                candidates = groups.get(machine_group(routed), [])
            else:
                candidates = [] if routed in down else [routed]

            op = {"seq": seq, "routed": routed, "rule": "New" if prev else "Free",
                  "fix_start": False, "min_start": None, "prev_machine": None, "remaining": None}
            b = prev.get((order["Order_ID"], seq))
            if b is not None:
                if b["pe"] <= 0:                       # finished before the plan start
                    counts["Finished"] += 1
                    continue
                if b["ps"] < 0 or b["zone"] == "Frozen":
                    if b["machine"] in down:
                        overrides.append((order["Order_ID"], seq, b["machine"]))
                        op["rule"], op["prev_machine"] = "Released (machine down)", b["machine"]
                    elif b["ps"] < 0:
                        candidates = [b["machine"]]
                        op.update(rule="In progress", fix_start=True, remaining=b["pe"])
                    else:
                        candidates = [b["machine"]]
                        op.update(rule="Frozen", min_start=b["ps"])
                elif b["zone"] == "Slushy":
                    op.update(rule="Slushy", prev_machine=b["machine"])
                else:
                    op["rule"] = "Liquid"
            if prev:
                counts[op["rule"]] = counts.get(op["rule"], 0) + 1

            if not candidates:
                unschedulable.append((order["Order_ID"], seq, routed))
                ops = None
                break
            if op["remaining"] is not None:
                op["durations"] = {m: op["remaining"] for m in candidates}
            else:
                op["durations"] = {m: int(math.ceil(base_hours * 60 / speed.get(m, 1.0)))
                                   for m in candidates}
            ops.append(op)
        if ops:
            if "Due_Date" in order and not pd.isna(order["Due_Date"]):
                due = due_in_working_minutes(order["Due_Date"], base_time)
            else:   # legacy: delivery days counted from schedule start
                due_days = order.get("Delivery_Period_Days", 30)
                due_days = 30 if pd.isna(due_days) else float(due_days)
                due = int(math.ceil(due_days * WORK_MINUTES_PER_DAY))
            weight = order.get("LD_Weight", 1)
            weight = 1 if pd.isna(weight) else max(1, int(round(weight / 100)))
            jobs.append({"order": order["Order_ID"], "item": order["Item_ID"], "qty": qty,
                         "due": due, "weight": weight, "ops": ops})

    fence = {"counts": counts, "overrides": overrides, "applied": bool(prev)}
    if not jobs:
        return {"status": "NO_JOBS", "makespan": 0, "total_tardiness": 0,
                "tasks": pd.DataFrame(), "unschedulable": unschedulable, "fence": fence}

    latest_lock = max([op["min_start"] or 0 for j in jobs for op in j["ops"]] + [0])
    horizon = latest_lock + sum(max(op["durations"].values()) for j in jobs for op in j["ops"])
    # with a baseline, only frozen / in-progress / released work may run in the frozen week
    frozen_boundary = datetime_to_working_minute(
        base_time + datetime.timedelta(days=FROZEN_DAYS), base_time) if prev else 0
    horizon += frozen_boundary

    # ---- variables & constraints -------------------------------------------
    machine_intervals = {}
    job_ends, tardiness_vars = [], []
    frozen_shifts, slushy_changes = [], []
    for j in jobs:
        prev_end = None
        for op in j["ops"]:
            sfx = f"_{j['order']}_{op['seq']}"
            start = model.NewIntVar(0, horizon, "s" + sfx)
            end = model.NewIntVar(0, horizon, "e" + sfx)
            op["start"], op["end"], op["alts"] = start, end, {}

            presences = []
            for m, dur in op["durations"].items():
                lit = model.NewBoolVar(f"x{sfx}_{m}")
                iv = model.NewOptionalIntervalVar(start, dur, end, lit, f"iv{sfx}_{m}")
                machine_intervals.setdefault(m, []).append(iv)
                op["alts"][m] = lit
                presences.append(lit)
            model.AddExactlyOne(presences)

            if op["fix_start"]:                      # in progress: continues immediately
                model.Add(start == 0)
            if op["min_start"] is not None:          # frozen: right-shift only
                model.Add(start >= op["min_start"])
                shift = model.NewIntVar(0, horizon, "shift" + sfx)
                model.Add(shift == start - op["min_start"])
                frozen_shifts.append(shift)
            if op["rule"] == "Slushy" and op["prev_machine"] in op["alts"]:
                slushy_changes.append(1 - op["alts"][op["prev_machine"]])
            if op["rule"] in ("Slushy", "Liquid", "New"):
                model.Add(start >= frozen_boundary)

            if prev_end is not None:
                model.Add(start >= prev_end)
            prev_end = end

        job_ends.append(prev_end)
        tard = model.NewIntVar(0, horizon + max(0, -j["due"]), f"tard_{j['order']}")
        model.Add(tard >= prev_end - j["due"])
        tardiness_vars.append(tard)

    for intervals in machine_intervals.values():
        model.AddNoOverlap(intervals)

    makespan = model.NewIntVar(0, horizon, "makespan")
    model.AddMaxEquality(makespan, job_ends)
    total_tard = sum(tardiness_vars)
    frozen_pen = FROZEN_SHIFT_PENALTY * sum(frozen_shifts)
    slushy_pen = SLUSHY_CHANGE_PENALTY * sum(slushy_changes)

    if objective == "tardiness":
        # primary: tardiness (+ frozen shifts); makespan and slushy changes break ties
        model.Minimize((total_tard + frozen_pen) * (horizon + 1) + makespan + slushy_pen)
    elif objective == "ld":
        # LD-weighted tardiness: late minutes x (rupees per week late / 100)
        weighted = sum(j["weight"] * t for j, t in zip(jobs, tardiness_vars))
        model.Minimize((weighted + frozen_pen) * (horizon + 1) + makespan + slushy_pen)
    else:
        model.Minimize(makespan + frozen_pen + slushy_pen)

    # ---- solve ---------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": status_name, "makespan": None, "total_tardiness": None,
                "tasks": pd.DataFrame(), "unschedulable": unschedulable, "fence": fence}

    rows = []
    for j in jobs:
        for op in j["ops"]:
            m = next(m for m, lit in op["alts"].items() if solver.Value(lit))
            s = solver.Value(op["start"])
            rows.append({"Order": j["order"], "Item": j["item"], "Op_Seq": op["seq"],
                         "Qty": j["qty"], "Machine": m, "Group": machine_group(m),
                         "Routed_Machine": op["routed"],
                         "start_min": s, "end_min": solver.Value(op["end"]),
                         "Zone": fence_zone(start_minute_to_datetime(s, base_time), base_time),
                         "Fence_Rule": op["rule"],
                         "Prev_Machine": op["prev_machine"],
                         "Shift_Min": (s - op["min_start"]) if op["min_start"] is not None else 0})
    tasks = pd.DataFrame(rows)
    fence["frozen_shifted"] = int((tasks["Shift_Min"] > 0).sum())
    fence["slushy_moved"] = int(((tasks["Fence_Rule"] == "Slushy")
                                 & (tasks["Machine"] != tasks["Prev_Machine"])).sum())

    return {"status": status_name,
            "makespan": solver.Value(makespan),
            "total_tardiness": sum(solver.Value(t) for t in tardiness_vars),
            "tasks": tasks,
            "unschedulable": unschedulable,
            "fence": fence}


def to_calendar(tasks, base_time=None):
    """Expand solver tasks into calendar segments for the Gantt chart / CSV export."""
    base_time = base_time or next_monday_8am()
    out = []
    for t in tasks.itertuples():
        for seg in map_to_real_schedule(t.start_min, t.end_min - t.start_min, base_time):
            out.append({"Job": t.Order, "Item": t.Item, "Op_Seq": t.Op_Seq,
                        "Machine": t.Machine, "Group": t.Group,
                        "Zone": getattr(t, "Zone", ""),
                        "Start": seg["start"], "Finish": seg["end"],
                        "Duration (Mins)": seg["duration"]})
    return pd.DataFrame(out)


def publish_frame(tasks, base_time):
    """One row per operation with calendar start/end, to be saved as the published baseline."""
    df = tasks[["Order", "Item", "Op_Seq", "Qty", "Machine", "Group", "Zone"]].copy()
    df["Planned_Start"] = [start_minute_to_datetime(m, base_time) for m in tasks["start_min"]]
    df["Planned_End"] = [working_minute_to_datetime(m, base_time) for m in tasks["end_min"]]
    df["Hours"] = ((tasks["end_min"] - tasks["start_min"]) / 60).round(1)
    df["Plan_Start"] = base_time
    df["Published_At"] = datetime.datetime.now().replace(microsecond=0)
    return df.sort_values(["Machine", "Planned_Start"])


def dispatch_sheet(tasks, base_time, days=FROZEN_DAYS):
    """Per-machine job list for operations starting within the next `days` (the frozen week)."""
    pub = publish_frame(tasks, base_time)
    cutoff = base_time + datetime.timedelta(days=days)
    sheet = pub[pub["Planned_Start"] < cutoff].copy()
    sheet.insert(0, "Seq_No", sheet.groupby("Machine").cumcount() + 1)
    return sheet[["Machine", "Seq_No", "Order", "Item", "Op_Seq", "Qty",
                  "Planned_Start", "Planned_End", "Hours"]]


def ld_report(tasks, orders, base_time):
    """Per-order completion vs due date and projected liquidated damages (LD).

    orders needs Order_ID, Make_In_House_Qty, Due_Date, ld_rate_per_week,
    max_ld_percentage, contract_value_per_unit.
    LD = min(started weeks late x ld_rate_per_week, max_ld_percentage)
         x contract_value_per_unit x in-house qty
    """
    last_end = tasks.groupby("Order")["end_min"].max()
    rows = []
    for o in orders.itertuples():
        if o.Order_ID not in last_end.index:
            continue
        finish = working_minute_to_datetime(int(last_end[o.Order_ID]), base_time)
        due = pd.Timestamp(o.Due_Date) + pd.Timedelta(hours=18)
        days_late = max(0, math.ceil((finish - due).total_seconds() / 86400))
        weeks_late = math.ceil(days_late / 7)
        ld_pct = min(weeks_late * o.ld_rate_per_week, o.max_ld_percentage)
        rows.append({"Order_ID": o.Order_ID, "Due_Date": pd.Timestamp(o.Due_Date).date(),
                     "Planned_Finish": finish, "Days_Late": days_late,
                     "LD_%": round(ld_pct * 100, 2),
                     "Projected_LD_Rs": round(ld_pct * o.contract_value_per_unit * o.Make_In_House_Qty, 2)})
    if not rows:
        return pd.DataFrame(columns=["Order_ID", "Due_Date", "Planned_Finish", "Days_Late",
                                     "LD_%", "Projected_LD_Rs"])
    return pd.DataFrame(rows).sort_values(["Projected_LD_Rs", "Days_Late"], ascending=False)
