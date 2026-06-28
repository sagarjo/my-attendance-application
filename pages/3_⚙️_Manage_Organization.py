import streamlit as st
from database import create_organization, create_employee, get_organizations

st.title("⚙️ Global Organization & Operations Control Room")

tab1, tab2 = st.tabs(["🏢 Setup New Organization", "➕ Onboard Corporate Employee"])

with tab1:
    st.subheader("Register Business Unit")
    name = st.text_input("Organization Official Name")
    code = st.text_input("Corporate ID Code (Exactly 3 Alphabets)", max_chars=3)
    roles_input = st.text_input("Operational Job Roles (Comma Separated values)", "Engineer, Manager, Operator")
    
    st.write("**Geo-Fencing Boundaries**")
    lat = st.number_input("Anchor Latitude Point", format="%.6f", value=0.0)
    lng = st.number_input("Anchor Longitude Point", format="%.6f", value=0.0)
    radius = st.slider("Authorized Workspace Radius Perimeter (Meters)", 50, 500, 50)
    
    st.write("**Standard Shift Timings**")
    start_t = st.time_input("Global Operations Shift Start Time")
    end_t = st.time_input("Global Operations Shift Closure Time")
    
    # New: Interactive Work Week Selection
    st.write("**Operational Work Week Configuration**")
    days_map = {
        "Monday": 1, "Tuesday": 2, "Wednesday": 3, 
        "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 0
    }
    
    selected_days = st.multiselect(
        "Select Operating Days for this Organization",
        options=list(days_map.keys()),
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )
    
    if st.button("Register Corporate Structure"):
        if len(code) != 3 or not code.isalpha():
            st.error("Corporate ID Code must be exactly 3 alphabets.")
            st.stop()
            
        if not selected_days:
            st.error("Please choose at least one working day for the organization.")
            st.stop()
            
        # Convert selected day strings into their corresponding database array integers
        work_week_integers = [days_map[day] for day in selected_days]
        roles_array = [r.strip() for r in roles_input.split(",") if r.strip()]
        
        try:
            create_organization(
                name, code, roles_array, lat, lng, radius, "UTC", 
                start_t, end_t, work_week_integers
            )
            st.success(f"Organization Identity Registry established for: {name} ({code.upper()})")
        except Exception as e:
            st.error(f"Error saving to database: {e}")

with tab2:
    st.subheader("Add Employee Identity Profile")
    try:
        orgs = get_organizations()
    except:
        orgs = []
        
    if orgs:
        org_map = {o['name']: o for o in orgs}
        selected = st.selectbox("Assign Employee to Target Organization", list(org_map.keys()))
        active_org = org_map[selected]
        
        emp_name = st.text_input("Employee Full Legal Name")
        emp_pin = st.text_input("Assign Secure 4-Digit Numeric PIN Code", max_chars=4, type="password")
        emp_role = st.selectbox("Select Functional Business Unit Role Profile", options=active_org['job_roles'])
        
        if st.button("Provision New Employee Profile Records"):
            create_employee(active_org['id'], active_org['org_code'], emp_name, emp_pin, emp_role)
            st.success(f"Employee Account for '{emp_name}' provisioned successfully inside organization structure.")
    else:
        st.info("Create an organization before attempting to register operations staff tracking metrics.")
        
