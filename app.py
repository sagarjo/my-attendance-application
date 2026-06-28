import streamlit as st
import datetime
from database import supabase  # Your core initialized Supabase configuration client [cite: 379]
# Import our separated standalone calendar engine [cite: 14]
from calendar_utils import calculate_attendance_metrics, render_html_calendar

st.set_page_config(layout="wide") [cite: 347]

st.title("👤 Employee Dashboard Portal")

# Mock session state for testing compliance parameters
if "employee" not in st.session_state:
    st.session_state["employee"] = {"id": "your-test-emp-uuid", "organization_id": "your-org-uuid"}
if "org_work_week" not in st.session_state:
    st.session_state["org_work_week"] = 6  # Default 6-day scalar work week logic [cite: 229]

emp_id = st.session_state["employee"]["id"]

# --- DATA FETCHING LAYER ---
@st.cache_data(ttl=60)
def load_portal_data(employee_id):
    # Fetch active logs from attendance_logs [cite: 121]
    logs_res = supabase.table("attendance_logs").select("*").eq("employee_id", employee_id).execute() [cite: 87, 246]
    
    # Fetch structural tracking info out of leave_applications table [cite: 139]
    leaves_res = supabase.table("leave_applications").select("*").eq("employee_id", employee_id).eq("is_approved", True).execute() [cite: 246]
    
    import pandas as pd
    return pd.DataFrame(logs_res.data), pd.DataFrame(leaves_res.data)

df_logs, df_leaves = load_portal_data(emp_id)

# --- EXECUTE EXTRACTED ANALYTICS MODULE ---
metrics = calculate_attendance_metrics(df_logs, df_leaves, st.session_state["org_work_week"])

# --- RENDER SUMMARY CARD MATRICES ---
st.subheader("Operational Metrics Summary")
cols = st.columns(4) [cite: 119]
cols[0].metric("Days Worked", metrics["days_worked"]) [cite: 145]
cols[1].metric("On Leave (Days)", metrics["on_leave"])
cols[2].metric("Total Worked Hrs", f"{metrics['total_wh']} hrs") [cite: 144]
cols[3].metric("Avg Daily WH", f"{metrics['avg_wh']} hrs") [cite: 146]

# --- RENDER EXTRACTED CALENDAR ENGINE ---
st.write("---") [cite: 14]
st.subheader("🗓️ Multi-Viewport Attendance Grid")

current_date = datetime.date.today()
# Explicitly trigger our visual interface injection layout function [cite: 200]
render_html_calendar(current_date.year, current_date.month, df_logs, df_leaves)

st.success("Dashboard components compiled and routed dynamically via isolated logic engines.")
