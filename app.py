# app.py
import streamlit as st 
import datetime 
import pandas as pd 
from database import supabase 

# Ensure this call remains at the absolute top of your script
st.set_page_config(page_title="Corporate Kiosk", layout="centered") 

# --- OVERRIDE SIDEBAR FILENAME DISPLAY ---
# This safely overrides and resizes the text space to render "Mark Attendance" completely
st.sidebar.markdown(
    """
    <style>
        /* Select and update the target text containment element */
        [data-testid="stSidebarNav"] ul li:first-child span {
            visibility: hidden;
            display: inline-block;
            width: 100%;
        }
        [data-testid="stSidebarNav"] ul li:first-child span::after {
            content: "Mark Attendance";
            visibility: visible;
            display: block;
            position: absolute;
            left: 0;
            top: 0;
            width: max-content;
            font-weight: 500;
        }
    </style>
    """,
    unsafe_allow_html=True
)

def get_employee_by_pin(pin_code, org_id): 
    res = supabase.table("employees").select("*").eq("pin", pin_code).eq("organization_id", org_id).execute() 
    return res.data[0] if res.data else None 

st.title("🏢 Daily Attendance Marking Kiosk")
st.subheader("Select Organization and Enter 4 digit Pin to Punch In")
st.markdown("---") 

# ... (the rest of your app.py execution logic remains unchanged)

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
            today_iso = today_date.isoformat()
            
            # --- 1. CRITICAL ENGINE CHECK: APPROVED LEAVE APPLICATION ---
            leave_res = supabase.table("leave_applications")\
                .select("*")\
                .eq("employee_id", emp['id'])\
                .eq("status", "Approved")\
                .lte("from_date", today_iso)\
                .gte("to_date", today_iso).execute()
                
            if leave_res.data:
                st.info(f"🌴 **Status:** You are on an approved leave today. Clock in options will be available after your leave period ends.")
            else:
                # Fetch logs for the current date to determine existing states
                start_today = datetime.datetime.combine(today_date, datetime.time(0,0,0)).isoformat()
                end_today = datetime.datetime.combine(today_date, datetime.time(23,59,59)).isoformat()
                
                today_logs = supabase.table("attendance_logs")\
                    .select("*")\
                    .eq("employee_id", emp['id'])\
                    .gte("timestamp", start_today)\
                    .lte("timestamp", end_today)\
                    .order("timestamp", desc=True).execute()
                
                # Check if a week-off action has already been performed today
                is_marked_weekoff = any(l['action'] == 'WEEK_OFF' for l in today_logs.data) if today_logs.data else False
                
                # --- 2. CRITICAL ENGINE CHECK: WEEK-OFF ACTION LOCKOUT ---
                if is_marked_weekoff:
                    st.warning("🗓️ **Status:** You are on a week-off for today.")
                else:
                    # Determine last standard punch state for toggle rendering
                    last_action = today_logs.data[0]['action'] if today_logs.data else 'OUT'
                    
                    st.subheader("Select Attendance Action")
                    col1, col2, col3 = st.columns(3)
                    
                    # Action A: Clock IN
                    if last_action in ['OUT', 'WEEK_OFF']:
                        if col1.button("🟢 Clock IN", use_container_width=True):
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

                    # Action B: Clock OUT
                    if last_action == 'IN':
                        if col2.button("🔴 Clock OUT", use_container_width=True):
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

                    # Action C: Punch Week-Off
                    if col3.button("🗓️ Punch Week-Off", use_container_width=True):
                        supabase.table("attendance_logs").insert({
                            "employee_id": emp['id'],
                            "timestamp": datetime.datetime.now().isoformat(),
                            "action": "WEEK_OFF",
                            "log_remark": "Manually logged week-off day"
                        }).execute()
                        st.success("Today successfully recorded as a Week-Off.")
                        st.rerun()
