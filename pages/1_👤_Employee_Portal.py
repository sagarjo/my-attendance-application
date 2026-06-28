import streamlit as st
import datetime
import pandas as pd
import calendar
from database import supabase  # Centralized client context handle

st.set_page_config(page_title="Employee Portal Workspace", layout="centered")

# --- PREMIUM DASHBOARD CUSTOM CSS INJECTION ---
st.markdown("""
<style>
    /* Global Background and Structural Context overrides */
    div[data-testid="stAppViewBlockContainer"] {
        padding-top: 2rem;
        max-width: 720px;
    }
    
    /* Modern Grid Layout Matrix for Summary Tiles */
    .metric-grid-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }
    .metric-ui-card {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 16px 12px;
        text-align: center;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-ui-title {
        font-size: 11px;
        color: #94A3B8;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .metric-ui-value {
        font-size: 22px;
        color: #F8FAFC;
        font-weight: 700;
        margin-top: 4px;
    }

    /* Professional Calendar UI Wrapper Styles */
    .calendar-container-box {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px;
        margin-top: 10px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    .calendar-header-title {
        font-size: 18px;
        font-weight: 700;
        color: #F1F5F9;
        margin-bottom: 16px;
        text-align: left;
    }
    .calendar-table-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 8px;
        text-align: center;
    }
    .calendar-header-day {
        font-weight: 600;
        font-size: 12px;
        color: #94A3B8;
        padding-bottom: 8px;
        text-transform: uppercase;
    }
    .calendar-day-box-cell {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 8px;
        aspect-ratio: 1 / 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: all 0.2s ease-in-out;
    }
    .calendar-day-box-cell:hover {
        border-color: #475569;
        background-color: #1E293B;
    }
    .day-text-num {
        font-size: 14px;
        font-weight: 600;
        color: #CBD5E1;
    }
    
    /* Elegant Unified Color Status Circles Matrix */
    .status-dot-row-wrapper {
        display: flex;
        gap: 4px;
        justify-content: center;
        align-items: center;
        margin-top: 6px;
        height: 6px;
    }
    .status-mini-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
    }
    .bg-dot-active { background-color: #10B981; }  /* Emerald Green: Worked */
    .bg-dot-leave { background-color: #3B82F6; }   /* Blue: Approved Leave */
    .bg-dot-weekoff { background-color: #64748B; } /* Slate: Week-Off */
    .bg-dot-system { background-color: #F59E0B; }  /* Amber: Auto-Timeout Checkout */
    
    /* Clean CSS Legend Key List design */
    .legend-wrapper {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #334155;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #94A3B8;
    }
</style>
""", unsafe_allow_html=True)

st.title("👤 Employee Portal & Self-Service Desk")
st.markdown("---")

# Authentication Entry Logic Context
pin_auth = st.sidebar.text_input("Enter 4-Digit Identity PIN to Sync Portal Data", type="password")

if not pin_auth:
    st.info("Awaiting identity verification. Please enter your PIN inside the sidebar form.")
