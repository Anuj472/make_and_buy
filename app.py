import streamlit as st
import pandas as pd
import pulp
import plotly.express as px

st.set_page_config(page_title="Make vs Buy Optimizer", page_icon="🏭", layout="wide")

st.title("🏭 Intelligent Make vs. Buy Optimizer")
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
    st.sidebar.header("🎯 Optimization Goal")
    st.sidebar.markdown("Select the primary objective for the solver:")
    
    # Selectable buttons (Radio)
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
    
    if st.button("🚀 Run MILP Optimization", type="primary"):
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
            st.success(f"Optimization Complete! Status: {stats.status.name} | Goal: {opt_goal}")
            
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
                    'Is_Critical': row['is_critical_component'],
                    'Decision': 'MAKE' if buy_qty == 0 else ('BUY' if make_qty == 0 else 'MAKE and BUY')
                })
            
            df_results = pd.DataFrame(results)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Optimal Penalty Score", f"{pulp.value(model.objective):,.0f}")
            col2.metric("Total Items Made", f"{df_results['Make_In_House_Qty'].sum():.0f}")
            col3.metric("Total Items Bought", f"{df_results['Buy_External_Qty'].sum():.0f}")
            col4.metric("Split Orders", len(df_results[df_results['Decision'] == 'MAKE and BUY']))
            
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
            
        else:
            st.error(f"Solver failed to find an optimal solution. Status: {stats.status.name}")
