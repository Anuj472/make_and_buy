import os
import datetime
import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
import importlib
import fjssp_scheduler as fs
importlib.reload(fs)

PUBLISHED_PLAN_FILE = "schedule_published.csv"
PUBLISHED_HISTORY_DIR = "published_plans"

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
        run_milp = st.button("🚀 Run Make vs. Buy Optimizer", type="primary", width="stretch")
    with col_btn2:
        run_jobshop = st.button("🏭 Run Job Shop Scheduling", type="primary", width="stretch")
        
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
        allow_parallel = True
        down_machines = []
        plan_start = fs.next_monday_8am()
        use_baseline = False
    else:
        st.sidebar.header("📅 Scheduling Goal")
        scheduling_objective = st.sidebar.radio("Choose Job Shop Goal:", ["Minimize Makespan (Total Time)", "Minimize Tardiness (Meet Due Dates)", "Minimize LD Penalty (₹ Late-Delivery Damages)"])
        st.sidebar.markdown("---")
        st.sidebar.header("🔀 Machine Flexibility")
        allow_parallel = st.sidebar.checkbox(
            "Allow sister machines in same group", value=True,
            help="Flexible Job Shop: an operation routed to CNC_MILL_3 may run on any active CNC_MILL machine. Untick to pin each step to its routing machine (old behaviour).")
        down_machines = st.sidebar.multiselect(
            "Machines down / unavailable", sorted(df_machines['machine_id'].tolist()),
            help="Excluded from scheduling. With flexibility on, their work moves to sister machines.")
        st.sidebar.markdown("---")
        st.sidebar.header("🧊 Time Fences")
        st.sidebar.caption(f"❄️ Frozen: week 1 (first {fs.FROZEN_DAYS} days) · 🧊 Slushy: weeks 2–4 · 💧 Liquid: week 5+")
        plan_date = st.sidebar.date_input("Plan start date (08:00)", value=fs.next_monday_8am().date(),
                                          help="Re-plan from this date. Move it forward a week to simulate the next weekly re-plan.")
        if plan_date.weekday() == 6:   # Sunday is not a working day
            plan_date = plan_date + datetime.timedelta(days=1)
            st.sidebar.caption("Sunday selected, plan starts Monday.")
        plan_start = datetime.datetime.combine(plan_date, datetime.time(fs.WORK_START_HOUR))
        use_baseline = False
        if os.path.exists(PUBLISHED_PLAN_FILE):
            pub_info = pd.read_csv(PUBLISHED_PLAN_FILE, nrows=1)
            use_baseline = st.sidebar.checkbox(
                "Respect published plan (apply fences)", value=True,
                help="Frozen ops keep their machine and can only move later. Slushy ops may change machine within the group (discouraged). Liquid ops are free.")
            if len(pub_info):
                st.sidebar.caption(f"Published plan: start {pub_info['Plan_Start'][0]}, published {pub_info['Published_At'][0]}")
        else:
            st.sidebar.caption("No published plan yet. Publish one below the schedule to start using fences.")
        st.sidebar.caption("Change settings, then click 'Run Job Shop Scheduling' again.")
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
        st.plotly_chart(fig_pie, width="stretch")
        
    with col_chart2:
        volume_df = pd.DataFrame({
            'Category': ['Make In-House', 'Buy External'],
            'Volume': [df_results['Make_In_House_Qty'].sum(), df_results['Buy_External_Qty'].sum()]
        })
        fig_bar = px.bar(volume_df, x='Category', y='Volume', title='Total Volume Distribution', 
                         color='Category', color_discrete_map={'Make In-House':'#2E8B57', 'Buy External':'#4682B4'})
        st.plotly_chart(fig_bar, width="stretch")
        
    st.markdown("### Final Order Decisions")
    st.dataframe(df_results, width="stretch")
    
