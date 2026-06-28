import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import calendar
from database import get_supabase_client
from calendar_utils import calculate_attendance_metrics

# Page Configuration
st.set_page_config(page_title="Employee Portal", page_icon="👤", layout="wide")

# Polish Custom Dashboard Layout Styling
st.markdown("""
<style>
    /* Metric KPI Cards Layout */
    .metric-container { display: flex; flex-wrap: nowrap; gap: 8px; margin-bottom: 16px; width: 100%; }
    .metric-card { flex: 1; min-width: 0; border-radius: 12px; padding: 10px 4px; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
    .metric-val { font-size: 20px; font-weight: 700; margin-bottom: 1px; }
    .metric-lbl { font-size: 10px; font-weight: 600; text-transform: uppercase; color: #6B7280; }
    .bg-absent { background-color: #FFF0F2; color: #DC2626; }
    .bg-leave { background-color: #F3E8FF; color: #7C3AED; }
    .bg-half { background-color: #FFF7ED; color: #EA580C; }
    
    .sub-metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px; }
    .sub-metric-card { background: #F9FAFB; border: 1px solid #F3F4F6; border-radius: 10px; padding: 8px 2px; text-align: center; }
    .sub-metric-card .icon-val { font-size: 13px; font-weight: 700; color: #111827; }
    .sub-metric-card .label { color: #6B7280; font-size: 10px; }

    /* Strict Mobile Table Calendar Override Format Matrix Rules */
    .mobile-table-calendar {
        width: 100% !important;
        border-collapse: separate !important;
        border-spacing: 4px !important;
        table-layout: fixed !important;
        margin-top: 10px !important;
    }
    .mobile-table-calendar th {
        font-size: 10px !important;
        font-weight: 700 !important;
        color: #4B5563 !important;
        text-transform: uppercase !important;
        text-align: center !important;
        padding-bottom: 6px !important;
        width: 14.28% !important;
    }
    .mobile-table-calendar td {
        vertical-align: middle !important;
        text-align: center !important;
        padding: 0 !important;
        width: 14.28% !important;
    }
    .cal-cell-inner {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 5px 1px;
        min-height: 48px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
    }
    .cal-cell-today {
        background-color: #00E5FF !important;
        border: 1.5px solid #111827 !important;
    }
    .cal-cell-inner .day-num {
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 2px;
        display: block;
    }
    .status-badge {
        display: inline-block !important;
        padding: 1px 2px !important;
        font-size: 8px !important;
        font-weight: 800 !important;
        border-radius: 3px !important;
        width: 92% !important;
        text-align: center !important;
        text-transform: uppercase !important;
        box-sizing: border-box !important;
        line-height: 1.1 !important;
    }
    .badge-present { background-color: #E6F4EA !important; color: #137333 !important; }
    .badge-absent { background-color: #FCE8E6 !important; color: #C5221F !important; }
    .badge-leave { background-color: #F3E8FF !important; color: #7C3AED !important; }
    .badge-off { background-color: #E8F0FE !important; color: #1A73E8 !important; }
</style>
""", unsafe_allow_html=True)

st.title("Attendance Portal")
supabase = get_supabase_client()

