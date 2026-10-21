import sys

import pandas as pd

from fjssp_scheduler import solve_fjssp, WORK_MINUTES_PER_DAY


def solve_job_shop_makespan(time_limit=60.0):
    print("Loading data...")
    decisions_df = pd.read_csv("Final_Make_Buy_Decisions.csv")
    routings_df = pd.read_csv("production_routings.csv")
    machines_df = pd.read_csv("machine_capacities.csv")

    # Filter to only the orders we decided to manufacture in-house
    make_orders = decisions_df[decisions_df["Make_In_House_Qty"] > 0].copy()
    print(f"Building schedule for {len(make_orders)} in-house orders...")

    # Compare the old behaviour (step pinned to one machine) with the flexible job shop
    for label, flexible in [("Pinned machine (old)", False), ("Flexible job shop  ", True)]:
        res = solve_fjssp(make_orders, routings_df, machines_df, objective="makespan",
                          flexible=flexible, time_limit=time_limit)
        if res["makespan"] is None:
            print(f"{label}: no solution ({res['status']})")
            continue
        days = res["makespan"] / WORK_MINUTES_PER_DAY
        moved = 0
        if not res["tasks"].empty:
            moved = int((res["tasks"]["Machine"] != res["tasks"]["Routed_Machine"]).sum())
        print(f"{label}: status={res['status']:<8} makespan={res['makespan']} min "
              f"({days:.1f} working days)  tardiness={res['total_tardiness'] / WORK_MINUTES_PER_DAY:.1f} days  "
              f"ops moved to sister machine={moved}")
        if res["unschedulable"]:
            print(f"  Unschedulable operations: {res['unschedulable']}")


if __name__ == "__main__":
    solve_job_shop_makespan(float(sys.argv[1]) if len(sys.argv) > 1 else 60.0)
