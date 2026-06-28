import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, date
import calendar
from database import get_supabase_client

# Page Configurations
st.set_page_config(page_title="Employee Portal", page_icon="👤", layout="wide")

# Inject Polished, Mobile-Responsive Flex/Grid Matrix 
st.markdown("""
<style>
    /* Status KPI Containers */
    .metric-container { display: flex; flex-wrap: nowrap; gap: 10px; margin-bottom: 20px; width: 100%; }
    .metric-card { flex: 1; min-width: 0; border-radius: 12px; padding: 12px 6px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .metric-val { font-size: 22px; font-weight: 700; margin-bottom: 2px; }
    .metric-lbl { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .bg-absent { background-color: #FFF0F2; color: #DC2626; }
    .bg-leave { background-color: #F3E8FF; color: #7C3AED; }
    .bg-half { background-color: #FFF7ED; color: #EA580C; }
    
    /* Sub Metric Rows */
    .sub-metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; }
    .sub-metric-card { background: #F9FAFB; border: 1px solid #F3F4F6; border-radius: 10px; padding: 10px 4px; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .sub-metric-card .icon-val { font-size: 14px; font-weight: 700; color: #111827; }
    .sub-metric-card .label { color: #6B7280; font-size: 11px; margin-top: 2px; }
    
    /* Explicit Fixed 7-Column Calendar Layout Grid */
    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; text-align: center; width: 100%; margin-top: 10px; }
    .calendar-header { font-weight: 700; font-size: 11px; color: #4B5563; padding-bottom: 8px; text-transform: uppercase; }
    
    /* Structured Day Boxes with High-Contrast Explicit Font Colors */
    .calendar-day { 
        padding: 8px 0px; 
        font-size: 14px; 
        font-weight: 700; 
        color: #111827 !important; /* Locks numeric color visibility strictly */
        border-radius: 8px; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        min-height: 54px; 
        background-color: #FFFFFF; 
        box-shadow: inset 0 0 0 1px #E5E7EB;
    }
    .day-today { background-color: #00E5FF !important; color: #000000 !important; font-weight: 800; box-shadow: none; }
    
    /* Dynamic Circular Status Indicators */
    .cal-dot-container { display: flex; gap: 3px; justify-content: center; align-items: center; margin-top: 4px; height: 6px; }
    .cal-dot { height: 6px; width: 6px; background-color: #10B981; border-radius: 50%; display: inline-block; }
    .cal-dot-absent { height: 6px; width: 6px; background-color: #DC2626; border-radius: 50%; display: inline-block; }
    .cal-dot-leave { height: 6px; width: 6px; background-color: #7C3AED; border-radius: 50%; display: inline-block; }
    .cal-dot-holiday { height: 6px; width: 6px; background-color: #9CA3AF; border-radius: 50%; display: inline-block; }
</style>
""", unsafe_allow_html=True)

st.title("Attendance Portal")
supabase = get_supabase_client()

# --- Tenant Separation Context Filters ---
org_response = supabase.table("organizations").select("id, name, work_week, shift_start_time, shift_end_time").execute()
orgs = org_response.data or []

if not orgs:
    st.warning("No organizations configured.")
    st.stop()

org_map = {o['name']: o for o in orgs}
selected_org_name = st.selectbox("Verify Organization", list(org_map.keys()))
selected_org = org_map[selected_org_name]

emp_response = supabase.table("employees").select("id, name, pin").eq("organization_id", selected_org['id']).execute()
employees = emp_response.data or []

if not employees:
    st.info("No employee profiles found.")
    st.stop()

emp_map = {e['name']: e for e in employees}
selected_emp_name = st.selectbox("Select Your Profile", list(emp_map.keys()))
selected_emp = emp_map[selected_emp_name]

pin_input = st.text_input("Confirm PIN Access", type="password", max_chars=4)