# --- Multi-Tenant Fetch Configuration Block ---
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
    
    now = datetime.now()
    curr_year, curr_month = now.year, now.month
    start_date = date(curr_year, curr_month, 1)
    end_date = date(curr_year, curr_month, calendar.monthrange(curr_year, curr_month)[1])
    
    logs_res = supabase.table("attendance_logs").select("timestamp, action").eq("employee_id", selected_emp['id']).gte("timestamp", start_date.isoformat()).lte("timestamp", (end_date + timedelta(days=1)).isoformat()).execute()
    leaves_res = supabase.table("leave_applications").select("*").eq("employee_id", selected_emp['id']).execute()
    
    logs_data = logs_res.data or []
    leaves_data = leaves_res.data or []
    
    try:
        work_days_count = int(selected_org.get('work_week', 6))
    except:
        work_days_count = 6
        
    shift_start_str = selected_org.get('shift_start_time') or '09:00:00'
    shift_end_str = selected_org.get('shift_end_time') or '18:00:00'
    org_start = datetime.strptime(shift_start_str, "%H:%M:%S").time()
    org_end = datetime.strptime(shift_end_str, "%H:%M:%S").time()
    
    # Calculate attendance logic values using our utilities layout module
    metrics = calculate_attendance_metrics(pd.DataFrame(logs_data), leaves_data, work_days_count, org_start, org_end, curr_year, curr_month)

    tab_summary, tab_apply, tab_holidays = st.tabs(["Summary", "Apply Leaves", "Holidays"])
    
    with tab_summary:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card bg-absent"><div class="metric-val">{metrics['absents']}</div><div class="metric-lbl">Absents</div></div>
            <div class="metric-card bg-leave"><div class="metric-val">{metrics['on_leave']}</div><div class="metric-lbl">On Leave</div></div>
            <div class="metric-card bg-half"><div class="metric-val">{metrics['half_days']}</div><div class="metric-lbl">Half Days</div></div>
        </div>
        <div class="sub-metric-grid">
            <div class="sub-metric-card"><div class="icon-val">🕒 {metrics['late_ins']}</div><div class="label">Late In</div></div>
            <div class="sub-metric-card"><div class="icon-val">⏰ {metrics['early_outs']}</div><div class="label">Early Out</div></div>
            <div class="sub-metric-card"><div class="icon-val">⏱️ {metrics['deficit_hours']}h</div><div class="label">Deficit</div></div>
        </div>
        <div class="sub-metric-grid">
            <div class="sub-metric-card"><div class="icon-val">📅 {metrics['total_wh']}</div><div class="label">Total WH</div></div>
            <div class="sub-metric-card"><div class="icon-val">💼 {metrics['days_worked']}</div><div class="label">Days Worked</div></div>
            <div class="sub-metric-card"><div class="icon-val">📈 {metrics['avg_wh']}</div><div class="label">Avg. WH</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader(f"📅 {calendar.month_name[curr_month]} {curr_year}")
        
        # FIXED STRUCTURE: Generating calendar using an immutable HTML Table Matrix
        html_calendar = '<table class="mobile-table-calendar"><thead><tr>'
        for weekday_name in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]:
            html_calendar += f'<th>{weekday_name}</th>'
        html_calendar += '</tr></thead><tbody>'
            
        cal_matrix = calendar.monthcalendar(curr_year, curr_month)
        for week in cal_matrix:
            html_calendar += '<tr>'
            for idx, day in enumerate(week):
                if day == 0:
                    html_calendar += '<td></td>'
                else:
                    is_today = (day == now.day)
                    cell_class = "cal-cell-inner cal-cell-today" if is_today else "cal-cell-inner"
                    lbl_color = "#000000" if is_today else "#111827"
                    
                    # Status logic evaluation configuration
                    if day in metrics["worked_days_set"]:
                        status_html = '<span class="status-badge badge-present">PRESENT</span>'
                    elif day in metrics["approved_leave_days"]:
                        status_html = '<span class="status-badge badge-leave">LEAVE</span>'
                    elif day in metrics["week_offs_set"]:
                        status_html = '<span class="status-badge badge-off">WEEK OFF</span>'
                    elif day < now.day:
                        status_html = '<span class="status-badge badge-absent">ABSENT</span>'
                    else:
                        status_html = '<span class="status-badge" style="background:#F3F4F6;color:#9CA3AF;">—</span>'
                        
                    html_calendar += f"""
                    <td>
                        <div class="{cell_class}">
                            <span class="day-num" style="color:{lbl_color};">{day}</span>
                            {status_html}
                        </div>
                    </td>
                    """
            html_calendar += '</tr>'
        html_calendar += '</tbody></table>'
        st.markdown(html_calendar, unsafe_allow_html=True)

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
                        "employee_id": selected_emp['id'], "leave_reason": reason,
                        "from_date": f_date.isoformat(), "to_date": t_date.isoformat(),
                        "no_of_days": delta_days, "status": "Pending", "is_approved": False
                    }).execute()
                    st.success("Leave request submitted successfully!")
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
            st.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.info("No historical leaves records found.")

    with tab_holidays:
        st.info("Corporate Holiday rosters tracking active.")
