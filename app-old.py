import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client
from postgrest.exceptions import APIError

# ==========================================
# 1. INITIALIZATION & DATABASE CONNECTIONS
# ==========================================
st.set_page_config(
    page_title="PunchClock - Attendance Portal",
    page_icon="⏰",
    layout="wide"
)

@st.cache_resource
def init_supabase() -> Client:
    """Initializes and caches the Supabase connection client."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("Configuration Error: `SUPABASE_URL` or `SUPABASE_KEY` missing in Secrets.")
        st.stop()
    except Exception as e:
        st.error(f"Failed to connect to backend engine: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# ==========================================
# 2. DATA LAYER / HELPER FUNCTIONS
# ==========================================
def fetch_employees():
    """Retrieves all active employee profiles ordered alphabetically."""
    try:
        response = supabase.table("employees").select("id, name, pin, role").order("name").execute()
        return response.data
    except APIError as e:
        st.error(f"Database Query Error: {e.message}")
        return []

def get_last_action_today(employee_id: str):
    """Fetches the latest check-in/out log for an employee within the current calendar day."""
    try:
        today_start = datetime.datetime.now().date().isoformat()
        
        response = (
            supabase.table("attendance_logs")
            .select("action, timestamp")
            .eq("employee_id", employee_id)
            .gte("timestamp", today_start)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except APIError as e:
        st.error(f"Error fetching status logs: {e.message}")
        return None

def write_attendance_log(employee_id: str, action: str):
    """Inserts a new timestamped event punch log entry."""
    try:
        data = {"employee_id": employee_id, "action": action}
        supabase.table("attendance_logs").insert(data).execute()
        return True
    except APIError as e:
        st.error(f"Failed to submit attendance log: {e.message}")
        return False

def add_new_employee(name: str, pin: str, role: str):
    """Registers a brand new employee identity inside the tracking matrix."""
    try:
        data = {"name": name, "pin": pin, "role": role}
        supabase.table("employees").insert(data).execute()
        return True
    except APIError as e:
        st.error(f"Failed to register employee profile: {e.message}")
        return False

def fetch_logs_by_date(selected_date: datetime.date):
    """Retrieves all global logs on a target date, joining employee metadata."""
    try:
        start_date = selected_date.isoformat()
        end_date = (selected_date + datetime.timedelta(days=1)).isoformat()
        
        # Pull records including inner reference join to the parent employee table
        response = (
            supabase.table("attendance_logs")
            .select("id, timestamp, action, employees(name, role)")
            .gte("timestamp", start_date)
            .lt("timestamp", end_date)
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data
    except APIError as e:
        st.error(f"Failed to build system logs dump: {e.message}")
        return []

# ==========================================
# 3. INTERACTIVE PRESENTATION INTERFACES
# ==========================================
st.sidebar.title("⏰ PunchClock System")
st.sidebar.markdown("---")
view_selection = st.sidebar.radio(
    "Navigation Portal",
    ["View A: Check-In/Out Kiosk", "View B: Admin Dashboard", "View C: Manage Employees"]
)
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0-MVP • Python Runtime & Postgres Data Sync Active")

# ------------------------------------------
# VIEW A: THE VISITOR / WORKER KIOSK Portal
# ------------------------------------------
if view_selection == "View A: Check-In/Out Kiosk":
    st.title("🏢 Workspace Attendance Portal")
    st.subheader("Fast Check-In Kiosk Engine")
    
    employees = fetch_employees()
    
    if not employees:
        st.warning("No operational employee files exist yet. Please register entries inside the admin console.")
    else:
        # Layout components clean form structure
        emp_names = [emp["name"] for emp in employees]
        selected_name = st.selectbox("Identify Employee Target Profile", emp_names)
        
        # Resolve target structure data element
        selected_emp = next(emp for emp in employees if emp["name"] == selected_name)
        
        entered_pin = st.text_input("Enter secure 4-Digit Identity PIN", type="password", max_chars=4)
        
        if entered_pin:
            if entered_pin == selected_emp["pin"]:
                st.success("🔒 PIN Identity Verified.")
                
                # Deduce current punch status rule logic flow
                last_log = get_last_action_today(selected_emp["id"])
                
                # Determine Next Required Interaction
                if last_log is None or last_log["action"] == "OUT":
                    next_action = "IN"
                    btn_label = "🟢 Clock In (Shift Entry)"
                    btn_color = "secondary"
                else:
                    next_action = "OUT"
                    btn_label = "🔴 Clock Out (Shift Exit)"
                    btn_color = "primary"
                
                # Last status summary context display
                if last_log:
                    parsed_time = datetime.datetime.fromisoformat(last_log["timestamp"]).strftime('%I:%M %p')
                    st.info(f"Your last logged status today: **{last_log['action']}** at **{parsed_time}**")
                else:
                    st.info("No timeline logs registered for you today yet.")
                
                # Process structural writes execution action trigger
                if st.button(btn_label, use_container_width=True):
                    if write_attendance_log(selected_emp["id"], next_action):
                        st.toast(f"Log updated successfully: {next_action}", icon="✅")
                        st.balloons()
                        st.success(f"Transaction Complete: Logged **{next_action}** for {selected_name} at current timestamp.")
                        st.rerun()
            else:
                st.error("❌ Identity Mismatch: Invalid secure PIN provided for this worker entry.")

# ------------------------------------------
# VIEW B: THE ANALYTICS / ADMIN DASHBOARD
# ------------------------------------------
elif view_selection == "View B: Admin Dashboard":
    st.title("📊 Administration Reporting Center")
    
    # Simple cleartext security layer check gate
    admin_auth_pass = st.text_input("Enter System Administration Authorization Passphrase", type="password")
    
    if admin_auth_pass == "admin123":  # Default hardcoded credential pattern logic
        st.success("🔐 Administrative access clearance approved.")
        
        # Operational parameters settings layout split
        col1, col2 = st.columns([1, 3])
        with col1:
            target_date = st.date_input("Filter Evaluation Date Range", datetime.date.today())
        
        raw_logs = fetch_logs_by_date(target_date)
        
        if raw_logs:
            # Flatten target relation hierarchy data mapping arrays out cleanly
            flattened_records = []
            for item in raw_logs:
                emp_meta = item.get("employees") or {"name": "Unknown", "role": "Unknown"}
                timestamp_obj = datetime.datetime.fromisoformat(item["timestamp"])
                
                flattened_records.append({
                    "Log ID": item["id"],
                    "Employee Name": emp_meta.get("name"),
                    "Role/Department": emp_meta.get("role"),
                    "Punch Type Event": item["action"],
                    "Timestamp Context": timestamp_obj.strftime('%Y-%m-%d %I:%M:%S %p')
                })
            
            df = pd.DataFrame(flattened_records)
            
            with col2:
                st.metric(label="Total Daily Active Punch Actions", value=len(df))
            
            st.dataframe(df, use_container_width=True)
            
            # Formulate robust native csv export functionality stream directly mapping
            csv_payload = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data Segment as CSV File Document",
                data=csv_payload,
                file_name=f"Attendance_Report_{target_date.isoformat()}.csv",
                mime="text/csv"
            )
        else:
            st.info(f"No entry or log transactions registered within system profiles on date: {target_date}")
            
    elif admin_auth_pass != "":
        st.error("Access Refused: Invalid Master Access Credential Combination Input Token String Pattern.")

# ------------------------------------------
# VIEW C: DATA CONTEXT MANAGEMENT ENGINE
# ------------------------------------------
elif view_selection == "View C: Manage Employees":
    st.title("👤 Workspace Identity Provisioning Center")
    st.subheader("Register Core System Personnel")
    
    with st.form("new_employee_form", clear_on_submit=True):
        emp_name = st.text_input("Full Legal Identity Name")
        emp_role = st.text_input("Organizational Role Designation (e.g., Engineering, Risk Analyst)")
        emp_pin = st.text_input("Assigned Login Gate PIN Code (Exactly 4 digits digits numeric)", max_chars=4, type="password")
        
        form_submitted = st.form_submit_button("Provision Access Registry Matrix Profile")
        
        if form_submitted:
            if not emp_name or not emp_role or not emp_pin:
                st.error("Processing Validation Error: All fields require structural tracking definitions filled.")
            elif not (emp_pin.isdigit() and len(emp_pin) == 4):
                st.error("Processing Validation Error: Core verification parameter must reside as exactly 4 numeric characters string formatting.")
            else:
                if add_new_employee(emp_name, emp_pin, emp_role):
                    st.success(f"System Matrix Successfully Authorized Entry Profile Instance record definition mapping: **{emp_name}** (**{emp_role}**)")
