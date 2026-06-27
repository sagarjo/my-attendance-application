import streamlit as st
import datetime
import pandas as pd
from database import supabase  # Your centralized Supabase client integration
from hvac_geo import haversine_validation  # Assuming geographic parsing utilities exist

st.set_page_config(page_title="Corporate Kiosk Portal", layout="centered")

def get_employee_by_pin(pin_code, org_id):
    res = supabase.table("employees").select("*").eq("pin", pin_code).eq("organization_id", org_id).execute()
    return res.data[0] if res.data else None

def auto_close_hanging_shifts(employee_id):
    """Closes any unlogged OUT actions from previous dates before creating new records."""
    today = datetime.date.today()
    res = supabase.table("attendance_logs")\
        .select("*")\
        .eq("employee_id", employee_id)\
        .order("timestamp", ascending=False)\
        .limit(1).execute()
    
    if res.data:
        last_log = res.data[0]
        last_log_dt = pd.to_datetime(last_log['timestamp'])
        
        if last_log['action'] == 'IN' and last_log_dt.date() < today:
            # Construct a system-enforced day-end log matching original shift date rules
            fallback_out_time = datetime.datetime.combine(last_log_dt.date(), datetime.time(23, 59, 59))
            supabase.table("attendance_logs").insert({
                "employee_id": employee_id,
                "timestamp": fallback_out_time.isoformat(),
                "action": "OUT",
                "log_remark": "System Auto Clock Out (Forgotten Punch)",
                "is_approved_missed": True
            }).execute()

def check_missed_punch_lockout(employee_id, week_offs, work_week):
    """Verifies if the employee left an unexcused absolute void on their last scheduled operational day."""
    today = datetime.date.today()
    check_day = today - datetime.timedelta(days=1)
    
    # Trace backward to find the last valid day the employee was expected to work
    while True:
        day_of_week = (check_day.weekday() + 1) % 7 # Convert Mon=0 to Sun=0 layout match
        if day_of_week in work_week and day_of_week not in (week_offs or []):
            break
        check_day -= datetime.timedelta(days=1)
        if (today - check_day).days > 7: # Circuit breaker
            return False

    # Check if a log entry exists for that target date range
    start_ts = datetime.datetime.combine(check_day, datetime.time(0,0,0)).isoformat()
    end_ts = datetime.datetime.combine(check_day, datetime.time(23,59,59)).isoformat()
    
    logs = supabase.table("attendance_logs").select("*")\
        .eq("employee_id", employee_id)\
        .gte("timestamp", start_ts)\
        .lte("timestamp", end_ts).execute()
        
    if not logs.data:
        # Check if there is already an explicit exception record written or if it is completely unlogged
        # Block the user until an administrator reviews or marks the day
        return True
    
    # Check if any past exception logs are still sitting unapproved
    unapproved_logs = supabase.table("attendance_logs").select("*")\
        .eq("employee_id", employee_id)\
        .eq("is_approved_missed", False).execute()
        
    return len(unapproved_logs.data) > 0

st.title("🏢 Relational Multi-Tenant Corporate Kiosk")
st.markdown("---")

# 1. Fetch Tenant Context
org_res = supabase.table("organizations").select("id", "name", "work_week").execute()
org_options = {o['name']: o for o in org_res.data} if org_res.data else {}

if not org_options:
    st.warning("No active corporate tenants found. Seed database setup tables.")
