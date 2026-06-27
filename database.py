import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Initializes and caches the Supabase connection."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Failed to connect to Database: {e}")
        st.stop()

supabase = get_supabase_client()

# --- Organization Helpers ---
def get_organizations():
    res = supabase.table("organizations").select("*").execute()
    return res.data

def create_organization(name, org_code, roles, lat, lng, radius, tz, start_t, end_t):
    data = {
        "name": name, "org_code": org_code.upper(), "job_roles": roles,
        "geo_latitude": lat, "geo_longitude": lng, "geo_radius_meters": radius,
        "timezone": tz, "shift_start_time": str(start_t), "shift_end_time": str(end_t)
    }
    return supabase.table("organizations").insert(data).execute()

# --- Employee Helpers ---
def get_employees_by_org(org_id):
    res = supabase.table("employees").select("*").eq("organization_id", org_id).execute()
    return res.data

def generate_next_emp_code(org_code: str) -> str:
    """Generates sequential codes like ABC001, ABC002."""
    res = supabase.table("employees").select("emp_code").like("emp_code", f"{org_code}%").execute()
    existing_codes = [int(d['emp_code'][3:]) for d in res.data if d['emp_code'][3:].isdigit()]
    next_num = max(existing_codes) + 1 if existing_codes else 1
    return f"{org_code.upper()}{next_num:03d}"

def create_employee(org_id, org_code, name, pin, role, start_t=None, end_t=None):
    emp_code = generate_next_emp_code(org_code)
    data = {
        "organization_id": org_id, "emp_code": emp_code, "name": name,
        "pin": pin, "role": role, 
        "shift_start_time": str(start_t) if start_t else None,
        "shift_end_time": str(end_t) if end_t else None
    }
    return supabase.table("employees").insert(data).execute()

# --- Attendance Helpers ---
def get_last_log_today(emp_id):
    from datetime import date
    today = date.today().isoformat()
    res = supabase.table("attendance_logs")\
        .select("*")\
        .eq("employee_id", emp_id)\
        .gte("timestamp", f"{today}T00:00:00")\
        .order("timestamp", desc=True)\
        .limit(1).execute()
    return res.data[0] if res.data else None

def log_attendance(emp_id, action, lat=None, lng=None, is_within_fence=True):
    data = {
        "employee_id": emp_id, "action": action,
        "latitude": lat, "longitude": lng, "is_within_fence": is_within_fence
    }
    return supabase.table("attendance_logs").insert(data).execute()