if pin_input and pin_input == selected_emp['pin']:
    st.success(f"Verified Profile: {selected_emp['name']}")
    
    # ---------------------------------------------------------
    # OPERATIONAL METRICS CALCULATION ENGINE
    # ---------------------------------------------------------
    now = datetime.now()
    curr_year, curr_month = now.year, now.month
    start_date = date(curr_year, curr_month, 1)
    end_date = date(curr_year, curr_month, calendar.monthrange(curr_year, curr_month)[1])
    
    # Query database records
    logs_res = supabase.table("attendance_logs").select("timestamp, action").eq("employee_id", selected_emp['id']).gte("timestamp", start_date.isoformat()).lte("timestamp", (end_date + timedelta(days=1)).isoformat()).execute()
    leaves_res = supabase.table("leave_applications").select("*").eq("employee_id", selected_emp['id']).execute()
    
    logs_data = logs_res.data or []
    leaves_data = leaves_res.data or []
    
    worked_days_set = set()
    daily_durations = {}
    late_ins = 0
    early_outs = 0
    half_days = 0
    total_wh = 0.0
    deficit_hours = 0.0
    
    shift_start_str = selected_org.get('shift_start_time') or '09:00:00'
    shift_end_str = selected_org.get('shift_end_time') or '18:00:00'
    org_start = datetime.strptime(shift_start_str, "%H:%M:%S").time()
    org_end = datetime.strptime(shift_end_str, "%H:%M:%S").time()
    allowed_work_week = selected_org.get('work_week') or [1, 2, 3, 4, 5]
    
    df_logs = pd.DataFrame(logs_data)
    if not df_logs.empty:
        df_logs['dt'] = pd.to_datetime(df_logs['timestamp'], utc=True, errors='coerce')
        df_logs = df_logs.dropna(subset=['dt'])
        
        if not df_logs.empty:
            # FIXED: Evaluated directly against native datetime series to avoid Pandas object conversions
            worked_days_set = set(df_logs['dt'].dt.day.unique())
            df_logs['date'] = df_logs['dt'].dt.date
            
            for day_date, group in df_logs.groupby('date'):
                day_hours = 0.0
                last_in = None
                sorted_group = group.sort_values('dt')
                
                for _, row in sorted_group.iterrows():
                    log_time = row['dt'].time()
                    if row['action'] == 'IN':
                        last_in = row['dt']
                        if log_time > org_start:
                            late_ins += 1
                    elif row['action'] == 'OUT' and last_in is not None:
                        day_hours += (row['dt'] - last_in).total_seconds() / 3600.0
                        last_in = None
                        if log_time < org_end:
                            early_outs += 1
                            
                daily_durations[day_date.day] = day_hours
                total_wh += day_hours
                if 0 < day_hours < 4.0:
                    half_days += 1
                if day_hours < 8.0:
                    deficit_hours += (8.0 - day_hours)

    days_worked = len(worked_days_set)
    avg_wh = round(total_wh / days_worked, 2) if days_worked > 0 else 0.0
    
    # Process Approved Leaves tracking ranges
    approved_leave_days = set()
    total_approved_leaves_count = 0
    
    for lv in leaves_data:
        if lv.get('status') == 'Approved':
            lv_from = datetime.strptime(lv['from_date'], "%Y-%m-%d").date()
            lv_to = datetime.strptime(lv['to_date'], "%Y-%m-%d").date()
            
            if lv_from.month == curr_month or lv_to.month == curr_month:
                total_approved_leaves_count += lv['no_of_days']
                
            curr_step = lv_from
            while curr_step <= lv_to:
                if curr_step.month == curr_month:
                    approved_leave_days.add(curr_step.day)
                curr_step += timedelta(days=1)
            
    # Calculate Absents dynamically against the work_week array setup
    absents = 0
    for d in range(1, now.day + 1):
        check_dt = date(curr_year, curr_month, d)
        mapped_db_day = (check_dt.weekday() + 1) % 7
        if mapped_db_day in allowed_work_week:
            if d not in worked_days_set and d not in approved_leave_days:
                absents += 1

    # Navigation Setup
    tab_summary, tab_apply, tab_holidays = st.tabs(["Summary", "Apply Leaves", "Holidays"])
    
    with tab_summary:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card bg-absent"><div class="metric-val">{absents}</div><div class="metric-lbl">Absents</div></div>
            <div class="metric-card bg-leave"><div class="metric-val">{total_approved_leaves_count}</div><div class="metric-lbl">On Leave</div></div>
            <div class="metric-card bg-half"><div class="metric-val">{half_days}</div><div class="metric-lbl">Half Days</div></div>
        </div>
        <div class="sub-metric-grid">
            <div class="sub-metric-card"><div class="icon-val">🕒 {late_ins}</div><div class="label">Late In</div></div>
            <div class="sub-metric-card"><div class="icon-val">⏰ {early_outs}</div><div class="label">Early Out</div></div>
            <div class="sub-metric-card"><div class="icon-val">⏱️ {round(deficit_hours, 1)}h</div><div class="label">Deficit</div></div>
        </div>
        <div class="sub-metric-grid">
            <div class="sub-metric-card"><div class="icon-val">📅 {round(total_wh, 2)}</div><div class="label">Total WH</div></div>
            <div class="sub-metric-card"><div class="icon-val">💼 {days_worked}</div><div class="label">Days Worked</div></div>
            <div class="sub-metric-card"><div class="icon-val">📈 {avg_wh}</div><div class="label">Avg. WH</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader(f"📅 {calendar.month_name[curr_month]} {curr_year}")
        
        # Build Grid Calendar Matrix
        cal = calendar.monthcalendar(curr_year, curr_month)
        cal_html = '<div class="calendar-grid">'
        for d_name in ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]:
            cal_html += f'<div class="calendar-header">{d_name}</div>'
            
        for week in cal:
            for idx, day in enumerate(week):
                if day == 0:
                    cal_html += '<div></div>'
                else:
                    is_today = (day == now.day)
                    day_cls = "calendar-day day-today" if is_today else "calendar-day"
                    c_date = date(curr_year, curr_month, day)
                    db_day_idx = (c_date.weekday() + 1) % 7
                    
                    # Generate dot indicator block tags cleanly
                    dot_html = '<div class="cal-dot-container">'
                    if day in worked_days_set:
                        dot_html += '<span class="cal-dot"></span>' 
                    elif day in approved_leave_days:
                        dot_html += '<span class="cal-dot cal-dot-leave"></span>' 
                    elif db_day_idx not in allowed_work_week:
                        dot_html += '<span class="cal-dot cal-dot-holiday"></span>' 
                    elif day < now.day:
                        dot_html += '<span class="cal-dot cal-dot-absent"></span>' 
                    else:
                        dot_html += '<span style="height:6px; width:6px; display:inline-block;"></span>'
                    dot_html += '</div>'
                        
                    # FIXED: Wrapped raw day digit cleanly inside explicit text block to maintain absolute visibility
                    cal_html += f'<div class="{day_cls}"><span style="display:block; font-size:14px; line-height:1.2;">{day}</span>{dot_html}</div>'
        cal_html += '</div>'
        st.markdown(cal_html, unsafe_allow_html=True)

    with tab_apply:
        st.subheader("Apply for Leave")
        with st.form("leave_application_form", clear_on_submit=True):
            reason = st.text_input("Reason for Leave", placeholder="Medical treatment, Family function, etc.")
            col_f, col_t = st.columns(2)
            f_date = col_f.date_input("From Date", min_value=date.today())
            t_date = col_t.date_input("To Date", min_value=date.today())
            submit_btn = st.form_submit_button('Submit Leave Application')
            
            if submit_btn:
                if t_date < f_date:
                    st.error("Error: 'To Date' cannot occur before 'From Date'.")
                elif not reason.strip():
                    st.error("Please enter a valid reason.")
                else:
                    delta_days = (t_date - f_date).days + 1
                    supabase.table("leave_applications").insert({
                        "employee_id": selected_emp['id'],
                        "leave_reason": reason,
                        "from_date": f_date.isoformat(),
                        "to_date": t_date.isoformat(),
                        "no_of_days": delta_days,
                        "status": "Pending",
                        "is_approved": False
                    }).execute()
                    st.success("Successfully submitted request!")
                    st.rerun()
                        
        st.markdown("---")
        st.subheader("Your Leave History & Feedback")
        if leaves_data:
            df_history = pd.DataFrame(leaves_data)[[
                'from_date', 'to_date', 'no_of_days', 'leave_reason', 'status', 'rejection_reason'
            ]].rename(columns={
                'from_date': 'From', 'to_date': 'To', 'no_of_days': 'Days', 
                'leave_reason': 'Reason', 'status': 'Approval Status', 'rejection_reason': 'Remarks / Reject Reason'
            })
            df_history['Remarks / Reject Reason'] = df_history['Remarks / Reject Reason'].fillna("—")
            st.dataframe(df_history, width='stretch', hide_index=True)
        else:
            st.info("No historical logs recorded yet.")

    with tab_holidays:
        st.info("Corporate Holiday rosters tracking active.")