# --- Job Shop Scheduling ---
if run_jobshop:
    with st.spinner("Generating Flexible Job Shop schedule via Google OR-Tools..."):
        solve_fjssp = fs.solve_fjssp
        to_calendar = fs.to_calendar
        ld_report = fs.ld_report
        next_monday_8am = fs.next_monday_8am
        WORK_MINUTES_PER_DAY = fs.WORK_MINUTES_PER_DAY

        # We need df_results, so let's get it from session state
        df_results = st.session_state['df_results']
        make_orders = df_results[df_results["Make_In_House_Qty"] > 0].copy()

        # Calendar due date = indent date + delivery period; LD terms from the indent
        indent_cols = ['order_id', 'order_date', 'ld_rate_per_week', 'max_ld_percentage', 'contract_value_per_unit']
        if set(indent_cols).issubset(df_orders.columns):
            make_orders = make_orders.merge(df_orders[indent_cols], left_on='Order_ID', right_on='order_id', how='left')
            make_orders['Due_Date'] = pd.to_datetime(make_orders['order_date']) + pd.to_timedelta(make_orders['Delivery_Period_Days'], unit='D')
            # rupees of LD per week late (linear approximation used by the solver)
            make_orders['LD_Weight'] = make_orders['contract_value_per_unit'] * make_orders['Make_In_House_Qty'] * make_orders['ld_rate_per_week']

        if make_orders.empty:
            st.info("No items selected for in-house manufacturing.")
        else:
            if "LD Penalty" in scheduling_objective:
                objective = "ld"
            elif "Minimize Tardiness" in scheduling_objective:
                objective = "tardiness"
            else:
                objective = "makespan"
            base_time = plan_start
            baseline = None
            if use_baseline and os.path.exists(PUBLISHED_PLAN_FILE):
                baseline = pd.read_csv(PUBLISHED_PLAN_FILE, parse_dates=['Planned_Start', 'Planned_End'])
            res = solve_fjssp(make_orders, df_routings, df_machines, objective=objective,
                              flexible=allow_parallel, down_machines=down_machines,
                              time_limit=30.0, base_time=base_time, baseline=baseline)

            if res["unschedulable"]:
                st.warning("Some orders were skipped because no active machine can run a step: "
                           + ", ".join(f"{o} op{s} ({m})" for o, s, m in res["unschedulable"]))

            if res["makespan"] is not None:
                makespan_days = res["makespan"] / WORK_MINUTES_PER_DAY
                tard_days = res["total_tardiness"] / WORK_MINUTES_PER_DAY
                tasks = res["tasks"]
                moved = int((tasks["Machine"] != tasks["Routed_Machine"]).sum())
                mode = "Flexible (sister machines allowed)" if allow_parallel else "Pinned to routing machine"
                st.success(f"Schedule Optimization Complete! ({res['status']}, {mode})  \n"
                           f"**Total Makespan (Completion Time):** {makespan_days:.2f} working days  \n"
                           f"**Total Tardiness:** {tard_days:.2f} working days  \n"
                           f"**Operations moved to a sister machine:** {moved} of {len(tasks)}")

                df_schedule = to_calendar(tasks, base_time)
                df_schedule = df_schedule.sort_values(by=["Machine", "Start"])
                st.session_state['schedule_df'] = df_schedule
                st.session_state['tasks'] = tasks
                st.session_state['plan_base'] = base_time
                st.session_state['fence'] = res['fence']
                if res['fence']['overrides']:
                    st.warning("Frozen work released because its machine is down: "
                               + ", ".join(f"{o} op{s} ({m})" for o, s, m in res['fence']['overrides']))
                if 'Due_Date' in make_orders.columns:
                    st.session_state['ld_df'] = ld_report(tasks, make_orders, base_time)
                else:
                    st.session_state.pop('ld_df', None)
            else:
                st.error(f"The scheduler could not find a valid schedule ({res['status']}).")

