import pandas as pd
import math
from ortools.sat.python import cp_model

def solve_job_shop_makespan():
    print("Loading data...")
    # 1. Load Data
    decisions_df = pd.read_csv("Final_Make_Buy_Decisions.csv")
    routings_df = pd.read_csv("production_routings.csv")

    # Filter to only the orders we decided to manufacture in-house
    make_orders = decisions_df[decisions_df["Make_In_House_Qty"] > 0].copy()
    
    # 2. Build the Model
    model = cp_model.CpModel()
    
    # We need to track all interval variables assigned to each machine
    machine_intervals = {}
    
    # We need to track the end time of the very last task of every job to calculate Makespan
    job_ends = []
    
    print(f"Building schedule for {len(make_orders)} in-house orders...")
    
    for index, order in make_orders.iterrows():
        order_id = order["Order_ID"]
        item_id = order["Item_ID"]
        qty = order["Make_In_House_Qty"]
        
        # Get the sequence of operations for this specific item
        item_routings = routings_df[routings_df["item_id"] == item_id].sort_values("operation_sequence")
        
        previous_task_end = None
        
        for _, task in item_routings.iterrows():
            machine_id = task["machine_id"]
            
            # Calculate duration in minutes (CP-SAT requires integers)
            total_hours = task["setup_hours"] + (task["run_hours_per_unit"] * qty)
            duration_mins = int(math.ceil(total_hours * 60))
            
            # Create a suffix for variable names
            suffix = f"_{order_id}_{machine_id}"
            
            # Create the interval variable for this task
            start_var = model.NewIntVar(0, 99999999, f"start{suffix}")
            end_var = model.NewIntVar(0, 99999999, f"end{suffix}")
            interval_var = model.NewIntervalVar(start_var, duration_mins, end_var, f"interval{suffix}")
            
            # Precedence Constraint: This task cannot start until the previous task in this job ends
            if previous_task_end is not None:
                model.Add(start_var >= previous_task_end)
            
            previous_task_end = end_var
            
            # Add to the machine's list of tasks so we can prevent overlap later
            if machine_id not in machine_intervals:
                machine_intervals[machine_id] = []
            machine_intervals[machine_id].append(interval_var)
            
        # The end of the last task in this loop is the end of the entire job
        if previous_task_end is not None:
            job_ends.append(previous_task_end)

    # 3. Add Machine Constraints (No Overlap)
    print("Adding machine capacity constraints...")
    for machine_id, intervals in machine_intervals.items():
        model.AddNoOverlap(intervals)
        
    # 4. Set the Objective (Minimize Makespan)
    # Makespan is the maximum end time across all jobs
    makespan = model.NewIntVar(0, 99999999, "makespan")
    model.AddMaxEquality(makespan, job_ends)
    model.Minimize(makespan)
    
    # 5. Solve the Model
    print("Solving model...")
    solver = cp_model.CpSolver()
    
    # Optional: Set a time limit in seconds (useful for very large problems)
    solver.parameters.max_time_in_seconds = 60.0
    
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"\n--- SUCCESS ---")
        print(f"Status: {solver.StatusName(status)}")
        total_minutes = solver.ObjectiveValue()
        print(f"Optimal Makespan: {total_minutes} minutes ({total_minutes/60:.2f} hours)")
        print(f"Wall time: {solver.WallTime():.2f} seconds")
    else:
        print("The solver could not find a solution.")

if __name__ == "__main__":
    solve_job_shop_makespan()
