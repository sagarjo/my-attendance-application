import streamlit as st
import datetime
import pandas as pd
import calendar
from database import supabase  # Centralized Supabase client instance

st.set_page_config(page_title="Personal Identity Dashboard", layout="centered")

# --- MOBILE COMPLIANT GRID SYSTEM & CALENDAR CLASS INJECTION ---
st.markdown("""
<style>
    .mobile-grid-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        border: 1px solid #334155;
    }
    .metric-title {
        font-size: 11px;
        color: #94A3B8;
        text-transform: uppercase;
        font-weight: 600;
    }
    .metric-value {
        font-size: 18px;
        color: #F8FAFC;
        font-weight: bold;
        margin-top: 4px;
    }
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 6px;
        text-align: center;
    }
    .calendar-header-cell {
        font-weight: bold;
        font-size: 12px;
        color: #64748B;
        padding: 4px;
    }
    .calendar-day-box {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 6px;
        min-height: 55px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        padding: 6px;
        position: relative;
    }
    .day-number {
        font-size: 12px;
        font-weight: 500;
        color: #E2E8F0;
    }
    .status-dot-container {
        display: flex;
        gap: 3px;
        justify-content: center;
        align-items: center;
        margin-top: 4px;
    }
    .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-active { background-color: #10B981; }  /* Green: Worked */
    .dot-leave { background-color: #3B82F6; }   /* Blue: Approved Leave */
    .dot-weekoff { background-color: #64748B; } /* Gray: Week-Off */
    .dot-system { background-color: #F59E0B; }  /* Yellow: Auto Timeout */
</style>
""", unsafe_allow_html=True)

st.title("👤 Employee Portal & Self-Service Desk")
st.markdown("---")

# Secure Authorization Verification
pin_auth = st.sidebar.text_input("Enter 4-Digit Identity PIN to Access Portal", type="password")

if not pin_auth:
    st.info("Awaiting personal identity verification via the sidebar entry credential field.")