if 'schedule_df' in st.session_state and st.session_state.get('active_view') == 'job_shop':
    df_schedule = st.session_state['schedule_df']

    # ---- Time fences: summary, publish, dispatch sheet ---------------------
    if 'tasks' in st.session_state:
        tasks = st.session_state['tasks']
        plan_base = st.session_state['plan_base']
        fence = st.session_state.get('fence', {})
        st.markdown("---")
        st.markdown(f"### 🧊 Time Fences (plan start {plan_base:%a %d %b %Y, %H:%M})")
        zc = tasks['Zone'].value_counts()
        f1, f2, f3 = st.columns(3)
        f1.metric("❄️ Frozen ops (week 1)", int(zc.get('Frozen', 0)))
        f2.metric("🧊 Slushy ops (weeks 2–4)", int(zc.get('Slushy', 0)))
        f3.metric("💧 Liquid ops (week 5+)", int(zc.get('Liquid', 0)))
        if fence.get('applied'):
            c = fence['counts']
            st.info(f"Re-planned against the published plan: "
                    f"{c.get('Finished', 0)} ops finished and dropped · {c.get('In progress', 0)} in progress kept · "
                    f"{c.get('Frozen', 0)} frozen locked ({fence.get('frozen_shifted', 0)} pushed later) · "
                    f"{fence.get('slushy_moved', 0)} of {c.get('Slushy', 0)} slushy moved machine · "
                    f"{c.get('New', 0)} new ops placed from week 2 · {len(fence.get('overrides', []))} frozen released (machine down)")
        else:
            st.caption("Fences not applied in this run (no published plan, or 'Respect published plan' is off). "
                       "Publish this plan to lock week 1 for the next re-plan.")

        if st.button("📌 Publish this plan as the baseline", type="primary"):
            pub = fs.publish_frame(tasks, plan_base)
            pub.to_csv(PUBLISHED_PLAN_FILE, index=False)
            os.makedirs(PUBLISHED_HISTORY_DIR, exist_ok=True)
            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            pub.to_csv(os.path.join(PUBLISHED_HISTORY_DIR, f"plan_{stamp}.csv"), index=False)
            st.success(f"Published {len(pub)} operations to {PUBLISHED_PLAN_FILE} (copy kept in {PUBLISHED_HISTORY_DIR}/). "
                       "Next runs with 'Respect published plan' will keep week 1 fixed.")

        st.markdown("#### 📋 Machine Dispatch Sheet (frozen week)")
        sheet = fs.dispatch_sheet(tasks, plan_base)
        d1, d2 = st.columns([2, 1])
        with d1:
            disp_machine = st.selectbox("Machine:", sorted(sheet['Machine'].unique()) if len(sheet) else ["(none)"],
                                        key="dispatch_machine")
        with d2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("📥 Download all dispatch sheets (CSV)", sheet.to_csv(index=False).encode('utf-8'),
                               file_name=f"dispatch_{plan_base:%Y%m%d}.csv", mime='text/csv')
        st.dataframe(sheet[sheet['Machine'] == disp_machine].drop(columns=['Machine']),
                     width="stretch", hide_index=True)

    if 'ld_df' in st.session_state:
        ld_df = st.session_state['ld_df']
        late = ld_df[ld_df['Days_Late'] > 0]
        st.markdown("---")
        st.markdown("### ⚖️ Delivery Risk & Projected LD (due = indent date + delivery period)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Orders Late", f"{len(late)} of {len(ld_df)}")
        c2.metric("Projected LD", f"₹{ld_df['Projected_LD_Rs'].sum():,.0f}")
        c3.metric("Worst Delay", f"{int(ld_df['Days_Late'].max()) if len(ld_df) else 0} days")
        st.dataframe(ld_df, width="stretch", hide_index=True)
    
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
                            hover_data=["Item", "Op_Seq", "Group", "Zone", "Duration (Mins)"])
    fig_gantt.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_gantt, width="stretch")
    
    # Drop the helper columns for clean display/export
    export_df = display_df.drop(columns=['Month', 'Week'])
    st.dataframe(export_df, width="stretch")
    
    csv = export_df.to_csv(index=False).encode('utf-8')
    with col4:
        st.markdown("<br>", unsafe_allow_html=True) # visual spacing
        st.download_button(
            label="📥 Download Schedule as CSV",
            data=csv,
            file_name=f'production_schedule.csv',
            mime='text/csv',
        )
