import pandas as pd
from datetime import datetime, time, timedelta, date
import calendar

def calculate_attendance_metrics(df_logs, leaves_data, work_days_count, org_start, org_end, curr_year, curr_month):
    metrics = {
        "absents": 0, "on_leave": 0, "half_days": 0, "late_ins": 0,
        "early_outs": 0, "deficit_hours": 0.0, "total_wh": 0.0,
        "days_worked": 0, "avg_wh": 0.0, 
        "worked_days_set": set(), "week_offs_set": set(),
        "approved_leave_days": set()
    }
    
    now = datetime.now()
    
    # 1. Process Attendance Logs & Kiosk Overrides
    if not df_logs.empty:
        df_logs['dt'] = pd.to_datetime(df_logs['timestamp'], utc=True, errors='coerce')
        df_logs = df_logs.dropna(subset=['dt'])
        
        if not df_logs.empty:
            df_logs['date'] = df_logs['dt'].dt.date
            
            # Map structural logs separately based on explicit action strings
            metrics["worked_days_set"] = set(df_logs[df_logs['action'].isin(['IN', 'OUT'])]['dt'].dt.day.unique())
            metrics["week_offs_set"] = set(df_logs[df_logs['action'] == 'WEEK_OFF']['dt'].dt.day.unique())
            
            for _, group in df_logs[df_logs['action'].isin(['IN', 'OUT'])].groupby('date'):
                day_hours = 0.0
                last_in = None
                sorted_group = group.sort_values('dt')
                
                for _, row in sorted_group.iterrows():
                    log_time = row['dt'].time()
                    if row['action'] == 'IN':
                        last_in = row['dt']
                        if log_time > org_start: 
                            metrics["late_ins"] += 1
                    elif row['action'] == 'OUT' and last_in is not None:
                        day_hours += (row['dt'] - last_in).total_seconds() / 3600.0
                        last_in = None
                        if log_time < org_end: 
                            metrics["early_outs"] += 1
                            
                metrics["total_wh"] += day_hours
                if 0 < day_hours < 4.0: 
                    metrics["half_days"] += 1
                if day_hours < 8.0: 
                    metrics["deficit_hours"] += (8.0 - day_hours)

    metrics["days_worked"] = len(metrics["worked_days_set"])
    metrics["avg_wh"] = round(metrics["total_wh"] / metrics["days_worked"], 2) if metrics["days_worked"] > 0 else 0.0
    metrics["total_wh"] = round(metrics["total_wh"], 2)
    metrics["deficit_hours"] = round(metrics["deficit_hours"], 1)

    # 2. Process Leaves Data
    for lv in leaves_data:
        if lv.get('status') == 'Approved':
            lv_from = datetime.strptime(lv['from_date'], "%Y-%m-%d").date()
            lv_to = datetime.strptime(lv['to_date'], "%Y-%m-%d").date()
            
            if lv_from.month == curr_month or lv_to.month == curr_month:
                metrics["on_leave"] += lv['no_of_days']
                
            curr_step = lv_from
            while curr_step <= lv_to:
                if curr_step.month == curr_month: 
                    metrics["approved_leave_days"].add(curr_step.day)
                curr_step += timedelta(days=1)
            
    # 3. Process Absents (past empty slots are only absent if not explicitly marked week off)
    max_day = now.day if (now.year == curr_year and now.month == curr_month) else calendar.monthrange(curr_year, curr_month)[1]
    
    for d in range(1, max_day + 1):
        if d not in metrics["worked_days_set"] and d not in metrics["approved_leave_days"] and d not in metrics["week_offs_set"]: 
            metrics["absents"] += 1
                
    return metrics