else:
    # Fetch Employee Record along with relational organization constraints
    emp_res = supabase.table("employees")\
        .select("*, organizations(shift_start_time, shift_end_time, work_week)")\
        .eq("pin", pin_auth).execute()
    
    if not emp_res.data:
        st.error("Invalid identity PIN code entered. Access Denied.")
    else:
        emp_data = emp_res.data[0]
        st.success(f"Authenticated Account Workspace: {emp_data['name']} ({emp_data['emp_code']})")
        
        # System Calendar Variables Configuration
        today = datetime.date.today()
        current_year = today.year
        current_month = today.month
        
        # Set absolute boundaries for the active operational month
        start_month_ts = datetime.datetime(current_year, current_month, 1, 0, 0, 0).isoformat()
        end_month_ts = datetime.datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1], 23, 59, 59).isoformat()
        
        # Pull Live Data Records out of Supabase Tables
        logs_res = supabase.table("attendance_logs")\
            .select("*")\
            .eq("employee_id", emp_data['id'])\
            .gte("timestamp", start_month_ts)\
            .lte("timestamp", end_month_ts).execute()
            
        leaves_res = supabase.table("leave_applications")\
            .select("*")\
            .eq("employee_id", emp_data['id']).execute()
            
        df_logs = pd.DataFrame(logs_res.data) if logs_res.data else pd.DataFrame()
        df_leaves = pd.DataFrame(leaves_res.data) if leaves_res.data else pd.DataFrame()
        
        # Parse Dates string columns into manageable formats
        if not df_logs.empty:
            df_logs['dt_parsed'] = pd.to_datetime(df_logs['timestamp'], utc=True, errors='coerce')
            df_logs['date_only'] = df_logs['dt_parsed'].dt.date
            
        # --- TRUE ANALYTICAL METRICS CALCULATIONS (Pandas Aggregations) ---
        days_worked = df_logs['date_only'].nunique() if not df_logs.empty else 0
        total_leaves = len(df_leaves[df_leaves['status'] == 'Approved']) if not df_leaves.empty else 0
        
        system_timeouts = 0
        if not df_logs.empty:
            system_timeouts = df_logs['log_remark'].str.contains("System Auto Clock Out", na=False).sum()
            
        # --- RENDER ADAPTABLE FLEX/GRID VISUAL TILE LAYOUT ---
        st.markdown(f"""
        <div class="mobile-grid-container">
            <div class="metric-card">
                <div class="metric-title">Days Worked</div>
                <div class="metric-value">{days_worked}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">On Leave</div>
                <div class="metric-value">{total_leaves}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Auto Timeouts</div>
                <div class="metric-value">{system_timeouts}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        portal_tabs = st.tabs(["🗓️ Visual Calendar Matrix", "📝 File Self-Service Leave"])
        
        # --- TAB 1: OPERATIONAL VISUALIZATION CALENDAR ---
        with portal_tabs[0]:
            st.subheader(f"Shift Status Matrix: {calendar.month_name[current_month]} {current_year}")
            
            # Print Calendar Header Row Fields
            days_header_html = "".join(f'<div class="calendar-header-cell">{d[:3]}</div>' for d in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
            st.markdown(f'<div class="calendar-grid">{days_header_html}</div>', unsafe_allow_html=True)
            
            # Calculate Month Structure Matrix Blocks
            cal_matrix = calendar.monthcalendar(current_year, current_month)
            grid_cells_html = []
            
            for week in cal_matrix:
                for day_idx, day in enumerate(week):
                    if day == 0:
                        grid_cells_html.append('<div class="calendar-day-box" style="visibility: hidden;"></div>')
                    else:
                        eval_date = datetime.date(current_year, current_month, day)
                        eval_weekday = (eval_date.weekday() + 1) % 7
                        
                        # Establish Base Boolean Condition Flags for Indicators
                        has_logs = False
                        is_sys_timeout = False
                        is_weekoff = eval_weekday in (emp_data['week_offs'] or [])
                        is_approved_leave = False
                        
                        # Process database log variables against target calendar elements
                        if not df_logs.empty:
                            day_tracks = df_logs[df_logs['date_only'] == eval_date]
                            if not day_tracks.empty:
                                has_logs = True
                                if day_tracks['log_remark'].str.contains("System Auto Clock Out", na=False).any():
                                    is_sys_timeout = True
                                if (day_tracks['action'] == 'WEEK_OFF').any():
                                    is_weekoff = True
                                    
                        # Sync active approved corporate leaves arrays
                        if not df_leaves.empty:
                            active_leaves = df_leaves[(df_leaves['status'] == 'Approved') & 
                                                      (pd.to_datetime(df_leaves['from_date']).dt.date <= eval_date) & 
                                                      (pd.to_datetime(df_leaves['to_date']).dt.date >= eval_date)]
                            if not active_leaves.empty:
                                is_approved_leave = True
                                
                        # Append the matching color dot structures
                        dots_html = ""
                        if is_approved_leave:
                            dots_html += '<span class="dot dot-leave" title="Approved Corporate Leave"></span>'
                        if is_weekoff:
                            dots_html += '<span class="dot dot-weekoff" title="Scheduled Week-Off"></span>'
                        if is_sys_timeout:
                            dots_html += '<span class="dot dot-system" title="System Auto Timeout Event"></span>'
                        elif has_logs and not is_weekoff:
                            dots_html += '<span class="dot dot-active" title="Active Log Generated"></span>'
                            
                        cell_box = f"""
                        <div class="calendar-day-box">
                            <div class="day-number">{day}</div>
                            <div class="status-dot-container">{dots_html}</div>
                        </div>
                        """
                        grid_cells_html.append(cell_box)
                        
            st.markdown(f'<div class="calendar-grid">{"".join(grid_cells_html)}</div>', unsafe_allow_html=True)
            
        # --- TAB 2: REQUEST FORM SUBMITTAL COMPONENT ---
        with portal_tabs[1]:
            st.subheader("Apply for Corporate Leave")
            with st.form("leave_submission_form", clear_on_submit=True):
                reason = st.text_input("State Formal Leave Reason / Context")
                c1, c2 = st.columns(2)
                f_date = c1.date_input("Start Date Bound", datetime.date.today())
                t_date = c2.date_input("End Date Bound", datetime.date.today())
                
                if st.form_submit_button("Submit Application"):
                    if t_date < f_date:
                        st.error("Validation Error: End Date cannot occur before the selected Start Date.")
                    else:
                        days_delta = (t_date - f_date).days + 1
                        supabase.table("leave_applications").insert({
                            "employee_id": emp_data['id'],
                            "leave_reason": reason,
                            "no_days": days_delta,
                            "from_date": f_date.isoformat(),
                            "to_date": t_date.isoformat(),
                            "status": "Pending",
                            "is_approved": False
                        }).execute()
                        st.success("Application successfully routed to database. Awaiting administrative review.")
            
            # Historical Leave Tracks Audit Stream Component
            st.markdown("---")
            st.subheader("Leave Application Tracking History")
            if not df_leaves.empty:
                for _, row in df_leaves.iterrows():
                    status_badge = "🟢 Approved" if row['status'] == 'Approved' else ("🔴 Rejected" if row['status'] == 'Rejected' else "🟡 Pending Review")
                    st.write(f"**Period:** {row['from_date']} to {row['to_date']} | Status: {status_badge}")
                    st.write(f"*Reason Filed:* {row['leave_reason']}")
                    if row['status'] == 'Rejected' and row.get('rejection_reason'):
                        st.warning(f"⚠️ **Admin Rejection Feedback:** {row['rejection_reason']}")
                    st.markdown("---")
                    
