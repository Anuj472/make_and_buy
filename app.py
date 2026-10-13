import streamlit as st
import pandas as pd
import pulp
import plotly.express as px

st.set_page_config(page_title="Make vs Buy Optimizer", page_icon="🏭", layout="wide")

st.title("🏭 Make vs. Buy Optimizer")
st.markdown("Optimize your supply chain by mathematically deciding which orders to manufacture in-house and which to outsource based on capacity and cost.")

def load_data():
    try:
        df_items = pd.read_csv("mto_item_master.csv")
        df_machines = pd.read_csv("machine_capacities.csv")
        df_routings = pd.read_csv("production_routings.csv")
        df_quotes = pd.read_csv("external_supplier_quotes.csv")
        df_orders = pd.read_csv("active_indents.csv")
        
        # New MCDM Tables
        df_strat = pd.read_csv("strategic_performance_data.csv")
        df_mgr = pd.read_csv("managerial_performance_data.csv")
        df_risk = pd.read_csv("sourcing_risk_data.csv")
        
        return df_items, df_machines, df_routings, df_quotes, df_orders, df_strat, df_mgr, df_risk
    except Exception as e:
        st.error(f"Error loading datasets: {e}")
        return None, None, None, None, None, None, None, None

df_items, df_machines, df_routings, df_quotes, df_orders, df_strat, df_mgr, df_risk = load_data()

