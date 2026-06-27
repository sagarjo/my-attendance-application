import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
from database import get_supabase_client  # Assuming your client initialization helper

# Page Configuration
st.set_page_config(page_title="Employee Portal", page_icon="👤", layout="wide")

# Custom CSS for modern Metric Cards (Matching Image 2 styling)
st.markdown("""
<style>
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-bottom: 25px;
    }
    .metric-card {
        flex: 1;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .metric-val {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 2px;
    }
    .metric-lbl {
        font-size: 14px;
        font-weight: 500;
        color: #6B7280;
    }
    /* Specific Colors from Reference UI */
    .bg-absent { background-color: #FFF0F2; color: #DC2626; }
    .bg-leave { background-color: #F3E8FF; color: #7C3AED; }
    .bg-half { background-color: #FFF7ED; color: #EA580C; }
    
    .sub-metric-card {
        background: #F9FAFB;
        border: 1px solid #F3F4F6;
        border-radius: 12px;
        padding: 12px;
        display: flex;
        align-items: center;
        justify-content: space-around;
    }
    
    /* Calendar dot styles */
    .cal-dot {
        height: 8px;
        width: 8px;
        background-color: #10B981; /* Green present dot */
        border-radius: 50%;
        display: inline-block;
        margin-top: 4px;
    }
    .cal-dot-absent { background-color: #DC2626; }
    .cal-dot-holiday { background-color: #9CA3AF; }
</style>
""", unsafe_allow_html=True)

st.title("Attendance Portal")

# --- Authentication / Profile Selection Layer ---
# In production, link this to a logged-in session state. For the MVP kiosk context:
supabase = get_supabase_client()

# Fetch organizations for context matching app.py
org_response = supabase.table("organizations").select("id, name").execute()
orgs = org_response.data if org_response.data else []

if not orgs:
    st.warning("No organizations registered yet.")
    st.stop()

org_names = [o['name'] for o in orgs]
selected_org_name = st.selectbox("Verify Organization", org_names)
selected_org = next(o for o in orgs if o['name'] == selected_org_name)

# Fetch Employees for selected organization
emp_response = supabase.table("employees").select("id, name, pin").eq("organization_id", selected_org['id']).execute()
employees = emp_response.data if emp_response.data else []

if not employees:
    st.info("No employees found in this organization.")
    st.stop()

emp_map = {e['name']: e for e in employees}
selected_emp_name = st.selectbox("Select Your Profile", list(emp_map.keys()))
selected_emp = emp_map[selected_emp_name]

pin_input = st.text_input("Confirm PIN Access", type="password", max_chars=4)

if pin_input:
    if pin_input != selected_emp['pin']:
        st.error("Incorrect PIN. Access Denied.")
        st.stop()
        
    st.success(f"Welcome back, {selected_emp['name']}!")
    st.write("---")
    
    # Navigation sub-tabs matching Reference Image 2
    tab_summary, tab_leaves, tab_holidays = st.tabs(["Summary", "Apply Leaves", "Holidays"])
    
    with tab_summary:
        # --- Mock / Calculated Metrics Processing Block ---
        # Fetching all logs for this employee to process stats dynamically
        logs_res = supabase.table("attendance_logs").select("*").eq("employee_id", selected_emp['id']).execute()
        logs_data = logs_res.data if logs_res.data else []
        
        # UI Top Level Status Rows (HTML Injected Strings)
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card bg-absent">
                <div class="metric-val">0</div>
                <div class="metric-lbl">Absents</div>
            </div>
            <div class="metric-card bg-leave">
                <div class="metric-val">0</div>
                <div class="metric-lbl">On Leave</div>
            </div>
            <div class="metric-card bg-half">
                <div class="metric-val">0</div>
                <div class="metric-lbl">Half Days</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Sub-metrics Grid Layout (Late In, Early Out, Hours Metrics)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="sub-metric-card"><div>🕒 <b>0</b><br><span style="color:#6B7280;font-size:12px;">Late In</span></div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="sub-metric-card"><div>⏰ <b>0</b><br><span style="color:#6B7280;font-size:12px;">Early Out</span></div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="sub-metric-card"><div>⏱️ <b>00:00</b><br><span style="color:#6B7280;font-size:12px;">Deficit Hr</span></div></div>', unsafe_allow_html=True)
            
        st.write("")
        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown('<div class="sub-metric-card"><div>📅 <b>204.37</b><br><span style="color:#6B7280;font-size:12px;">Total WH</span></div></div>', unsafe_allow_html=True)
        with col5:
            st.markdown('<div class="sub-metric-card"><div>💼 <b>21</b><br><span style="color:#6B7280;font-size:12px;">Day(s) Worked</span></div></div>', unsafe_allow_html=True)
        with col6:
            st.markdown('<div class="sub-metric-card"><div>📈 <b>9.73</b><br><span style="color:#6B7280;font-size:12px;">Avg. WH</span></div></div>', unsafe_allow_html=True)
            
        st.write("---")
        
        # --- Interactive Visual Calendar View Matrix ---
        now = datetime.now()
        curr_year = now.year
        curr_month = now.month
        
        st.subheader(f"📅 {calendar.month_name[curr_month]} {curr_year}")
        
        # Get active dates from database logs to render accurate green indicators
        active_days = set()
        for log in logs_data:
            log_dt = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            if log_dt.year == curr_year and log_dt.month == curr_month:
                active_days.add(log_dt.day)
        
        # Generating the calendar matrix
        cal = calendar.monthcalendar(curr_year, curr_month)
        days_weeks = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        
        # Creating Grid Columns for Calendar Headers
        cal_cols = st.columns(7)
        for idx, day_name in enumerate(days_weeks):
            cal_cols[idx].markdown(f"**{day_name}**")
            
        for week in cal:
            cal_cols = st.columns(7)
            for idx, day in enumerate(week):
                if day == 0:
                    cal_cols[idx].write("")
                else:
                    # Check if day matches current runtime date target
                    is_today = (day == now.day and curr_month == now.month)
                    
                    # Highlight 'Today' block layout
                    if is_today:
                        box_style = "background-color:#00E5FF; padding:10px; border-radius:4px; text-align:center; color:black; font-weight:bold;"
                    else:
                        box_style = "text-align:center; padding:10px;"
                    
                    # Determine indicator dot color
                    dot_html = ""
                    if day in active_days:
                        dot_html = '<br><span class="cal-dot"></span>'
                    elif idx == 0 or idx == 6:  # Weekends default indicator
                        dot_html = '<br><span class="cal-dot cal-dot-holiday"></span>'
                        
                    cal_cols[idx].markdown(f'<div style="{box_style}">{day}{dot_html}</div>', unsafe_allow_html=True)
                    
    with tab_leaves:
        st.write("### Apply Leaves Pipeline Coming Soon")
    with tab_holidays:
        st.write("### Corporate Holiday Rosters")
        
