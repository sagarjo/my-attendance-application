import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
from database import get_supabase_client  # Your client initialization helper

# Page Configuration
st.set_page_config(page_title="Employee Portal", page_icon="👤", layout="wide")

# Modern Responsive CSS Layout Matrix
st.markdown("""
<style>
    /* Responsive Top Metric Row */
    .metric-container {
        display: flex;
        flex-wrap: nowrap; /* Forces them to stay side-by-side on mobile */
        gap: 10px;
        margin-bottom: 20px;
        width: 100%;
    }
    .metric-card {
        flex: 1;
        min-width: 0; /* Prevents text overflow breaks */
        border-radius: 12px;
        padding: 12px 6px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .metric-val {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 2px;
    }
    .metric-lbl {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .bg-absent { background-color: #FFF0F2; color: #DC2626; }
    .bg-leave { background-color: #F3E8FF; color: #7C3AED; }
    .bg-half { background-color: #FFF7ED; color: #EA580C; }

    /* Responsive Sub-Metrics Grid */
    .sub-metric-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr); /* Enforces exactly 3 columns on all screens */
        gap: 10px;
        margin-bottom: 12px;
    }
    .sub-metric-card {
        background: #F9FAFB;
        border: 1px solid #F3F4F6;
        border-radius: 10px;
        padding: 10px 4px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .sub-metric-card .icon-val {
        font-size: 14px;
        font-weight: 700;
        color: #111827;
    }
    .sub-metric-card .label {
        color: #6B7280;
        font-size: 11px;
        margin-top: 2px;
    }
    
    /* Responsive Calendar Grid */
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr); /* Strict 7-day row alignment */
        gap: 6px;
        text-align: center;
    }
    .calendar-header {
        font-weight: 700;
        font-size: 11px;
        color: #4B5563;
        padding-bottom: 8px;
    }
    .calendar-day {
        padding: 8px 0px;
        font-size: 13px;
        font-weight: 500;
        border-radius: 6px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 45px;
    }
    .day-today {
        background-color: #00E5FF !important;
        color: #000000 !important;
        font-weight: 700;
    }
    .cal-dot {
        height: 6px;
        width: 6px;
        background-color: #10B981;
        border-radius: 50%;
        margin-top: 4px;
    }
    .cal-dot-holiday { background-color: #9CA3AF; }
</style>
""", unsafe_allow_html=True)

st.title("Attendance Portal")

# --- Authentication Logic ---
supabase = get_supabase_client()
org_response = supabase.table("organizations").select("id, name").execute()
orgs = org_response.data or []

if not orgs:
    st.warning("No organizations registered yet.")
    st.stop()

org_names = [o['name'] for o in orgs]
selected_org_name = st.selectbox("Verify Organization", org_names)
selected_org = next(o for o in orgs if o['name'] == selected_org_name)

emp_response = supabase.table("employees").select("id, name, pin").eq("organization_id", selected_org['id']).execute()
employees = emp_response.data or []

if not employees:
    st.info("No employees found.")
    st.stop()

emp_map = {e['name']: e for e in employees}
selected_emp_name = st.selectbox("Select Your Profile", list(emp_map.keys()))
selected_emp = emp_map[selected_emp_name]

pin_input = st.text_input("Confirm PIN Access", type="password", max_chars=4)

if pin_input:
    if pin_input != selected_emp['pin']:
        st.error("Incorrect PIN.")
        st.stop()
        
    st.tabs(["Summary", "Apply Leaves", "Holidays"])
    
    # --- Fetch Log Data ---
    logs_res = supabase.table("attendance_logs").select("*").eq("employee_id", selected_emp['id']).execute()
    logs_data = logs_res.data or []
    
    # 1. High-Level Summary Cards
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card bg-absent"><div class="metric-val">0</div><div class="metric-lbl">Absents</div></div>
        <div class="metric-card bg-leave"><div class="metric-val">0</div><div class="metric-lbl">Leave</div></div>
        <div class="metric-card bg-half"><div class="metric-val">0</div><div class="metric-lbl">Half Day</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Detailed Sub-Metrics Row 1 & 2 (Forced 3 Columns using CSS Grid)
    st.markdown("""
    <div class="sub-metric-grid">
        <div class="sub-metric-card"><div class="icon-val">🕒 0</div><div class="label">Late In</div></div>
        <div class="sub-metric-card"><div class="icon-val">⏰ 0</div><div class="label">Early Out</div></div>
        <div class="sub-metric-card"><div class="icon-val">⏱️ 00:00</div><div class="label">Deficit Hr</div></div>
    </div>
    <div class="sub-metric-grid">
        <div class="sub-metric-card"><div class="icon-val">📅 204.37</div><div class="label">Total WH</div></div>
        <div class="sub-metric-card"><div class="icon-val">💼 21</div><div class="label">Days Worked</div></div>
        <div class="sub-metric-grid-item sub-metric-card"><div class="icon-val">📈 9.73</div><div class="label">Avg. WH</div></div>
    </div>
    """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 3. Responsive Interactive Calendar Matrix
    now = datetime.now()
    curr_year, curr_month = now.year, now.month
    st.subheader(f"June {curr_year}")
    
    active_days = set()
    for log in logs_data:
        log_dt = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
        if log_dt.year == curr_year and log_dt.month == curr_month:
            active_days.add(log_dt.day)
            
    cal = calendar.monthcalendar(curr_year, curr_month)
    days_weeks = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    
    # Building Calendar HTML Block strings
    cal_html = '<div class="calendar-grid">'
    for day_name in days_weeks:
        cal_html += f'<div class="calendar-header">{day_name}</div>'
        
    for week in cal:
        for idx, day in enumerate(week):
            if day == 0:
                cal_html += '<div></div>'
            else:
                is_today = (day == now.day)
                class_list = "calendar-day day-today" if is_today else "calendar-day"
                
                dot_html = ""
                if day in active_days:
                    dot_html = '<span class="cal-dot"></span>'
                elif idx in [0, 6]:
                    dot_html = '<span class="cal-dot cal-dot-holiday"></span>'
                    
                cal_html += f'<div class="{class_list}">{day}{dot_html}</div>'
    cal_html += '</div>'
    
    st.markdown(cal_html, unsafe_allow_html=True)
    