if df_orders is not None:
    st.markdown("### 🎛️ Control Panel")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        run_milp = st.button("🚀 Run Make vs. Buy Optimizer", type="primary", use_container_width=True)
    with col_btn2:
        run_jobshop = st.button("🏭 Run Job Shop Scheduling", type="primary", use_container_width=True)
        
    if run_jobshop and 'df_results' not in st.session_state:
        try:
            st.session_state['df_results'] = pd.read_csv("Final_Make_Buy_Decisions.csv")
        except FileNotFoundError:
            st.warning("⚠️ No Make vs Buy decisions found. Please run the optimizer first.")
            run_jobshop = False
            
    if run_milp:
        st.session_state['active_view'] = 'make_buy'
        
    if run_jobshop:
        st.session_state['active_view'] = 'job_shop'
        
    active_view = st.session_state.get('active_view', 'make_buy')

    if active_view == 'make_buy':
        st.sidebar.header("🎯 Optimization Goal")
        st.sidebar.markdown("Select the primary objective for the solver:")
        opt_goal = st.sidebar.radio(
            "Choose Goal:",
            [
                "💰 Maximize Financial Performance", 
                "🛡️ Minimize Sourcing Risks",
                "👥 Maximize Managerial Performance",
                "🏆 Maximize Strategic Competitive Performance"
            ]
        )
        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ Constraints")
        capacity_multiplier = st.sidebar.slider("Machine Capacity Multiplier", 0.1, 2.0, 1.0, 0.1, help="Artificially increase or restrict factory capacity to see how the solver reacts.")
        scheduling_objective = "Minimize Makespan (Total Time)"
    else:
        st.sidebar.header("📅 Scheduling Goal")
        scheduling_objective = st.sidebar.radio("Choose Job Shop Goal:", ["Minimize Makespan (Total Time)", "Minimize Tardiness (Meet Due Dates)"])
        opt_goal = "💰 Maximize Financial Performance"
        capacity_multiplier = 1.0
        
    if run_milp:
        with st.spinner("Initializing PuLP Solver and building matrix..."):
            # Pre-Processing
            df = df_orders.merge(df_items, on="item_id")\
                          .merge(df_quotes, on="item_id")\
                          .merge(df_strat, on="item_id")\
                          .merge(df_mgr, on="item_id")\
                          .merge(df_risk, on="item_id")
            
            machine_net_cap = {}
            machine_rates = {}
            
            for _, row in df_machines.iterrows():
                m_id = row['machine_id']
                machine_net_cap[m_id] = max(0, row['available_yearly_hours'] - row['existing_wip_hours']) * capacity_multiplier
                machine_rates[m_id] = row['operating_cost_per_hour']
                
            df['true_buy_cost'] = df['vendor_price_per_unit'] + df['incoming_qa_cost_per_unit']
            
            # MILP Model
            model = pulp.LpProblem("IOL_Make_vs_Buy_Optimization", pulp.LpMinimize)
            
            make_vars = model.add_variable_dicts("Make", df['order_id'], lowBound=0, cat='Integer')
            buy_vars  = model.add_variable_dicts("Buy",  df['order_id'], lowBound=0, cat='Integer')
            is_make   = model.add_variable_dicts("IsMake", df['order_id'], cat='Binary')
            
            # Binary Link Constraint
            for _, row in df.iterrows():
                order = row['order_id']
                qty = row['order_quantity']
                model += make_vars[order] <= qty * is_make[order], f"Link_Upper_{order}"
                model += make_vars[order] >= is_make[order],       f"Link_Lower_{order}"
                
            objective_terms = []
            
            for _, row in df.iterrows():
                order = row['order_id']
                
                # --- Goal 1: Financial ---
                if "Financial" in opt_goal:
                    rm_cost = row['raw_material_cost_per_unit'] * (1 + row['expected_scrap_percentage'])
                    labor_cost = row.get('labor_cost_per_unit', 0)
                    make_penalty = rm_cost + labor_cost
                    buy_penalty = row['true_buy_cost']
                
                # --- Goal 2: Sourcing Risks ---
                # Paper states -8 is max negative risk, +8 is max positive.
                # To minimize risk in a minimization solver, we penalize negative scores.
                elif "Risks" in opt_goal:
                    risk_score = row['ip_leakage_risk'] + row['supplier_disruption_risk'] + row['appropriation_risk']
                    make_penalty = 0 # No external risk for making
                    buy_penalty = (24 - risk_score) # Shift score so a bad risk (-24) becomes a huge penalty (48)
                
                # --- Goal 3: Managerial Performance ---
                elif "Managerial" in opt_goal:
                    mgr_score = row['transaction_complexity'] + row['supplier_rel_value'] + row['customer_perception']
                    make_penalty = 0 
                    buy_penalty = (24 - mgr_score) # Shift score to penalize bad managerial outcomes
                
                # --- Goal 4: Strategic Competitive Performance ---
                elif "Strategic" in opt_goal:
                    # Penalize lead times and defect rates
                    make_penalty = row['internal_lead_time_days'] + (row['internal_defect_rate'] * 1000) - row['volume_flexibility_score']
                    buy_penalty = row['vendor_lead_time_days_x'] + (row['vendor_defect_rate'] * 1000)
                
                objective_terms.append(make_vars[order] * make_penalty)
                objective_terms.append(buy_vars[order] * buy_penalty)
                
            # Machine Constraints
            for m_id in machine_net_cap.keys():
                machine_usage = []
                for _, row in df.iterrows():
                    order = row['order_id']
                    item = row['item_id']
                    scrap_factor = 1 + row['expected_scrap_percentage']
                    
                    routing_step = df_routings[(df_routings['item_id'] == item) & (df_routings['machine_id'] == m_id)]
                    if not routing_step.empty:
                        run_hrs   = routing_step['run_hours_per_unit'].values[0]
                        setup_hrs = routing_step['setup_hours'].values[0]
                        rate = machine_rates[m_id]
                        
                        setup_used = is_make[order] * setup_hrs
                        run_used = make_vars[order] * run_hrs * scrap_factor
                        machine_usage.append(setup_used)
                        machine_usage.append(run_used)
                        
                        # Only add Machine Cost to objective if optimizing Financials
                        if "Financial" in opt_goal:
                            objective_terms.append(setup_used * rate)
                            objective_terms.append(run_used * rate)
                
                # Machine capacity constraint ALWAYS applies
                if machine_usage:
                    model += pulp.lpSum(machine_usage) <= machine_net_cap[m_id], f"CapLimit_{m_id}"
                    
            # Set Objective
            model += pulp.lpSum(objective_terms)
            
            # Demand & Strategic Constraints
            for _, row in df.iterrows():
                order = row['order_id']
                model += make_vars[order] + buy_vars[order] == row['order_quantity'], f"Demand_{order}"
                if row['is_critical_component']:
                    model += buy_vars[order] == 0, f"Strategic_Make_{order}"
                    
            # Solve
            stats = model.solve()
            
        if stats.status.name in ['Optimal', 'GapLimit']:
            # Extract Results
            results = []
            for _, row in df.iterrows():
                order = row['order_id']
                make_qty = make_vars[order].varValue
                buy_qty  = buy_vars[order].varValue
                results.append({
                    'Order_ID': order,
                    'Item_ID': row['item_id'],
                    'Demand': row['order_quantity'],
                    'Make_In_House_Qty': make_qty,
                    'Buy_External_Qty': buy_qty,
                    'Delivery_Period_Days': row['delivery_period_days'],
                    'Is_Critical': row['is_critical_component'],
                    'Decision': 'MAKE' if buy_qty == 0 else ('BUY' if make_qty == 0 else 'MAKE and BUY')
                })
            
            df_results = pd.DataFrame(results)
            df_results.to_csv("Final_Make_Buy_Decisions.csv", index=False)
            
            st.session_state['df_results'] = df_results
            st.session_state['milp_score'] = pulp.value(model.objective)
            st.session_state['milp_status'] = stats.status.name
            st.session_state['opt_goal_used'] = opt_goal
            
            # Clear old schedule if it exists
            if 'schedule_df' in st.session_state:
                del st.session_state['schedule_df']
                
        else:
            st.error(f"Solver failed to find an optimal solution. Status: {stats.status.name}")

