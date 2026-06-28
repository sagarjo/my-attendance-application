import streamlit as st
import pandas as pd
import datetime
from calendar import monthrange

def calculate_attendance_metrics(df_logs, df_leaves, work_days_allowed_count):
    """
    Computes all dashboard counters dynamically off raw database frames.
    """
    metrics = {
        "absents": 0, "on_leave": 0, "half_days": 0, "late_ins": 0,
        "early_outs": 0, "deficit_hours": 0.0, "total_wh": 0.0,
        "days_worked": 0, "avg_wh": 0.0
    }
    
    # If no logs and no leaves exist, return default metrics safely
    if df_logs.empty and df_leaves.empty:
        return metrics

    # 1. Process Leaves Total Count
    if not df_leaves.empty:
        metrics["on_leave"] = int(df_leaves['no_of_days'].sum()) [cite: 51]

    if df_logs.empty:
        return metrics

    # Parse timestamps cleanly to avoid .dt accessor string exceptions [cite: 73, 171]
    df_logs['dt'] = pd.to_datetime(df_logs['timestamp'], utc=True, errors='coerce') [cite: 171]
    df_logs['date_str'] = df_logs['dt'].dt.strftime('%Y-%m-%d')
    
    # Group matched pairs to evaluate Working Hours (WH)
    unique_days = df_logs['date_str'].unique()
    metrics["days_worked"] = len(unique_days) [cite: 146]
    
    total_wh_accumulator = 0.0
    
    for date_group, group in df_logs.groupby('date_str'):
        sorted_group = group.sort_values('dt')
        ins = sorted_group[sorted_group['action'] == 'IN']
        outs = sorted_group[sorted_group['action'] == 'OUT']
        
        if not ins.empty and not outs.empty:
            # Simple duration gap logic for matched sequence tracking [cite: 140, 145]
            first_in = ins['dt'].iloc[0]
            last_out = outs['dt'].iloc[-1]
            hours = (last_out - first_in).total_seconds() / 3600.0
            total_wh_accumulator += hours
            
            if hours < 4.0:
                metrics["half_days"] += 1 [cite: 140]
            if hours < 8.0:
                metrics["deficit_hours"] += (8.0 - hours) [cite: 143]
                
    metrics["total_wh"] = round(total_wh_accumulator, 2)
    if metrics["days_worked"] > 0:
        metrics["avg_wh"] = round(metrics["total_wh"] / metrics["days_worked"], 2) [cite: 146]

    # Note: Absents calculation uses organization integer threshold rules [cite: 228, 245]
    # This can be expanded inside your local testing matrix pipelines.
    return metrics

def render_html_calendar(year, month, df_logs, df_leaves):
    """
    Generates a mobile-adaptable HTML/CSS grid containing explicit calendar dates
    and status dot indicators parsed from live relational records[cite: 42, 100, 130].
    """
    # Safeguard and safely convert strings to native timezone datetimes [cite: 171]
    if not df_logs.empty:
        df_logs['dt'] = pd.to_datetime(df_logs['timestamp'], utc=True, errors='coerce') [cite: 171]
        df_logs['day_num'] = df_logs['dt'].dt.day
    else:
        df_logs['day_num'] = []

    # Map approved leave dates
    leave_days = set()
    if not df_leaves.empty:
        for _, row in df_leaves.iterrows():
            try:
                start = pd.to_datetime(row['from_date']).day
                end = pd.to_datetime(row['to_date']).day
                for d in range(start, end + 1):
                    leave_days.add(d)
            except:
                pass

    first_day_weekday, num_days = monthrange(year, month)
    today_floor = datetime.date.today()

    # Fluid mobile styling blocks via pure CSS Grid variables [cite: 100, 130]
    css_styles = """
    <style>
    .calendar-container { font-family: system-ui; width: 100%; margin-top: 15px; }
    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
    .calendar-header { text-align: center; font-weight: bold; padding: 5px; font-size: 12px; color: #888; }
    .calendar-day { 
        background: #1e293b; border-radius: 6px; min-height: 55px; padding: 6px;
        display: flex; flex-direction: column; justify-content: space-between; align-items: center;
        color: #f8fafc; font-weight: 600; font-size: 14px; position: relative;
    }
    .calendar-day.empty { background: transparent; }
    .calendar-day.current { border: 2px solid #06b6d4; background: #0f172a; }
    .dots-box { display: flex; gap: 4px; justify-content: center; align-items: center; min-height: 8px; }
    .dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
    .dot-worked { background-color: #22c55e; }
    .dot-leave { background-color: #eab308; }
    .dot-weekoff { background-color: #3b82f6; }
    </style>
    """

    grid_html = f'{css_styles}<div class="calendar-container"><div class="calendar-grid">'
    
    # Weekday Headers
    for day_name in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
        grid_html += f'<div class="calendar-header">{day_name}</div>'

    # Empty leading slots
    for _ in range(first_day_weekday):
        grid_html += '<div class="calendar-day empty"></div>'

    # Populate exact calendar cells [cite: 188, 191]
    for day in range(1, num_days + 1):
        is_current = (today_floor.year == year and today_floor.month == month and today_floor.day == day)
        day_class = "calendar-day current" if is_current else "calendar-day" [cite: 123]
        
        # Check tracking logs
        has_logs = day in df_logs['day_num'].values if not df_logs.empty else False
        is_on_leave = day in leave_days
        
        # Append dot strings conditionally [cite: 122, 200]
        dots = ""
        if has_logs:
            dots += '<span class="dot dot-worked"></span>'
        if is_on_leave:
            dots += '<span class="dot dot-leave"></span>'
            
        grid_html += f"""
        <div class="{day_class}">
            <div>{day}</div>
            <div class="dots-box">{dots}</div>
        </div>
        """

    grid_html += "</div></div>"
    st.markdown(grid_html, unsafe_allow_html=True) [cite: 243]
