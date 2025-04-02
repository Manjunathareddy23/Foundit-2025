import streamlit as st
from datetime import datetime, timedelta
from db_utils import get_db_connection

def get_task_statistics(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all tasks for the user
        cursor.execute("""
        SELECT * FROM tasks 
        WHERE assigned_to = ? OR assigned_by = ?
        """, (user_id, user_id))
        
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Calculate statistics
        stats = {
            'total': len(tasks),
            'completed': len([t for t in tasks if t['status'] == 'Completed']),
            'pending': len([t for t in tasks if t['status'] == 'Pending']),
            'in_progress': len([t for t in tasks if t['status'] == 'In Progress']),
            'overdue': 0,
            'due_today': 0,
            'due_this_week': 0,
            'priority_high': len([t for t in tasks if t['priority'] == 'High']),
            'priority_medium': len([t for t in tasks if t['priority'] == 'Medium']),
            'priority_low': len([t for t in tasks if t['priority'] == 'Low']),
            'time_spent': sum([t['time_spent'] or 0 for t in tasks]),
            'estimated_time': sum([t['time_estimate'] or 0 for t in tasks])
        }
        
        # Calculate date-based statistics
        today = datetime.now().date()
        for task in tasks:
            if task['due_date'] and task['status'] != 'Completed':
                due_date = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                
                if due_date < today:
                    stats['overdue'] += 1
                elif due_date == today:
                    stats['due_today'] += 1
                elif due_date <= today + timedelta(days=7):
                    stats['due_this_week'] += 1
        
        # Calculate completion rate
        if stats['total'] > 0:
            stats['completion_rate'] = (stats['completed'] / stats['total']) * 100
        else:
            stats['completion_rate'] = 0
        
        # Calculate time efficiency
        if stats['estimated_time'] > 0:
            stats['time_efficiency'] = (stats['time_spent'] / stats['estimated_time']) * 100
        else:
            stats['time_efficiency'] = 0
        
        # Calculate trending data (tasks by creation date)
        task_dates = {}
        for task in tasks:
            date = task['created_date'].split(' ')[0]  # Get just the date part
            if date in task_dates:
                task_dates[date] += 1
            else:
                task_dates[date] = 1
        
        stats['task_trend'] = task_dates
        
        # Calculate status distribution
        status_count = {}
        for task in tasks:
            status = task['status']
            if status in status_count:
                status_count[status] += 1
            else:
                status_count[status] = 1
        
        stats['status_distribution'] = status_count
        
        # Calculate priority distribution
        priority_count = {}
        for task in tasks:
            priority = task['priority']
            if priority in priority_count:
                priority_count[priority] += 1
            else:
                priority_count[priority] = 1
        
        stats['priority_distribution'] = priority_count
        
        return stats
    except Exception as e:
        st.error(f"Error calculating statistics: {str(e)}")
        return {}
