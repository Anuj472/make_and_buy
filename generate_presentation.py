import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # Blank slide

    # Color Palette
    C_DARK_NAVY = RGBColor(15, 23, 42)       # #0f172a
    C_SLATE_BG  = RGBColor(241, 245, 249)    # #f1f5f9
    C_CARD_BG   = RGBColor(255, 255, 255)    # #ffffff
    C_BORDER    = RGBColor(226, 232, 240)    # #e2e8f0
    C_PRIMARY   = RGBColor(37, 99, 235)      # #2563eb
    C_PRIMARY_LIGHT = RGBColor(239, 246, 255)# #eff6ff
    C_TEAL      = RGBColor(13, 148, 136)     # #0d9488
    C_AMBER     = RGBColor(217, 119, 6)      # #d97706
    C_TEXT_MAIN = RGBColor(30, 41, 59)       # #1e293b
    C_TEXT_MUTED= RGBColor(100, 116, 139)    # #64748b
    C_WHITE     = RGBColor(255, 255, 255)

    def add_header(slide, title, category="SYSTEM OVERVIEW"):
        # Header banner or clean text
        # Category pill
        pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.4), Inches(2.8), Inches(0.35))
        pill.fill.solid()
        pill.fill.fore_color.rgb = C_PRIMARY_LIGHT
        pill.line.color.rgb = C_PRIMARY
        pill.line.width = Pt(1)
        tf_pill = pill.text_frame
        tf_pill.word_wrap = True
        p_pill = tf_pill.paragraphs[0]
        p_pill.text = category.upper()
        p_pill.font.size = Pt(10)
        p_pill.font.bold = True
        p_pill.font.color.rgb = C_PRIMARY
        p_pill.alignment = PP_ALIGN.CENTER
        
        # Title
        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(0.7))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = C_DARK_NAVY

    def add_card(slide, left, top, width, height, bg_color=C_CARD_BG, border_color=C_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
        return card

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Navy Background)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_DARK_NAVY
    bg1.line.fill.background()

    # Title Card Accent
    pill1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(1.5), Inches(3.8), Inches(0.45))
    pill1.fill.solid()
    pill1.fill.fore_color.rgb = RGBColor(30, 58, 138)
    pill1.line.color.rgb = C_PRIMARY
    p_p1 = pill1.text_frame.paragraphs[0]
    p_p1.text = "MANUFACTURING OPERATIONS & PLANNING"
    p_p1.font.size = Pt(11)
    p_p1.font.bold = True
    p_p1.font.color.rgb = RGBColor(147, 197, 253)
    p_p1.alignment = PP_ALIGN.CENTER

    tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(2.6))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p1_t = tf1.paragraphs[0]
    p1_t.text = "Whole-Factory Optimal Process Scheduling\n& Operations Framework"
    p1_t.font.size = Pt(36)
    p1_t.font.bold = True
    p1_t.font.color.rgb = C_WHITE

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "\nUnifying Make-vs-Buy Decisions, Flexible Job Shop Optimization, and Human-in-the-Loop Shop Floor Execution"
    p1_sub.font.size = Pt(16)
    p1_sub.font.color.rgb = RGBColor(203, 213, 225)

    # 3 Summary Stat/Pillar Badges
    b_data = [
        ("PART I: IMPLEMENTED", "Make vs Buy MILP + Baseline JSSP", C_PRIMARY),
        ("PART II: IN-PLANNING", "Flexible Job Shop + Cart Logistics", C_TEAL),
        ("REALITY GROUNDING", "No AGVs / No IoT: Human-in-the-Loop", C_AMBER)
    ]
    for i, (head, desc, color) in enumerate(b_data):
        bx = add_card(s1, Inches(1.2 + i*3.8), Inches(5.2), Inches(3.5), Inches(1.4), bg_color=RGBColor(30, 41, 59), border_color=color)
        tb = s1.shapes.add_textbox(Inches(1.3 + i*3.8), Inches(5.3), Inches(3.3), Inches(1.2))
        tbf = tb.text_frame
        tbf.word_wrap = True
        p_h = tbf.paragraphs[0]
        p_h.text = head
        p_h.font.size = Pt(11)
        p_h.font.bold = True
        p_h.font.color.rgb = color
        p_d = tbf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(13)
        p_d.font.color.rgb = C_WHITE

    # =========================================================================
    # SLIDE 2: Executive Summary & Project Architecture
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Executive Architecture: From Orders to Machine Execution", "System Overview")

    # Card 1: The Industrial Challenge
    add_card(s2, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.2))
    tb2_1 = s2.shapes.add_textbox(Inches(1.0), Inches(1.9), Inches(5.2), Inches(4.8))
    tf2_1 = tb2_1.text_frame
    tf2_1.word_wrap = True
    p = tf2_1.paragraphs[0]
    p.text = "The Industrial Challenge & Local Optima"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    bullets2_1 = [
        ("Siloed Decisions Fail: ", "Deciding Make-vs-Buy purely on annual machine capacity creates unexecutable shop-floor blockages."),
        ("Physical Coupling: ", "A CNC machine cannot cut without raw blanks wheeled from stores, tooling fixtures, and qualified machinists."),
        ("Bottleneck Propagation: ", "If intermediate staging racks are full, upstream machines are physically blocked from unloading."),
        ("Factory Reality: ", "Precision optical & CNC shops do not have multimillion-dollar AGVs or IoT streaming telemetry. Scheduling must work with manual carts and supervisor shift feedback.")
    ]
    for bold_txt, norm_txt in bullets2_1:
        p = tf2_1.add_paragraph()
        p.space_before = Pt(10)
        run_b = p.add_run()
        run_b.text = bold_txt
        run_b.font.bold = True
        run_b.font.size = Pt(13)
        run_b.font.color.rgb = C_TEXT_MAIN
        run_n = p.add_run()
        run_n.text = norm_txt
        run_n.font.size = Pt(13)
        run_n.font.color.rgb = C_TEXT_MUTED

    # Card 2: The Two-Pillar Solution Architecture
    add_card(s2, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2))
    tb2_2 = s2.shapes.add_textbox(Inches(7.0), Inches(1.9), Inches(5.3), Inches(4.8))
    tf2_2 = tb2_2.text_frame
    tf2_2.word_wrap = True
    p = tf2_2.paragraphs[0]
    p.text = "Integrated Two-Pillar Framework"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_TEAL

    bullets2_2 = [
        ("Pillar 1: Implemented Baseline (Code Active)", "\n• Order-Level Make vs Buy MILP (PuLP)\n• Multi-Criteria Decision Making (MCDM: Risk, Strategy, Finance)\n• Baseline CP-SAT Job Shop Scheduler\n• Streamlit Interactive Operations Dashboard"),
        ("Pillar 2: In-Planning Target (Whole Factory)", "\n• Flexible Job Shop (Parallel CNC/Polishing Machine Pools)\n• Sequence-Dependent Setup Times (SDST Changeovers)\n• Inter-Bay Cart Transit & Staging Buffer Capacities\n• Vacuum Coating Batching & Thermal Curing Rules\n• Human-in-the-Loop Disruption Repair (Right-Shift & Re-Solve)")
    ]
    for bold_txt, norm_txt in bullets2_2:
        p = tf2_2.add_paragraph()
        p.space_before = Pt(12)
        run_b = p.add_run()
        run_b.text = bold_txt
        run_b.font.bold = True
        run_b.font.size = Pt(14)
        run_b.font.color.rgb = C_DARK_NAVY
        run_n = p.add_run()
        run_n.text = norm_txt
        run_n.font.size = Pt(12)
        run_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 3: Part I (Implemented) — Make vs Buy Optimizer
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Implemented: Make vs. Buy Multi-Criteria Optimizer", "Part I: Work Completed")

    # 3 Horizontal Cards
    c3_w = Inches(3.7)
    c3_h = Inches(5.2)

    # Card 1: Core Problem & Inputs
    add_card(s3, Inches(0.8), Inches(1.7), c3_w, c3_h)
    tb = s3.shapes.add_textbox(Inches(0.95), Inches(1.85), Inches(3.4), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Mathematical Formulation"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    bullets3_1 = [
        ("Solver Engine: ", "PuLP Mixed-Integer Linear Programming (MILP)."),
        ("Decision Variables: ", "Integer Make_vars[i] and Buy_vars[i], linked by Binary IsMake[i]."),
        ("Strict Demand Fulfill: ", "Make[i] + Buy[i] == Order_Qty[i]."),
        ("Capacity Handshake: ", "Machine net capacity limits:\nSum(Setup + Run * (1 + Scrap)) <= Available_Hours."),
        ("Critical Policy: ", "Critical items strictly forbidden from external purchase (Buy[i] == 0).")
    ]
    for b_t, n_t in bullets3_1:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(11)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(11)
        r_n.font.color.rgb = C_TEXT_MUTED

    # Card 2: 4 MCDM Strategic Goals
    add_card(s3, Inches(4.8), Inches(1.7), c3_w, c3_h)
    tb = s3.shapes.add_textbox(Inches(4.95), Inches(1.85), Inches(3.4), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "4 Selectable MCDM Goals"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_TEAL

    goals = [
        ("💰 Financial Performance: ", "Minimizes raw materials, direct labor, machine runtime costs, and vendor purchase prices."),
        ("🛡️ Sourcing Risk: ", "Penalizes IP leakage, vendor financial instability, and supplier disruption risk (-8 to +8 scale)."),
        ("👥 Managerial Performance: ", "Optimizes transaction complexity, supplier relationship value, and customer perception."),
        ("🏆 Strategic Competitiveness: ", "Penalizes external lead times and vendor defect rates while rewarding internal volume flexibility.")
    ]
    for b_t, n_t in goals:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(11)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(11)
        r_n.font.color.rgb = C_TEXT_MUTED

    # Card 3: Dashboard Outputs
    add_card(s3, Inches(8.8), Inches(1.7), c3_w, c3_h)
    tb = s3.shapes.add_textbox(Inches(8.95), Inches(1.85), Inches(3.4), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Interactive Deliverables"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_DARK_NAVY

    outputs = [
        ("Order-Level Tagging: ", "Categorizes orders automatically into MAKE, BUY, or MAKE & BUY."),
        ("Executive KPI Cards: ", "Instant readouts for Total Units Made, Units Bought, Optimal Penalty Score, and Split Orders."),
        ("Decision Distribution: ", "Interactive Plotly Pie and Bar charts visualizing volume splits."),
        ("Scenario Stress-Testing: ", "Machine capacity slider (0.1x to 2.0x) to test bottleneck shocks."),
        ("Output File: ", "Exports decisions directly to Final_Make_Buy_Decisions.csv for scheduling.")
    ]
    for b_t, n_t in outputs:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(11)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(11)
        r_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 4: Part I (Implemented) — Baseline Job Shop Scheduler
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Implemented: Baseline Job Shop Scheduler (CP-SAT)", "Part I: Work Completed")

    add_card(s4, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.2))
    tb = s4.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Constraint Programming Formulation"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    bullets4_1 = [
        ("Engine: ", "Google OR-Tools CP-SAT (Constraint Programming with SAT solver)."),
        ("Order Filtration: ", "Pulls all orders where Make_In_House_Qty > 0 from Make/Buy decisions."),
        ("Task Duration Logic: ", "Duration = Setup_Hours + (Run_Hours_Per_Unit * Qty). Formulated in integer minutes."),
        ("Machine Interval Variables: ", "IntervalVar(start, duration, end) with AddNoOverlap across each machine's operations."),
        ("Job Precedence: ", "Strict chain start_var(op_k+1) >= end_var(op_k)."),
        ("Dual Objective Modes: ", "Minimizes Total Makespan (C_max) OR Total Weighted Due-Date Tardiness (sum max(0, C_i - d_i)).")
    ]
    for b_t, n_t in bullets4_1:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    add_card(s4, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2))
    tb = s4.shapes.add_textbox(Inches(7.0), Inches(1.85), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Factory Working Calendar & UI Visualization"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_TEAL

    bullets4_2 = [
        ("Real Working Calendar Mapping: ", "Maps integer solver minutes into 10-hour working days (8:00 AM - 6:00 PM), 6 days a week (Monday to Saturday, Sundays closed)."),
        ("Interactive Multi-Track Gantt: ", "Visualizes full production schedule color-coded by Job ID using Plotly Timeline."),
        ("Cascade Shift Filters: ", "Enables shop supervisors to filter by Machine -> Month -> ISO Week for granular views."),
        ("Export Capabilities: ", "One-click download of production_schedule.csv formatted with exact Start/Finish timestamps for shop management.")
    ]
    for b_t, n_t in bullets4_2:
        p = tf.add_paragraph()
        p.space_before = Pt(10)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 5: Baseline Limitations & The Gap to Whole-Factory Optimization
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Current Code Limitations: Why Whole-Factory Planning Is Needed", "Gap Analysis")

    # Table comparing Current vs Problem
    gaps = [
        ("1. Single-Machine Routing", "Routings specify only 1 machine (e.g. CNC_MILL).", "Completely ignores parallel machines (CNC_MILL_2..5), artificially causing 4x longer makespans."),
        ("2. Zero Material Transit", "Transit time between machines is assumed to be 0 mins.", "Ignores the 15-30 min trolley travel, part washing, and deburring between machine bays."),
        ("3. Static Setup Times", "Fixed setup hours per item regardless of sequence.", "Fails to model sequence-dependent changeovers (e.g., lens polisher tooling & fixture swaps)."),
        ("4. Infinite Buffers", "Buffers between machines are assumed infinite (UIS).", "In reality, buffer racks hold 2-3 carts. If full, upstream machines are physically blocked."),
        ("5. Open-Loop Scheduling", "Static schedule solved once in batch mode.", "When a machine fails or an operator is delayed, the schedule shatters with no repair mechanism.")
    ]

    for i, (dim, curr, prob) in enumerate(gaps):
        add_card(s5, Inches(0.8), Inches(1.7 + i*1.05), Inches(11.7), Inches(0.95))
        tb = s5.shapes.add_textbox(Inches(1.0), Inches(1.75 + i*1.05), Inches(11.3), Inches(0.85))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = dim + "  |  "
        r1.font.bold = True
        r1.font.size = Pt(13)
        r1.font.color.rgb = C_PRIMARY
        r2 = p.add_run()
        r2.text = "Current: " + curr + "   -->   "
        r2.font.size = Pt(12)
        r2.font.color.rgb = C_TEXT_MUTED
        r3 = p.add_run()
        r3.text = "Impact: " + prob
        r3.font.bold = True
        r3.font.size = Pt(12)
        r3.font.color.rgb = C_AMBER

    # =========================================================================
    # SLIDE 6: Part II (In-Planning) — The 4-Layer Process Framework
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "In-Planning: 4-Layer Cyber-Physical Architecture (ISA-95)", "Part II: Target Roadmap")

    layers = [
        ("Layer 1: Enterprise Layer (ERP / SCM)", "Master Production Schedule (MPS) & Material Requirements (MRP)", "Ingests customer purchase orders, committed delivery SLAs, and supplier component lead times.", C_DARK_NAVY),
        ("Layer 2: Advanced Planning & Scheduling (APS)", "Global Optimization Engine (PuLP MILP + Master Planning)", "Executes finite-capacity planning, decides Make-vs-Buy, and feeds certified promise dates back to ERP.", C_PRIMARY),
        ("Layer 3: Practical MES & Reactive Engine", "Tri-Controller Coordination (Process, FJSSP, Material Handling)", "Process Controller (Chamber batching) + FJSSP Sequencer (Parallel machines) + Cart Staging Coordinator.", C_TEAL),
        ("Layer 4: Real Shop Floor Execution", "Human-in-the-Loop Feedback (Shift Work-Lists & Supervisor Console)", "Daily machine dispatch sheets, trolley transfer tickets, and supervisor 1-click disruption repair.", C_AMBER)
    ]
    for i, (l_title, l_sub, l_desc, col) in enumerate(layers):
        add_card(s6, Inches(0.8), Inches(1.7 + i*1.3), Inches(11.7), Inches(1.15), border_color=col)
        tb = s6.shapes.add_textbox(Inches(1.0), Inches(1.8 + i*1.3), Inches(11.3), Inches(0.95))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = l_title + "  —  "
        r1.font.bold = True
        r1.font.size = Pt(14)
        r1.font.color.rgb = col
        r2 = p.add_run()
        r2.text = l_sub
        r2.font.bold = True
        r2.font.size = Pt(13)
        r2.font.color.rgb = C_TEXT_MAIN
        p2 = tf.add_paragraph()
        p2.text = l_desc
        p2.font.size = Pt(12)
        p2.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 7: In-Planning Phase 1 — Flexible Job Shop & Setup Times
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Phase 1: Flexible Job Shop (FJSSP) & Sequence-Dependent Setups", "Target Engineering")

    add_card(s7, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.2))
    tb = s7.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "1. Parallel Machine Routing (FJSSP)"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    b7_1 = [
        ("The Available Machine Assets: ", "machine_capacities.csv already lists:\n• 5 CNC Mills (CNC_MILL_1 to 5)\n• 5 Lens Polishers (LENS_POLISHER_1 to 5)\n• 5 Coating Chambers (COATING_CHAMBER_1 to 5)\n• 5 Assembly Stations (ASSEMBLY_STATION_1 to 5)\n• 4 Testing Rigs (TESTING_RIG_1 to 4)"),
        ("Mathematical Formulation: ", "Each operation O_ij can execute on any eligible machine k in M_ij."),
        ("CP-SAT Optional Intervals: ", "modeled using AddOptionalIntervalVar with a Boolean presence flag x_ijk, enforcing Sum(x_ijk) == 1."),
        ("Impact: ", "Eliminates artificial bottlenecks, balances machine workload, and cuts makespan by 40–60%.")
    ]
    for b_t, n_t in b7_1:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    add_card(s7, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2))
    tb = s7.shapes.add_textbox(Inches(7.0), Inches(1.85), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "2. Sequence-Dependent Setups (SDST)"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_TEAL

    b7_2 = [
        ("Industrial Changeovers: ", "In precision lens & CNC machining, changeover time depends on product family transitions:\n• Switching optical lens curve requires tool lap change.\n• Changing milling material (aluminum to titanium) requires chip cleaning and tool offset re-calibration."),
        ("Asymmetric Setup Matrix: ", "Matrix S[k, family_A, family_B] defining exact changeover minutes."),
        ("CP-SAT Circuit Formulation: ", "Transition times enforced between consecutive tasks on machine k:\nStart(task_B) >= End(task_A) + S[k, A, B]."),
        ("Production Clustering: ", "Solver naturally clusters similar items together to minimize total setup downtime across the factory.")
    ]
    for b_t, n_t in b7_2:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 8: In-Planning Phase 2 — Manual Material Handling & Buffers
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Phase 2: Material Handling & Buffering (Tailored: No AGVs)", "Target Engineering")

    add_card(s8, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.2))
    tb = s8.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Manual Cart / Trolley Inter-Bay Transit"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    b8_1 = [
        ("Tailored to Real Factory Reality: ", "Eliminates all unnecessary complexity of autonomous AGV battery curves and robotic LiDAR routing."),
        ("Inter-Bay Handling Time (tau_ab): ", "Models the real physical time required to move parts between shop bays:\n• 0 mins: Consecutive tasks on same machine.\n• 5–10 mins: Moving within the same department bay.\n• 15–30 mins: Inter-department move (e.g. CNC Bay -> Optical Polishing -> Vacuum Chamber -> QA Rig)."),
        ("Physical Work Included: ", "Accounts for washing, burr removal, packing into protective tote bins, and physical trolley wheeling."),
        ("Precedence Coupling: ", "Start(Op_j+1) >= End(Op_j) + tau_ab.")
    ]
    for b_t, n_t in b8_1:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    add_card(s8, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2))
    tb = s8.shapes.add_textbox(Inches(7.0), Inches(1.85), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Workstation Staging Buffers & Blocking"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_TEAL

    b8_2 = [
        ("Finite Intermediate Storage (FIS): ", "Workstations have physical space for only 2–3 tote carts (Capacity C_b)."),
        ("The Blocking Phenomenon: ", "If machine B's buffer is completely full, upstream machine A cannot release the finished batch. Machine A becomes 'blocked', unable to start its next job."),
        ("Aisle Congestion Prevention: ", "Mathematically prevents unmanaged work-in-process (WIP) from piling up in pedestrian and cart corridors."),
        ("Cumulative Staging Constraints: ", "Enforced via CP-SAT Cumulative constraints over machine staging areas, keeping shop floor flow lean and organized.")
    ]
    for b_t, n_t in b8_2:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 9: In-Planning Phase 3 — Process Batching & Thermal Time Lags
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Phase 3: Upstream Process Batching & Thermal Curing Rules", "Target Engineering")

    add_card(s9, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.2))
    tb = s9.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Optical Coating Chamber Batching"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    b9_1 = [
        ("The Batch Process Nature: ", "In COATING_CHAMBER units, running single lenses is economically infeasible due to vacuum cycle & heating overheads."),
        ("Lot Sizing Bounds [B_min, B_max]: ", "Enforces minimum chamber fill (e.g. at least 20 units) and maximum chamber volume (e.g. up to 100 units)."),
        ("Multi-Order Consolidation: ", "Batches lenses from multiple active indents sharing identical optical anti-reflective coating recipes."),
        ("Backward Locking: ", "Upstream milling and polishing operations are pulled backward to hit the exact scheduled vacuum pump-down window.")
    ]
    for b_t, n_t in b9_1:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    add_card(s9, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2))
    tb = s9.shapes.add_textbox(Inches(7.0), Inches(1.85), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Zero-Wait & Curing Time-Lag Rules"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_TEAL

    b9_2 = [
        ("Zero-Wait (ZW) Constraints: ", "For processes where freshly treated optical glass oxidizes or degrades if exposed to ambient air without immediate sealing."),
        ("Limited-Wait (LW) Curing Windows: ", "theta_min <= Start(Op_next) - End(Op_batch) <= theta_max."),
        ("Physical Cooling & Adhesive Curing: ", "Parts must sit for at least theta_min (e.g., 60 mins cooling after autoclave/chamber) but must enter assembly before adhesive shelf-life theta_max (e.g., 24 hours)."),
        ("Yield Protection: ", "Eliminates scrap caused by out-of-spec chemical degradation between process stages.")
    ]
    for b_t, n_t in b9_2:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 10: In-Planning Phase 4 — Human-in-the-Loop Disruption Repair
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Phase 4: Human-in-the-Loop Rescheduling (No IoT Needed)", "Target Engineering")

    add_card(s10, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.2))
    tb = s10.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.2), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Robust Predictive Buffering"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    b10_1 = [
        ("The Brownfield Reality: ", "Machines lack telemetry sensors; schedules cannot be minute-brittle."),
        ("Safety Slack Buffers: ", "Adds a 5–10% protective buffer to task runtimes on bottleneck machines."),
        ("Variance Absorption: ", "Minor manual delays (machinist adjusting a clamp, 10 min setup slip) are absorbed internally by the safety slack without breaking downstream operations."),
        ("Schedule Stability: ", "Prevents 'schedule nervousness' and eliminates constant recalculations during the shift.")
    ]
    for b_t, n_t in b10_1:
        p = tf.add_paragraph()
        p.space_before = Pt(10)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    add_card(s10, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2))
    tb = s10.shapes.add_textbox(Inches(7.0), Inches(1.85), Inches(5.3), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Interactive Disruption Console"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_AMBER

    b10_2 = [
        ("Supervisor UI in Streamlit: ", "Supervisor logs shop events via simple dropdowns:\n• Mark Machine Down (e.g. CNC_MILL_2 down until 14:00)\n• Report Operation Delay (e.g. IOL-OPT-004 delayed 45 min)\n• Insert Rush Work Order (Priority Military Indent)"),
        ("Mode 1 — One-Click Right-Shift Repair: ", "Pushes downstream tasks to the right without changing machine assignments or sequence. Zero shop floor confusion!"),
        ("Mode 2 — Local CP-SAT Re-Optimization: ", "Locks in-progress tasks, re-routes unstarted tasks across active parallel machines (CNC_MILL_1, 3, 4, 5).")
    ]
    for b_t, n_t in b10_2:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(12)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(12)
        r_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 11: In-Planning Phase 5 — Actionable Shop-Floor Dispatch Sheets
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Phase 5: Actionable Shop-Floor Outputs & Dispatch Sheets", "Target Engineering")

    add_card(s11, Inches(0.8), Inches(1.7), Inches(3.7), Inches(5.2))
    tb = s11.shapes.add_textbox(Inches(0.95), Inches(1.85), Inches(3.4), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "1. Machinist Dispatch Sheets"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    b11_1 = [
        ("Per-Machine Worklist: ", "Printed or displayed on a tablet at each cell (e.g. CNC_MILL_3)."),
        ("Clean Sequence Order: ", "Shows exact order of jobs (Job 1 -> Job 2 -> Job 3)."),
        ("Tooling & Setup Notes: ", "Lists required cutting tools, chuck jaws, and optical fixtures."),
        ("Target Time Windows: ", "Displays planned start, planned finish, and customer due date.")
    ]
    for b_t, n_t in b11_1:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(11)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(11)
        r_n.font.color.rgb = C_TEXT_MUTED

    add_card(s11, Inches(4.8), Inches(1.7), Inches(3.7), Inches(5.2))
    tb = s11.shapes.add_textbox(Inches(4.95), Inches(1.85), Inches(3.4), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "2. Material Cart Tickets"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_TEAL

    b11_2 = [
        ("Tote Box Traveler Cards: ", "Accompany every physical rolling cart across departments."),
        ("Clear Routing Instructions: ", "Informs material handlers: 'Move from CNC Bay to Polishing Bay 2'."),
        ("Batch Inspection Sign-off: ", "Includes checkboxes for deburring, ultrasonic washing, and QA count."),
        ("Staging Destination: ", "Designates specific input rack buffer at downstream station.")
    ]
    for b_t, n_t in b11_2:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(11)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(11)
        r_n.font.color.rgb = C_TEXT_MUTED

    add_card(s11, Inches(8.8), Inches(1.7), Inches(3.7), Inches(5.2))
    tb = s11.shapes.add_textbox(Inches(8.95), Inches(1.85), Inches(3.4), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "3. Supervisor Dashboard"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_DARK_NAVY

    b11_3 = [
        ("Live Factory Schedule Gantt: ", "Color-coded multi-machine timeline with setup vs run blocks."),
        ("Bottleneck Indicator: ", "Highlights machines running above 85% utilization."),
        ("Buffer Congestion Alerts: ", "Flags when a staging buffer exceeds cart capacity."),
        ("What-If Simulation: ", "Enables management to test adding a 2nd shift or overtime before committing.")
    ]
    for b_t, n_t in b11_3:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(11)
        r_b.font.color.rgb = C_TEXT_MAIN
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(11)
        r_n.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 12: Comparison Matrix — Current vs Planned System
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Architecture Scorecard: Implemented vs. In-Planning", "Comparative Analysis")

    # Table layout
    rows = 7
    cols = 3
    table_shape = s12.shapes.add_table(rows, cols, Inches(0.8), Inches(1.7), Inches(11.7), Inches(5.2))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(3.0)
    tbl.columns[1].width = Inches(4.2)
    tbl.columns[2].width = Inches(4.5)

    headers = ["Factory Scheduling Dimension", "Current Implemented State", "Target In-Planning System"]
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_DARK_NAVY
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = C_WHITE

    matrix_data = [
        ("Machine Allocation", "Single fixed machine per operation", "Parallel Flexible Job Shop (CNC_MILL_1..5, etc.)"),
        ("Sequence-Dependent Setups", "Static uniform hours per item", "SDST transition matrix S[k, A, B] by item family"),
        ("Shop Floor Material Handling", "Assumed 0 minutes instant jump", "Manual cart/trolley inter-bay lags (5-30 mins)"),
        ("Intermediate Buffers", "Infinite buffer assumption (UIS)", "Finite Intermediate Storage (FIS) with blocking rules"),
        ("Upstream Process Batching", "Ignored; individual piece flow", "Vacuum Coating Chamber lot sizing [B_min, B_max]"),
        ("Shop Floor Uncertainty", "Static open-loop batch solver", "Safety slack buffers + Supervisor 1-click repair")
    ]
    for i, (dim, cur, pln) in enumerate(matrix_data):
        c0 = tbl.cell(i+1, 0)
        c0.fill.solid()
        c0.fill.fore_color.rgb = C_PRIMARY_LIGHT if i%2==0 else C_WHITE
        p0 = c0.text_frame.paragraphs[0]
        p0.text = dim
        p0.font.bold = True
        p0.font.size = Pt(11)
        p0.font.color.rgb = C_DARK_NAVY

        c1 = tbl.cell(i+1, 1)
        c1.fill.solid()
        c1.fill.fore_color.rgb = C_CARD_BG if i%2==0 else C_SLATE_BG
        p1 = c1.text_frame.paragraphs[0]
        p1.text = cur
        p1.font.size = Pt(11)
        p1.font.color.rgb = C_TEXT_MUTED

        c2 = tbl.cell(i+1, 2)
        c2.fill.solid()
        c2.fill.fore_color.rgb = C_CARD_BG if i%2==0 else C_SLATE_BG
        p2 = c2.text_frame.paragraphs[0]
        p2.text = pln
        p2.font.bold = True
        p2.font.size = Pt(11)
        p2.font.color.rgb = C_TEAL

    # =========================================================================
    # SLIDE 13: Technical Implementation Roadmap & Milestones
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "Execution Roadmap: Phased Rollout Plan", "Project Execution")

    phases = [
        ("Phase 1: FJSSP & Parallel Pools", "Week 1–2", "Upgrade CP-SAT model to distribute operations across CNC_MILL_1..5 and LENS_POLISHER_1..5; integrate SDST matrix.", C_PRIMARY),
        ("Phase 2: Inter-Bay Cart Transit", "Week 3", "Integrate transfer times tau_ab (5-30 min) and workstation staging buffer limits C_b to eliminate floor congestion.", C_TEAL),
        ("Phase 3: Vacuum Chamber Batching", "Week 4", "Implement coating chamber batch sizing bounds [B_min, B_max] and Limited-Wait cooling/curing time lags.", C_PRIMARY),
        ("Phase 4: Disruption Management", "Week 5", "Build the Supervisor Disruption Console in Streamlit for One-Click Right-Shift Repair and Local Re-Optimization.", C_AMBER),
        ("Phase 5: Floor Dispatch Sheets", "Week 6", "Deploy printable and interactive Daily Machine Dispatch Lists and Cart Traveler Tickets for shop floor execution.", C_DARK_NAVY)
    ]

    for i, (p_title, p_time, p_desc, col) in enumerate(phases):
        add_card(s13, Inches(0.8), Inches(1.7 + i*1.05), Inches(11.7), Inches(0.95), border_color=col)
        tb = s13.shapes.add_textbox(Inches(1.0), Inches(1.75 + i*1.05), Inches(11.3), Inches(0.85))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r1 = p.add_run()
        r1.text = p_title + "  [" + p_time + "]:  "
        r1.font.bold = True
        r1.font.size = Pt(13)
        r1.font.color.rgb = col
        r2 = p.add_run()
        r2.text = p_desc
        r2.font.size = Pt(12)
        r2.font.color.rgb = C_TEXT_MAIN

    # =========================================================================
    # SLIDE 14: Conclusion & Immediate Action Items
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    bg14 = s14.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg14.fill.solid()
    bg14.fill.fore_color.rgb = C_DARK_NAVY
    bg14.line.fill.background()

    add_card(s14, Inches(1.2), Inches(1.2), Inches(10.9), Inches(5.1), bg_color=RGBColor(30, 41, 59), border_color=C_PRIMARY)
    tb14 = s14.shapes.add_textbox(Inches(1.5), Inches(1.5), Inches(10.3), Inches(4.5))
    tf14 = tb14.text_frame
    tf14.word_wrap = True
    p = tf14.paragraphs[0]
    p.text = "Strategic Impact & Next Steps"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = C_WHITE

    concl_points = [
        ("1. Proven Solid Foundation: ", "The existing codebase already possesses robust Make-vs-Buy linear programming (PuLP) and baseline CP-SAT scheduling capabilities."),
        ("2. Tailored to Manufacturing Reality: ", "By stripping away unrealistic AGV/IoT assumptions, the in-planning system focuses directly on what machinists and supervisors actually need: parallel machine load balancing, setup clustering, cart transit times, and quick repair buttons."),
        ("3. High Return on Investment (ROI): ", "Unlocking the 19 parallel machines in your capacity database will immediately slash makespan and backlog without purchasing new machines."),
        ("4. Immediate Implementation Action: ", "Proceed to Phase 1: Upgrading CP-SAT to Flexible Job Shop with Parallel Machine Pools in schedule_makespan.py and app.py.")
    ]
    for b_t, n_t in concl_points:
        p = tf14.add_paragraph()
        p.space_before = Pt(14)
        r_b = p.add_run()
        r_b.text = b_t
        r_b.font.bold = True
        r_b.font.size = Pt(14)
        r_b.font.color.rgb = RGBColor(147, 197, 253)
        r_n = p.add_run()
        r_n.text = n_t
        r_n.font.size = Pt(14)
        r_n.font.color.rgb = C_WHITE

    # Save Presentation
    output_path = "/home/anuj/Desktop/Make_or_Buy/Whole_Factory_Optimization_and_Scheduling_Master_Deck.pptx"
    prs.save(output_path)
    print(f"Presentation successfully created at: {output_path}")

if __name__ == "__main__":
    create_deck()
