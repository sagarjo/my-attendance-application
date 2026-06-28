import streamlit as st
import datetime
import pandas as pd
from database import supabase  # Centralized multi-tenant client handle

st.set_page_config(page_title="Corporate Kiosk Portal", layout="centered")

def get_employee_by_pin(pin_code, org_id):
    res = supabase.table("employees").select("*").eq("pin", pin_code).eq("organization_id", org_id).execute()
    return res.data[0] if res.data else None

st.title("🏢 Relational Multi-Tenant Corporate Kiosk")
st.markdown("---")

# Fetch Tenant Context
org_res = supabase.table("organizations").select("id", "name").execute()
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
            
            today_date = datetime.date.today()
            
            # Fetch logs for the current date to manage punch action toggles
            start_today = datetime.datetime.combine(today_date, datetime.time(0,0,0)).isoformat()
            end_today = datetime.datetime.combine(today_date, datetime.time(23,59,59)).isoformat()
            
            today_logs = supabase.table("attendance_logs").select("*")\
                .eq("employee_id", emp['id'])\
                .gte("timestamp", start_today)\
                .lte("timestamp", end_today)\
                .order("timestamp", desc=True).execute()
            
            # Determine last action state for toggle rendering
            last_action = today_logs.data[0]['action'] if today_logs.data else 'OUT'
            
            st.subheader("Select Attendance Action")
            col1, col2, col3 = st.columns(3)
            
            # Action 1: Clock IN (Visible only if user is clocked OUT or hasn't started)
            if last_action in ['OUT', 'WEEK_OFF']:
                if col1.button("🟢 Clock IN", width="stretch"):
                    supabase.table("attendance_logs").insert({
                        "employee_id": emp['id'],
                        "timestamp": datetime.datetime.now().isoformat(),
                        "action": "IN",
                        "log_remark": "Regular Punch In"
                    }).execute()
                    st.success("Shift Clock In registered successfully.")
                    st.rerun()
            else:
                col1.info("Already Clocked In")

            # Action 2: Clock OUT (Visible if user is currently clocked IN)
            if last_action == 'IN':
                if col2.button("🔴 Clock OUT", width="stretch"):
                    supabase.table("attendance_logs").insert({
                        "employee_id": emp['id'],
                        "timestamp": datetime.datetime.now().isoformat(),
                        "action": "OUT",
                        "log_remark": "Regular Punch Out"
                    }).execute()
                    st.success("Shift Clock Out registered successfully.")
                    st.rerun()
            else:
                col2.info("Not Clocked In")

            # Action 3: Mark Week-Off (Always accessible on this screen for manual override)
            if col3.button("🗓️ Punch Week-Off", width="stretch"):
                supabase.table("attendance_logs").insert({
                    "employee_id": emp['id'],
                    "timestamp": datetime.datetime.now().isoformat(),
                    "action": "WEEK_OFF",
                    "log_remark": "Manually logged week-off day"
                }).execute()
                st.success("Today successfully recorded as a Week-Off.")
                st.rerun()
