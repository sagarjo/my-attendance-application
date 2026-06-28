import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from database import get_organizations, supabase

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# --- Custom Mobile-Responsive CSS Flexbox/Grid System ---
# FIXED: Using unsafe_allow_html=True to correctly compile visual calendar cards
st.markdown("""
<style>
    .metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
        gap: 12px;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #11151c;
        border: 1px solid #222e3d;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: #00f0ff;
    }
    .metric-label {
        font-size: 11px;
        color: #8899a6;
        text-transform: uppercase;
        margin-top: 4px;
        letter-spacing: 0.5px;
    }
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 8px;
        text-align: center;
        margin-top: 10px;
    }
    .calendar-day-header {
        font-weight: bold;
        font-size: 13px;
        color: #8899a6;
        padding-bottom: 8px;
        border-bottom: 1px solid #222e3d;
    }
    .calendar-day {
        background-color: #1a233a;
        border: 1px solid #253556;
        border-radius: 6px;
        padding: 10px 4px;
        min-height: 60px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        color: #ffffff !important;
        font-size: 14px;
    }
    .status-dot {
        height: 7px;
        width: 7px;
        border-radius: 50%;
        display: inline-block;
        margin-top: 6px;
    }
    .dot-worked { background-color: #00ff66; box-shadow: 0 0 6px #00ff66; }
    .dot-leave { background-color: #ffcc00; box-shadow: 0 0 6px #ffcc00; }
    .dot-weekoff { background-color: #555555; }
    .dot-absent { background-color: #ff3333; box-shadow: 0 0 6px #ff3333; }
</style>
""", unsafe_allow_html=True)

st.title("👤 Corporate Employee Portal")

# --- Context Initialization & Database Connections ---
try:
    orgs = get_organizations()
except:
    orgs = []

if not orgs:
    st.info("Please set up an organization and employee structure first.")
    st.stop()

org_map = {o['name']: o for o in orgs}
selected_org_name = st.selectbox("Select Organization Context", list(org_map.keys()))
active_org = org_map[selected_org_name]

# FIXED: Safely fetch simple integer work week tracking metrics (Defaulting to 6)
work_days_allowed_count = int(active_org.get('work_week', 6)) 

# Employee Profile Retrieval Sequence
emp_res = supabase.table("employees").select("*").eq("organization_id", active_org['id']).execute()
employees = emp_res.data

if not employees:
    st.warning("No employees found in this business unit.")
    st.stop()

emp_map = {e['name']: e for e in employees}
selected_emp = st.selectbox("Select Employee Profile", list(emp_map.keys()))
active_emp = emp_map[selected_emp]

# --- Fetch Operational Logs & Leaves from Backend Tables ---
now = datetime.now(pytz.utc)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

logs_res = supabase.table("attendance_logs")\
    .select("*")\
    .eq("employee_id", active_emp['id'])\
    .gte("timestamp", start_of_month.isoformat())\
    .execute()

leaves_res = supabase.table("leave_applications")\
    .select("*")\
    .eq("employee_id", active_emp['id'])\
    .eq("is_approved", True)\
    .execute()

# --- Process Analytics Engine via Pandas ---
df_logs = pd.DataFrame(logs_res.data)
approved_leaves = leaves_res.data

worked_dates = set()
week_off_dates = set()

if not df_logs.empty:
    df_logs['dt'] = pd.to_datetime(df_logs['timestamp'], utc=True)
    df_logs['date_str'] = df_logs['dt'].dt.strftime('%Y-%m-%d')
    
    worked_dates = set(df_logs[df_logs['action'].isin(['IN', 'OUT'])]['date_str'].unique())
    week_off_dates = set(df_logs[df_logs['action'] == 'WEEK_OFF']['date_str'].unique())

leave_dates = set()
for l in approved_leaves:
    try:
        start_d = datetime.strptime(l['from_date'], '%Y-%m-%d').date()
        end_d = datetime.strptime(l['to_date'], '%Y-%m-%d').date()
        curr = start_d
        while curr <= end_d:
            leave_dates.add(curr.strftime('%Y-%m-%d'))
            curr += timedelta(days=1)
    except Exception:
        pass

# --- Compute True Absenteeism & Matrix Mappings via Scalar Configuration ---
absent_count = 0
total_days_in_month_to_date = now.day
calendar_days_data = {}

for day in range(1, total_days_in_month_to_date + 1):
    check_date = start_of_month.replace(day=day)
    date_str = check_date.strftime('%Y-%m-%d')
    
    # ISO weekday: Mon = 1, Tue = 2, Wed = 3, Thu = 4, Fri = 5, Sat = 6, Sun = 7
    iso_weekday = check_date.isoweekday()
    
    # Core Evaluation Engine: Scheduled working window depends on the raw work day limit count
    is_scheduled_workday = iso_weekday <= work_days_allowed_count
    
    if date_str in worked_dates:
        status = "Worked"
    elif date_str in leave_dates:
        status = "On Leave"
    elif date_str in week_off_dates or not is_scheduled_workday:
        status = "Week Off"
    else:
        status = "Absent"
        absent_count += 1
        
    calendar_days_data[day] = status

# --- Render Metric UI Performance Tiles ---
st.subheader("📊 Performance Trackers")
st.markdown(f"""
<div class="metric-container">
    <div class="metric-card">
        <div class="metric-value">{absent_count}</div>
        <div class="metric-label">Absents</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{len(leave_dates)}</div>
        <div class="metric-label">On Leave</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{len(worked_dates)}</div>
        <div class="metric-label">Days Worked</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{work_days_allowed_count} Days</div>
        <div class="metric-label">Work Week</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Render Synchronized Attendance Calendar Grid Matrix ---
st.subheader("🗓️ Operational Attendance Grid")

# Render Horizontal Weekday Headers
days_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
header_cols = st.columns(7)
for idx, header in enumerate(days_headers):
    header_cols[idx].markdown(f'<div class="calendar-day-header">{header}</div>', unsafe_allow_html=True)

# Compute First Day Offset Padding Configuration
first_day_weekday = start_of_month.isoweekday()

# FIXED: Wrapped calendar elements inside a single macro markdown block using unsafe_allow_html=True
grid_html = '<div class="calendar-grid">'

# Append hidden blocks to shift numbers to correct weekday columns
for _ in range(first_day_weekday - 1):
    grid_html += '<div style="visibility: hidden;"></div>'

# Populate each calendar tracking index element
for day in range(1, total_days_in_month_to_date + 1):
    day_status = calendar_days_data[day]
    
    if day_status == "Worked":
        dot_class = "dot-worked"
    elif day_status == "On Leave":
        dot_class = "dot-leave"
    elif day_status == "Week Off":
        dot_class = "dot-weekoff"
    else:
        dot_class = "dot-absent"
        
    grid_html += f"""
    <div class="calendar-day">
        <strong>{day}</strong>
        <span class="status-dot {dot_class}"></span>
    </div>
    """

grid_html += "</div>"
st.markdown(grid_html, unsafe_allow_html=True)