else:
    selected_org_name = st.selectbox("Select Organization Location", list(org_options.keys()))
    org_data = org_options[selected_org_name]
    
    pin_input = st.text_input("Enter 4-Digit Corporate Identity PIN", type="password")
    
    if pin_input:
        emp = get_employee_by_pin(pin_input, org_data['id'])
        if not emp:
            st.error("Invalid Authorization Identity Credentials.")
        else:
            st.success(f"Welcome, {emp['name']} ({emp['emp_code']})")
            
            # Run Automated Background Maintenance Tasks
            auto_close_hanging_shifts(emp['id'])
            
            today_date = datetime.date.today()
            today_weekday = (today_date.weekday() + 1) % 7
            
            # --- FEATURE 1: LEAVE SYNCHRONIZATION AUDIT ---
            leave_res = supabase.table("leave_applications")\
                .eq("employee_id", emp['id'])\
                .eq("is_approved", True)\
                .gte("to_date", today_date.isoformat())\
                .lte("from_date", today_date.isoformat()).execute()
                
            if leave_res.data:
                st.info("🚨 Kiosk Lockout: You are officially scheduled on an Approved Corporate Leave today.")
                # Force-hide terminal punch actions entirely
            else:
                # --- FEATURE 3: MISSED PUNCH ENGINE GATEWAY ---
                is_locked_out = check_missed_punch_lockout(emp['id'], emp['week_offs'], org_data['work_week'])
                
                if is_locked_out:
                    st.error("❌ Attendance System Locked Out: You missed a valid Clock In on your last scheduled working shift. You must obtain administrative dashboard sign-off before using this kiosk.")
                    
                    # Create an auto-flagged tracking metric if no logs exist for that period
                    if st.button("File Exception Report for Admin Review"):
                        supabase.table("attendance_logs").insert({
                            "employee_id": emp['id'],
                            "timestamp": datetime.datetime.now().isoformat(),
                            "action": "MISSED_IN_EXCEPTION",
                            "log_remark": "Awaiting Admin Approval for missed operational shift window",
                            "is_approved_missed": False
                        }).execute()
                        st.info("Exception ticket submitted. Contact your administrator.")
                else:
                    # Fetch logs for current date to toggle state variables
                    start_today = datetime.datetime.combine(today_date, datetime.time(0,0,0)).isoformat()
                    end_today = datetime.datetime.combine(today_date, datetime.time(23,59,59)).isoformat()
                    
                    today_logs = supabase.table("attendance_logs").select("*")\
                        .eq("employee_id", emp['id'])\
                        .gte("timestamp", start_today)\
                        .lte("timestamp", end_today).execute()
                    
                    # --- FEATURE 2: WEEK-OFF MARKING MECHANISM ---
                    is_marked_weekoff = any(l['action'] == 'WEEK_OFF' for l in today_logs.data)
                    
                    if today_weekday in (emp['week_offs'] or []) or is_marked_weekoff:
                        st.warning("🗓️ Operational Notice: Today is designated as a standard Week-Off.")
                        if not is_marked_weekoff:
                            if st.button("Formally Record Today as Week-Off in Logs"):
                                supabase.table("attendance_logs").insert({
                                    "employee_id": emp['id'],
                                    "timestamp": datetime.datetime.now().isoformat(),
                                    "action": "WEEK_OFF",
                                    "log_remark": "Manually confirmed week-off via frontend kiosk option"
                                }).execute()
                                st.rerun()
                    
                    # Render standard Core Punch Layout if not manually blocked by weekoff logs
                    if not is_marked_weekoff:
                        last_action = today_logs.data[-1]['action'] if today_logs.data else 'OUT'
                        
                        col1, col2 = st.columns(2)
                        if last_action in ['OUT', 'WEEK_OFF']:
                            if col1.button("🟢 Perform Shift Clock IN", use_container_width=True):
                                supabase.table("attendance_logs").insert({
                                    "employee_id": emp['id'],
                                    "timestamp": datetime.datetime.now().isoformat(),
                                    "action": "IN",
                                    "log_remark": "Regular Punch In"
                                }).execute()
                                st.success("Shift record registered successfully.")
                                st.rerun()
                        else:
                            if col2.button("🔴 Perform Shift Clock OUT", use_container_width=True):
                                supabase.table("attendance_logs").insert({
                                    "employee_id": emp['id'],
                                    "timestamp": datetime.datetime.now().isoformat(),
                                    "action": "OUT",
                                    "log_remark": "Regular Punch Out"
                                }).execute()
                                st.success("Shift record updated successfully.")
                                st.rerun()
