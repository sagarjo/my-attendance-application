import streamlit as st
import datetime
from database import supabase  # Your core initialized Supabase configuration client

# Global Multi-Tenant App Configurations
st.set_page_config(
    page_title="Multi-Tenant Kiosk Attendance System",
    page_icon="⏰",
    layout="wide"
)

st.title("👤 Employee Dashboard Portal")

st.markdown("""
### Welcome to the Employee Attendance & Kiosk Management System

Please use the sidebar menu to navigate to your required module:
* **👤 Employee Portal:** Check summary stats, review your calendar, and apply for leaves.
* **📊 Admin Dashboard:** Manage organizations, process leave requests, and view employee history logs.
""")

st.info("💡 **Tip:** If you are accessing this from a tablet or mobile screen, hide the sidebar via the top-left 'X' button to maximize real-estate.")
