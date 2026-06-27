import streamlit as st
import pandas as pd
from database import get_organizations, get_employees_by_org, supabase

st.title("👤 Employee Dashboard & Personal Logs")

orgs = get_organizations()
org_options = {o['name']: o for o in orgs} if orgs else {}
selected_org = st.selectbox("Verify Organization", list(org_options.keys()))

if selected_org:
    target_org = org_options[selected_org]
    emps = get_employees_by_org(target_org['id'])
    emp_options = {f"{e['name']} ({e['emp_code']})": e for e in emps}
    
    selected_emp = st.selectbox("Select Your Profile", list(emp_options.keys()))
    pin = st.text_input("Confirm PIN Access", type="password")
    
    if pin and pin == emp_options[selected_emp]['pin']:
        emp_id = emp_options[selected_emp]['id']
        
        # Fetch individual history logs
        res = supabase.table("attendance_logs").select("*").eq("employee_id", emp_id).order("timestamp", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            st.metric("Total Shifts Formed (This Period)", len(df[df['action'] == 'IN']))
            st.dataframe(df[['timestamp', 'action', 'is_within_fence']], use_container_width=True)
        else:
            st.info("No personal attendance logs identified yet.")
            
