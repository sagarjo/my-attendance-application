import streamlit as st
import pandas as pd
from database import get_supabase_client

st.title("📊 Admin Leave Management Portal")
supabase = get_supabase_client()

# Fetch active organizations for filtering context
org_response = supabase.table("organizations").select("id, name").execute()
orgs = org_response.data or []

if not orgs:
    st.warning("No organizations registered yet.")
    st.stop()

org_options = {o['name']: o['id'] for o in orgs}
sel_org = st.selectbox("Select Organization Context", list(org_options.keys()))
current_org_id = org_options[sel_org]

# Fetch leave requests joining employee names for this organization
leaves_query = supabase.table("leave_applications")\
    .select("*, employees!inner(name, organization_id)")\
    .eq("employees.organization_id", current_org_id)\
    .order("created_at", desc=True).execute()

leaves_data = leaves_query.data or []

tab_pending, tab_processed = st.tabs(["⏳ Pending Requests", "✅ Processed History"])

with tab_pending:
    pending_leaves = [l for l in leaves_data if l.get('status', 'Pending') == 'Pending']
    
    if not pending_leaves:
        st.info("No pending leave applications requiring review.")
    else:
        for request in pending_leaves:
            with st.container(border=True):
                col_info, col_actions = st.columns([2, 1])
                
                with col_info:
                    st.markdown(f"**Employee:** {request['employees']['name']}")
                    st.markdown(f"📅 **Duration:** {request['from_date']} to {request['to_date']} ({request['no_of_days']} Days)")
                    st.markdown(f"📝 **Reason:** {request['leave_reason']}")
                
                with col_actions:
                    # Form workflow block to handle feedback capture during rejection
                    with st.form(key=f"review_form_{request['id']}"):
                        reject_msg = st.text_input("Rejection Reason", placeholder="Required only if rejecting", key=f"rej_text_{request['id']}")
                        
                        btn_approve = st.form_submit_button("👍 Approve", type="primary")
                        btn_reject = st.form_submit_button("❌ Reject")
                        
                        if btn_approve:
                            supabase.table("leave_applications").update({
                                "status": "Approved",
                                "is_approved": True,
                                "rejection_reason": None
                            }).eq("id", request['id']).execute()
                            st.success("Application approved successfully!")
                            st.rerun()
                            
                        if btn_reject:
                            if not reject_msg.strip():
                                st.error("Please provide a rejection reason.")
                            else:
                                supabase.table("leave_applications").update({
                                    "status": "Rejected",
                                    "is_approved": False,
                                    "rejection_reason": reject_msg.strip()
                                }).eq("id", request['id']).execute()
                                st.success("Application rejected with feedback.")
                                st.rerun()

with tab_processed:
    processed_leaves = [l for l in leaves_data if l.get('status', 'Pending') != 'Pending']
    
    if not processed_leaves:
        st.info("No processed leave history available.")
    else:
        flat_history = []
        for pl in processed_leaves:
            flat_history.append({
                "Employee": pl['employees']['name'],
                "From": pl['from_date'],
                "To": pl['to_date'],
                "Days": pl['no_of_days'],
                "Reason": pl['leave_reason'],
                "Status": pl['status'],
                "Feedback / Rejection Reason": pl['rejection_reason'] or "N/A"
            })
        st.dataframe(pd.DataFrame(flat_history), use_container_width=True, hide_index=True)