else:
    # Look up Employee data tracks [cite: 3]
    emp_res = supabase.table("employees")\
        .select("*, organizations(shift_start_time, shift_end_time, work_week)")\
        .eq("pin", pin_auth).execute()
    
    if not emp_res.data:
        st.error("Invalid identity PIN code entered. Access Denied.")
    else:
        emp_data = emp_res.data[0]
        st.success(f"Workspace Synchronized: {emp_data['name']} ({emp_data['emp_code']})")
        
        # Configure standard structural calendar fields
        today = datetime.date.today()
        current_year = today.year
        current_month = today.month
        
        start_month_ts = datetime.datetime(current_year, current_month, 1, 0, 0, 0).isoformat()
        end_month_ts = datetime.datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1], 23, 59, 59).isoformat()
        
        # Pull transactional log structures [cite: 3]
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
        
        # Vectorized parsing rules to securely handle calendar data strings
        if not df_logs.empty:
            df_logs['dt_parsed'] = pd.to_datetime(df_logs['timestamp'], utc=True, errors='coerce')
            df_logs['date_only'] = df_logs['dt_parsed'].dt.date
            
        # Compute summary values
        days_worked = df_logs['date_only'].nunique() if not df_logs.empty else 0
        total_leaves = len(df_leaves[df_leaves['status'] == 'Approved']) if not df_leaves.empty else 0
        system_timeouts = df_logs['log_remark'].str.contains("System Auto Clock Out", na=False).sum() if not df_logs.empty else 0
        
        # --- RENDER MODERN HIGHLIGHT SUMMARY METRIC GRID ---
        st.markdown(f"""
        <div class="metric-grid-container">
            <div class="metric-ui-card">
                <div class="metric-ui-title">Days Worked</div>
                <div class="metric-ui-value">{days_worked}</div>
            </div>
            <div class="metric-ui-card">
                <div class="metric-ui-title">On Leave</div>
                <div class="metric-ui-value">{total_leaves}</div>
            </div>
            <div class="metric-ui-card">
                <div class="metric-ui-title">Auto Timeouts</div>
                <div class="metric-ui-value">{system_timeouts}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        portal_tabs = st.tabs(["🗓️ Visual Attendance Matrix", "📝 Request New Leave"])
        
        # --- TAB 1: IMMUTABLE CALENDAR MATRIX ENGINE ---
        with portal_tabs[0]:
            # Generate Calendar Structure Blocks array using standard weekday ranges
            cal_matrix = calendar.monthcalendar(current_year, current_month)
            month_label = f"{calendar.month_name[current_month]} {current_year}"
            
            # Setup dynamic string accumulation buffer arrays
            html_buffer = []
            html_buffer.append(f'<div class="calendar-container-box">')
            html_buffer.append(f'<div class="calendar-header-title">{month_label}</div>')
            html_buffer.append('<div class="calendar-table-grid">')
            
            # Week Header Days labels
            for day_name in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
                html_buffer.append(f'<div class="calendar-header-day">{day_name}</div>')
                
            # Iterate through month calendar elements safely
            for week in cal_matrix:
                for day_idx, day_num in enumerate(week):
                    if day_num == 0:
                        # Structural spacing blank container cell block
                        html_buffer.append('<div class="calendar-day-box-cell" style="opacity: 0; pointer-events: none;"></div>')
                    else:
                        eval_date = datetime.date(current_year, current_month, day_num)
                        eval_weekday = (eval_date.weekday() + 1) % 7
                        
                        # Set default flag parameters
                        has_logs = False
                        is_sys_timeout = False
                        is_weekoff = eval_weekday in (emp_data['week_offs'] or [])
                        is_approved_leave = False
                        
                        if not df_logs.empty:
                            day_tracks = df_logs[df_logs['date_only'] == eval_date]
                            if not day_tracks.empty:
                                has_logs = True
                                if day_tracks['log_remark'].str.contains("System Auto Clock Out", na=False).any():
                                    is_sys_timeout = True
                                if (day_tracks['action'] == 'WEEK_OFF').any():
                                    is_weekoff = True
                                    
                        if not df_leaves.empty:
                            active_leaves = df_leaves[(df_leaves['status'] == 'Approved') & 
                                                      (pd.to_datetime(df_leaves['from_date']).dt.date <= eval_date) & 
                                                      (pd.to_datetime(df_leaves['to_date']).dt.date >= eval_date)]
                            if not active_leaves.empty:
                                is_approved_leave = True
                                
                        # Process color circles to place inside current date box 
                        dots_markup = []
                        if is_approved_leave:
                            dots_markup.append('<span class="status-mini-dot bg-dot-leave" title="Approved Corporate Leave"></span>')
                        if is_weekoff:
                            dots_markup.append('<span class="status-mini-dot bg-dot-weekoff" title="Scheduled Week-Off"></span>')
                        if is_sys_timeout:
                            dots_markup.append('<span class="status-mini-dot bg-dot-system" title="System Auto-Closed Out"></span>')
                        elif has_logs and not is_weekoff:
                            dots_markup.append('<span class="status-mini-dot bg-dot-active" title="Shift Complete"></span>')
                            
                        dots_row = f'<div class="status-dot-row-wrapper">{"".join(dots_markup)}</div>'
                        
                        # Append formatted individual cell layout block string
                        html_buffer.append(f"""
                        <div class="calendar-day-box-cell">
                            <div class="day-text-num">{day_num}</div>
                            {dots_row}
                        </div>
                        """)
                        
            html_buffer.append('</div>')  # Close calendar-table-grid
            
            # Append integrated dashboard tracking legend key list
            html_buffer.append("""
            <div class="legend-wrapper">
                <div class="legend-item"><span class="status-mini-dot bg-dot-active"></span> Present</div>
                <div class="legend-item"><span class="status-mini-dot bg-dot-leave"></span> Leave</div>
                <div class="legend-item"><span class="status-mini-dot bg-dot-weekoff"></span> Week-Off</div>
                <div class="legend-item"><span class="status-mini-dot bg-dot-system"></span> Auto-Timeout</div>
            </div>
            """)
            html_buffer.append('</div>')  # Close calendar-container-box
            
            # Single clean push to UI layer
            st.markdown("".join(html_buffer), unsafe_allow_html=True)
            
        # --- TAB 2: REQUEST FORM SUBMITTAL COMPONENT ---
        with portal_tabs[1]:
            st.subheader("Apply for Corporate Leave")
            with st.form("leave_submission_form", clear_on_submit=True):
                reason = st.text_input("State Leave Reason / Context")
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
                            "no_of_days": days_delta,
                            "from_date": f_date.isoformat(),
                            "to_date": t_date.isoformat(),
                            "status": "Pending",
                            "is_approved": False
                        }).execute()
                        st.success("Application successfully routed to database. Awaiting administrative review.")
            
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
