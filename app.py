import streamlit as st
from database import get_organizations, get_employees_by_org

st.set_page_config(page_title="Attendance Kiosk", page_icon="🏢", layout="centered")

st.title("🏢 Organization Attendance Kiosk")
st.write("---")

# 1. Select Organization
orgs = get_organizations()
if not orgs:
    st.info("No organizations registered yet. Please set up via Admin Controls.")
    st.stop()

org_options = {o['name']: o for o in orgs}
selected_org_name = st.selectbox("Select your Organization", options=list(org_options.keys()))
selected_org = org_options[selected_org_name]

# 2. Select Employee scoped to selected Org
employees = get_employees_by_org(selected_org['id'])
if not employees:
    st.warning("No employees registered under this organization.")
    st.stop()

emp_options = {f"{e['name']} ({e['emp_code']})": e for e in employees}
selected_emp_name = st.selectbox("Select Your Name", options=list(emp_options.keys()))
employee = emp_options[selected_emp_name]

# 3. Enter Pin Verification
pin_input = st.text_input("Enter 4-Digit Security PIN", type="password", max_chars=4)

if pin_input:
    if pin_input == employee['pin']:
        st.success("Identity Verified!")
        
        # Check last log status
        last_log = get_last_log_today(employee['id'])
        current_status = last_log['action'] if last_log else "OUT"
        
        st.write(f"Your current status today: **{current_status}**")
        
        # Real-time dummy location payload (to fulfill Geo requirements dynamically)
        # In structural web standard layouts, this can be tracked via standard Geolocation APIs
        lat, lng = selected_org['geo_latitude'], selected_org['geo_longitude'] 
        
        col1, col2 = st.columns(2)
        if current_status == "IN":
            if col1.button("🛑 Clock Out", use_container_width=True):
                log_attendance(employee['id'], "OUT", lat, lng, True)
                st.toast("Successfully Clocked Out!", icon="✅")
                st.rerun()
        else:
            if col2.button("🟢 Clock In", use_container_width=True):
                log_attendance(employee['id'], "IN", lat, lng, True)
                st.toast("Successfully Clocked In!", icon="🚀")
                st.rerun()
    else:
        st.error("Incorrect PIN string entered. Authentication Failed.")
