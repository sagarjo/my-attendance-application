import streamlit as st
import datetime
import pandas as pd
from database import supabase  # Centralized Supabase client connection entry

st.set_page_config(page_title="Corporate Administration Portal", layout="wide")

st.title("📊 Enterprise Compliance & Exception Management")
st.markdown("---")

# 1. Multi-Tenant Organization Scope Verification Selector
org_res = supabase.table("organizations").select("id", "name").execute()
org_options = {o['name']: o for o in org_res.data} if org_res.data else {}

if not org_options:
    st.warning("No active corporate tenants found. Seed organization settings first.")
else:
    selected_org = st.selectbox("Select Organization Domain Context", list(org_options.keys()))
    current_org_id = org_options[selected_org]['id']
    
    # Simple hardcoded credential validation gateway
    admin_password = st.sidebar.text_input("Admin Authorization Token", type="password")
    if admin_password != "admin123":  # Target benchmark verification token
        st.info("Provide valid administrative credentials in the sidebar to view core tracking matrices.")
    else:
        # Create administrative control tabs
        tab_missed, tab_leaves, tab_reporting = st.tabs([
            "⚠️ Missed Punch Lockouts", 
            "🗓️ Employee Leave Requests", 
            "📈 Log Reporting Engines"
        ])
        
        # --- TAB 1: MISSED PUNCH EXCEPTION PROCESSOR ---
        with tab_missed:
            st.subheader("Pending Exception Logs Requiring Kiosk Clearance")
            
            # Fetch unapproved logs indicating a missed working day exception gateway
            pending_exceptions = supabase.table("attendance_logs")\
                .select("id, employee_id, timestamp, log_remark, is_approved_missed, employees!inner(name, emp_code, organization_id)")\
                .eq("is_approved_missed", False)\
                .eq("employees.organization_id", current_org_id).execute()
                
            if not pending_exceptions.data:
                st.success("No compliance anomalies or lockouts require review for this organization.")
            else:
                for item in pending_exceptions.data:
                    emp_ref = item['employees']
                    log_id = item['id']
                    
                    with st.container():
                        st.write(f"**Employee:** {emp_ref['name']} ({emp_ref['emp_code']})")
                        st.write(f"**Exception Log Stamp:** {item['timestamp']}")
                        st.caption(f"Reason: {item['log_remark']}")
                        
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Approve Exception & Clear Kiosk", key=f"app_miss_{log_id}"):
                            supabase.table("attendance_logs").update({
                                "is_approved_missed": True,
                                "log_remark": "Approved by Admin - Kiosk Restored"
                            }).eq("id", log_id).execute()
                            st.success(f"Cleared lockout status for {emp_ref['name']}.")
                            st.rerun()
                            
                        if c2.button("❌ Reject & Maintain Security Lock", key=f"den_miss_{log_id}"):
                            supabase.table("attendance_logs").update({
                                "log_remark": "Rejected by Admin - Requires Physical Verification"
                            }).eq("id", log_id).execute()
                            st.error("Exception record flagged. Kiosk block remains active.")
                            st.rerun()
                    st.markdown("---")
        
        # --- TAB 2: LEAVE APPLICATION WORKFLOW ---
        with tab_leaves:
            st.subheader("Review Pending Self-Service Leave Submissions")
            
            # FIXED: Column targeted correctly as no_of_days
            pending_leaves = supabase.table("leave_applications")\
                .select("id, employee_id, leave_reason, no_of_days, from_date, to_date, status, employees!inner(name, emp_code, organization_id)")\
                .eq("status", "Pending")\
                .eq("employees.organization_id", current_org_id).execute()
                
            if not pending_leaves.data:
                st.info("No leave applications require administrative review.")
            else:
                for leave in pending_leaves.data:
                    emp_ref = leave['employees']
                    leave_id = leave['id']
                    
                    with st.container():
                        st.write(f"**Staff Member:** {emp_ref['name']} ({emp_ref['emp_code']})")
                        st.write(f"**Duration:** {leave['from_date']} to {leave['to_date']} ({leave['no_of_days']} Days)")
                        st.write(f"**Reason Profile:** {leave['leave_reason']}")
                        
                        reject_reason_input = st.text_input("Provide Rejection Feedback (Required if Rejecting)", key=f"txt_{leave_id}")
                        
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Approve Leave Request", key=f"app_lev_{leave_id}"):
                            supabase.table("leave_applications").update({
                                "status": "Approved",
                                "is_approved": True
                            }).eq("id", leave_id).execute()
                            st.success("Leave marked as approved. Kiosk locks activated for those dates.")
                            st.rerun()
                            
                        if c2.button("❌ Reject Leave Request", key=f"rej_lev_{leave_id}"):
                            if not reject_reason_input:
                                st.error("You must explicitly input a rejection reason string.")
                            else:
                                supabase.table("leave_applications").update({
                                    "status": "Rejected",
                                    "is_approved": False,
                                    "rejection_reason": reject_reason_input
                                }).eq("id", leave_id).execute()
                                st.warning("Leave application rejected. Feedback logged.")
                                st.rerun()
                    st.markdown("---")

        # --- TAB 3: REPORTING AND DOWNLOAD CORE ---
        with tab_reporting:
            st.subheader("Data Extraction Engine")
            filter_date = st.date_input("Select Target Operations Date", datetime.date.today())
            
            # Formulate structured dates boundaries for extraction
            start_date_ts = datetime.datetime.combine(filter_date, datetime.time(0,0,0)).isoformat()
            end_date_ts = datetime.datetime.combine(filter_date, datetime.time(23,59,59)).isoformat()
            
            reporting_logs = supabase.table("attendance_logs")\
                .select("id, timestamp, action, log_remark, employees!inner(name, emp_code, organization_id)")\
                .gte("timestamp", start_date_ts)\
                .lte("timestamp", end_date_ts)\
                .eq("employees.organization_id", current_org_id).execute()
                
            if not reporting_logs.data:
                st.info("No recorded punches match the selected target date.")
            else:
                flat_records = []
                for row in reporting_logs.data:
                    flat_records.append({
                        "Log ID": row['id'],
                        "Employee Name": row['employees']['name'],
                        "Employee Code": row['employees']['emp_code'],
                        "Timestamp": row['timestamp'],
                        "Punch Type": row['action'],
                        "System Remark": row['log_remark']
                    })
                
                df_report = pd.DataFrame(flat_records)
                st.dataframe(df_report, width="stretch")
                
                csv_binary = df_report.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Filtered Metrics to CSV File",
                    data=csv_binary,
                    file_name=f"attendance_report_{filter_date}.csv",
                    mime="text/csv"
                )
