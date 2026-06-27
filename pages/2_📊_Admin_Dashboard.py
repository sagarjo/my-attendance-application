import streamlit as st
import pandas as pd
from database import get_organizations, supabase

st.title("📊 Enterprise Administrative Portal")

# Simple Hardcoded Multi-tenant Authentication simulation for MVP
admin_email = st.text_input("Admin Email ID")
admin_pass = st.text_input("Admin Security Password", type="password")

if admin_email and admin_pass == "admin123": # Keep simple for MVP
    st.success("Authorized Administrator Verified.")
    
    orgs = get_organizations()
    org_options = {o['name']: o for o in orgs}
    sel_org = st.selectbox("Select Managed Organization Context", list(org_options.keys()))
    current_org_id = org_options[sel_org]['id']
    
    # Date Filtering Rules
    filter_date = st.date_input("Filter Records by Date")
    
    if st.button("Generate Attendance Report"):
        # Relational Join Logic executed cleanly through Supabase Engine
        res = supabase.table("attendance_logs").select(
            "id, timestamp, action, is_within_fence, employees!inner(name, emp_code, organization_id)"
        ).eq("employees.organization_id", current_org_id).execute()
        
        if res.data:
            # Flatten structures
            flat_data = []
            for entry in res.data:
                flat_data.append({
                    "Employee Code": entry['employees']['emp_code'],
                    "Name": entry['employees']['name'],
                    "Timestamp": entry['timestamp'],
                    "Action Type": entry['action'],
                    "Geo Compliant": entry['is_within_fence']
                })
            df = pd.DataFrame(flat_data)
            st.dataframe(df)
            
            # Export Mechanism
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Structured CSV Report",
                data=csv,
                file_name=f"Attendance_Report_{sel_org}_{filter_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No records matched operational criteria configuration metrics.")

