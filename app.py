import streamlit as st
import math
from datetime import date
from database import get_organizations, get_employees_by_org, get_last_log_today, log_attendance

# Set strict layout configurations
st.set_page_config(
    page_title="Organization Attendance Kiosk", 
    page_icon="🏢", 
    layout="centered"
)

st.title("🏢 Organization Attendance Kiosk")
st.write("---")

# 1. Fetch and Verify Active Corporate Registrations
try:
    organizations = get_organizations()
except Exception as e:
    st.error(f"Failed to connect to backend architecture: {e}")
    st.stop()

if not organizations:
    st.info("No organizations registered yet. Please set up via Admin Controls.")
    st.stop()

# Build dictionary mapper for cleaner UX drop-down interaction
org_options = {org['name']: org for org in organizations}
selected_org_name = st.selectbox("Select your Organization", options=list(org_options.keys()))
selected_org = org_options[selected_org_name]

# 2. Extract and Filter Employee Profiles Scoped to Selected Organization
employees = get_employees_by_org(selected_org['id'])

if not employees:
    st.warning("No employees registered under this organization.")
    st.stop()

# Build employee lookup mapping displaying Name along with Unique Employee ID Code
emp_options = {f"{emp['name']} ({emp['emp_code']})": emp for emp in employees}
selected_emp_name = st.selectbox("Select Your Name", options=list(emp_options.keys()))
employee = emp_options[selected_emp_name]

# 3. Secure Gatekeeper Verification View
pin_input = st.text_input("Enter 4-Digit Security PIN", type="password", max_chars=4)

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Computes the great-circle distance between two points on a sphere 
    using the Haversine formula. Returns distance strictly in meters.
    """
    # Earth's mean radius in kilometers
    R = 6371.0 
    
    # Convert degrees to radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine structural core matrix computation
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Distance in meters
    return (R * c) * 1000

if pin_input:
    if pin_input == employee['pin']:
        st.success("Identity Verified!")
        
        # Pull Organization Geofence parameters
        org_lat = float(selected_org['geo_latitude'])
        org_lng = float(selected_org['geo_longitude'])
        allowed_radius = float(selected_org['geo_radius_meters'])
        
        st.write("### 📍 Location Verification")
        
        # --- TECHNICAL NOTE ON DEVICE GEOLOCATION ---
        # For a production progressive web application (PWA), you would replace these 
        # testing input inputs with a frontend custom component like `streamlit-geolocation` 
        # to pull actual browser hardware cords. For stability, we present clean controls here.
        device_lat = st.number_input("Current Device Latitude", value=org_lat, format="%.6f")
        device_lng = st.number_input("Current Device Longitude", value=org_lng, format="%.6f")
        
        # Run live Geofence distance checks
        distance_from_base = calculate_haversine_distance(org_lat, org_lng, device_lat, device_lng)
        is_within_fence = distance_from_base <= allowed_radius
        
        # Visual cues detailing compliance parameters
        st.write(f"Calculated Distance to Workspace Boundary: **{distance_from_base:.2f} meters**")
        if is_within_fence:
            st.success("📍 Coordinates Verified: Inside Authorized Workspace Perimeter.")
        else:
            st.error("🚨 Out of Bounds: You are attempting to check in outside the permitted geofence.")
            
        st.write("---")
        
        # 4. State Evaluation Toggles (Clock-In vs Clock-Out Rules)
        last_log = get_last_log_today(employee['id'])
        current_status = last_log['action'] if last_log else "OUT"
        
        st.write(f"Your current status today: **{current_status}**")
        
        # Streamlit 1.58+ compliant layout sizing structure
        col1, col2 = st.columns(2)
        
        if current_status == "IN":
            if col1.button("🛑 Clock Out", width="stretch"):
                log_attendance(
                    emp_id=employee['id'], 
                    action="OUT", 
                    lat=device_lat, 
                    lng=device_lng, 
                    is_within_fence=is_within_fence
                )
                st.toast("Successfully Clocked Out!", icon="✅")
                st.rerun()
        else:
            # If punch is out-of-bounds, you can opt to disable or allow with warning flags based on policy rules
            if col2.button("🟢 Clock In", width="stretch"):
                log_attendance(
                    emp_id=employee['id'], 
                    action="IN", 
                    lat=device_lat, 
                    lng=device_lng, 
                    is_within_fence=is_within_fence
                )
                st.toast("Successfully Clocked In!", icon="🚀")
                st.rerun()
    else:
        st.error("Incorrect PIN string entered. Authentication Failed.")
        