if 'df_results' in st.session_state and st.session_state.get('active_view') == 'make_buy':
    df_results = st.session_state['df_results']
    
    if 'milp_status' in st.session_state:
        st.success(f"Make vs. Buy Optimization Complete! Status: {st.session_state['milp_status']} | Goal: {st.session_state['opt_goal_used']}")
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Optimal Penalty Score", f"{st.session_state['milp_score']:,.0f}")
        col2.metric("Total Items Made", f"{df_results['Make_In_House_Qty'].sum():.0f}")
        col3.metric("Total Items Bought", f"{df_results['Buy_External_Qty'].sum():.0f}")
        col4.metric("Split Orders", len(df_results[df_results['Decision'] == 'MAKE and BUY']))
    else:
        st.info("Loaded previous Make vs. Buy decisions from file.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Items Made", f"{df_results['Make_In_House_Qty'].sum():.0f}")
        col2.metric("Total Items Bought", f"{df_results['Buy_External_Qty'].sum():.0f}")
        col3.metric("Split Orders", len(df_results[df_results['Decision'] == 'MAKE and BUY']))
    
    # Charts
    st.markdown("### Decision Distribution")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_pie = px.pie(df_results, names='Decision', title='Order Level Decisions', color='Decision',
                         color_discrete_map={'MAKE':'#2E8B57', 'BUY':'#4682B4', 'MAKE and BUY':'#FF8C00'})
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_chart2:
        volume_df = pd.DataFrame({
            'Category': ['Make In-House', 'Buy External'],
            'Volume': [df_results['Make_In_House_Qty'].sum(), df_results['Buy_External_Qty'].sum()]
        })
        fig_bar = px.bar(volume_df, x='Category', y='Volume', title='Total Volume Distribution', 
                         color='Category', color_discrete_map={'Make In-House':'#2E8B57', 'Buy External':'#4682B4'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.markdown("### Final Order Decisions")
    st.dataframe(df_results, use_container_width=True)
    
# --- Job Shop Scheduling ---
if run_jobshop:
    with st.spinner("Generating Production Schedule via Google OR-Tools..."):
        import math
        from ortools.sat.python import cp_model
        import datetime
        
        def map_to_real_schedule(start_working_min, duration_mins, start_date):
            segments = []
            remaining_duration = duration_mins
            current_working_min = start_working_min
            
            while remaining_duration > 0:
                working_day = current_working_min // 600 # 10 hours = 600 mins
                min_in_day = current_working_min % 600
                
                weeks = working_day // 6 # 6 working days a week
                day_of_week = working_day % 6
                
                real_start = start_date + datetime.timedelta(days=weeks*7 + day_of_week) + datetime.timedelta(minutes=min_in_day)
                mins_left_in_day = 600 - min_in_day
                segment_duration = min(remaining_duration, mins_left_in_day)
                real_end = real_start + datetime.timedelta(minutes=segment_duration)
                
                segments.append({
                    "start": real_start,
                    "end": real_end,
                    "duration": segment_duration
                })
                
                remaining_duration -= segment_duration
                current_working_min += segment_duration
                
            return segments

        # We need df_results, so let's get it from session state
        df_results = st.session_state['df_results']
        make_orders = df_results[df_results["Make_In_House_Qty"] > 0].copy()
        
        if make_orders.empty:
            st.info("No items selected for in-house manufacturing.")
        else:
            model = cp_model.CpModel()
            machine_intervals = {}
            job_ends = []
            task_list = []
            all_tardiness = []
            
            for index, order in make_orders.iterrows():
                order_id = order["Order_ID"]
                item_id = order["Item_ID"]
                qty = order["Make_In_House_Qty"]
                # Default to 30 days if not found
                due_date_days = float(order.get("Delivery_Period_Days", 30))
                due_date_mins = int(math.ceil(due_date_days * 600))
                
                item_routings = df_routings[df_routings["item_id"] == item_id].sort_values("operation_sequence")
                previous_task_end = None
                
                for _, task in item_routings.iterrows():
                    machine_id = task["machine_id"]
                    total_hours = task["setup_hours"] + (task["run_hours_per_unit"] * qty)
                    duration_mins = int(math.ceil(total_hours * 60))
                    
                    suffix = f"_{order_id}_{machine_id}"
                    start_var = model.NewIntVar(0, 99999999, f"start{suffix}")
                    end_var = model.NewIntVar(0, 99999999, f"end{suffix}")
                    interval_var = model.NewIntervalVar(start_var, duration_mins, end_var, f"interval{suffix}")
                    
                    if previous_task_end is not None:
                        model.Add(start_var >= previous_task_end)
                    
                    previous_task_end = end_var
                    
                    if machine_id not in machine_intervals:
                        machine_intervals[machine_id] = []
                    machine_intervals[machine_id].append(interval_var)
                    
                    task_list.append({
                        "Order": order_id,
                        "Machine": machine_id,
                        "start_var": start_var,
                        "end_var": end_var
                    })
                    
                if previous_task_end is not None:
                    job_ends.append(previous_task_end)
                    
                    # Calculate Tardiness for this job
                    lateness_var = model.NewIntVar(-99999999, 99999999, f'lateness_{order_id}')
                    model.Add(lateness_var == previous_task_end - due_date_mins)
                    tardiness_var = model.NewIntVar(0, 99999999, f'tardiness_{order_id}')
                    model.AddMaxEquality(tardiness_var, [0, lateness_var])
                    all_tardiness.append(tardiness_var)

            for machine_id, intervals in machine_intervals.items():
                model.AddNoOverlap(intervals)
                
            makespan = model.NewIntVar(0, 99999999, "makespan")
            model.AddMaxEquality(makespan, job_ends)
            
            if "Minimize Tardiness" in scheduling_objective:
                model.Minimize(sum(all_tardiness))
            else:
                model.Minimize(makespan)
                
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30.0
            status = solver.Solve(model)
            
            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                makespan_days = solver.Value(makespan) / 600
                if "Minimize Tardiness" in scheduling_objective:
                    st.success(f"Schedule Optimization Complete!  \n**Total Tardiness Penalty:** {solver.ObjectiveValue() / 600:.2f} working days  \n**Total Makespan (Completion Time):** {makespan_days:.2f} working days")
                else:
                    st.success(f"Schedule Optimization Complete! Optimal Makespan: {solver.ObjectiveValue() / 600:.2f} working days")
                
                schedule_data = []
                # Base time is next Monday 8:00 AM
                today = datetime.datetime.today()
                days_ahead = 0 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                base_time = (today + datetime.timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0, microsecond=0)
                
                for t in task_list:
                    start_min = solver.Value(t["start_var"])
                    end_min = solver.Value(t["end_var"])
                    duration = end_min - start_min
                    
                    segments = map_to_real_schedule(start_min, duration, base_time)
                    
                    for seg in segments:
                        schedule_data.append({
                            "Job": t["Order"],
                            "Machine": t["Machine"],
                            "Start": seg["start"],
                            "Finish": seg["end"],
                            "Duration (Mins)": seg["duration"]
                        })
                    
                df_schedule = pd.DataFrame(schedule_data)
                df_schedule = df_schedule.sort_values(by=["Machine", "Start"])
                st.session_state['schedule_df'] = df_schedule
            else:
                st.error("The scheduler could not find a valid schedule.")

if 'schedule_df' in st.session_state and st.session_state.get('active_view') == 'job_shop':
    df_schedule = st.session_state['schedule_df']
    
    st.markdown("---")
    st.markdown("### 🖨️ Print & View Schedule (8AM - 6PM, Mon-Sat)")
    
    df_schedule['Month'] = df_schedule['Start'].dt.strftime('%Y-%m')
    # Use %G for ISO year instead of %Y to prevent Dec 31 bugs with ISO weeks
    df_schedule['Week'] = df_schedule['Start'].dt.strftime('%G-W%V')
    
    col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1.5])
    
    with col1:
        machines = ["All Machines"] + sorted(list(df_schedule['Machine'].unique()))
        selected_machine = st.selectbox("Filter by Machine:", machines)
        
    # Cascade filtering down to Month
    display_df = df_schedule.copy()
    if selected_machine != "All Machines":
        display_df = display_df[display_df['Machine'] == selected_machine]
        
    with col2:
        months = ["All Months"] + sorted(list(display_df['Month'].unique()))
        selected_month = st.selectbox("Filter by Month:", months)
        
    # Cascade filtering down to Week
    if selected_month != "All Months":
        display_df = display_df[display_df['Month'] == selected_month]
        
    with col3:
        weeks = ["All Weeks"] + sorted(list(display_df['Week'].unique()))
        selected_week = st.selectbox("Filter by Week:", weeks)
        
    # Final filter applied
    if selected_week != "All Weeks":
        display_df = display_df[display_df['Week'] == selected_week]
        
    fig_gantt = px.timeline(display_df, x_start="Start", x_end="Finish", y="Machine", color="Job",
                            title=f"In-House Production Schedule",
                            hover_data=["Duration (Mins)"])
    fig_gantt.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_gantt, use_container_width=True)
    
    # Drop the helper columns for clean display/export
    export_df = display_df.drop(columns=['Month', 'Week'])
    st.dataframe(export_df, use_container_width=True)
    
    csv = export_df.to_csv(index=False).encode('utf-8')
    with col4:
        st.markdown("<br>", unsafe_allow_html=True) # visual spacing
        st.download_button(
            label="📥 Download Schedule as CSV",
            data=csv,
            file_name=f'production_schedule.csv',
            mime='text/csv',
        )
