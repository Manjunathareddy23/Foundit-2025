import uuid
from datetime import datetime, timedelta
import streamlit as st
from database import get_db_connection

def add_task(task_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_id = str(uuid.uuid4())
        
        cursor.execute('''
        INSERT INTO tasks (
            id, title, description, priority, status, due_date, 
            created_date, modified_date, assigned_by, assigned_to, 
            tags, recurring, recurrence_end_date, reminder, time_estimate, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, 
            task_data['title'], 
            task_data.get('description', ''),
            task_data['priority'],
            task_data['status'],
            task_data.get('due_date', None),
            now,
            now,
            task_data.get('assigned_by', st.session_state.user_id),
            task_data.get('assigned_to', st.session_state.user_id),
            task_data.get('tags', ''),
            task_data.get('recurring', 'None'),
            task_data.get('recurrence_end_date', None),
            task_data.get('reminder', None),
            task_data.get('time_estimate', 0),
            task_data.get('notes', '')
        ))
        
        # If task is assigned to someone else, create notification
        if task_data.get('assigned_to') != st.session_state.user_id:
            notification_id = str(uuid.uuid4())
            message = f"You have been assigned a new task: {task_data['title']}"
            
            cursor.execute('''
            INSERT INTO notifications (id, user_id, task_id, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                notification_id,
                task_data.get('assigned_to'),
                task_id,
                message,
                now
            ))
        
        conn.commit()
        conn.close()
        
        # Handle recurring tasks
        if task_data.get('recurring', 'None') != 'None':
            create_recurring_tasks(task_id, task_data)
        
        return True, "Task added successfully", task_id
    except Exception as e:
        return False, f"Error adding task: {str(e)}", None

def get_tasks(user_id=None, filters=None, sort_by=None, sort_order="asc"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks"
        params = []
        
        # Apply filters
        if filters or user_id:
            query += " WHERE "
            conditions = []
            
            if user_id:
                conditions.append("(assigned_to = ? OR assigned_by = ?)")
                params.extend([user_id, user_id])
            
            if filters:
                if 'status' in filters:
                    conditions.append("status = ?")
                    params.append(filters['status'])
                
                if 'priority' in filters:
                    conditions.append("priority = ?")
                    params.append(filters['priority'])
                
                if 'due_date' in filters:
                    conditions.append("due_date = ?")
                    params.append(filters['due_date'])
                
                if 'tags' in filters:
                    conditions.append("tags LIKE ?")
                    params.append(f"%{filters['tags']}%")
                
                if 'search' in filters:
                    search_term = f"%{filters['search']}%"
                    conditions.append("(title LIKE ? OR description LIKE ? OR tags LIKE ?)")
                    params.extend([search_term, search_term, search_term])
            
            query += " AND ".join(conditions)
        
        # Apply sorting
        if sort_by:
            query += f" ORDER BY {sort_by} "
            if sort_order.lower() == "desc":
                query += "DESC"
            else:
                query += "ASC"
        else:
            # Default sort by due date
            query += " ORDER BY due_date ASC"
        
        cursor.execute(query, params)
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # Get assigned user details
        for task in tasks:
            if task['assigned_to'] != user_id:
                cursor.execute("SELECT username FROM users WHERE id = ?", (task['assigned_to'],))
                user = cursor.fetchone()
                if user:
                    task['assigned_to_name'] = user['username']
                else:
                    task['assigned_to_name'] = "Unknown"
            else:
                task['assigned_to_name'] = "You"
        
        conn.close()
        return tasks
    except Exception as e:
        st.error(f"Error fetching tasks: {str(e)}")
        return []

def update_task(task_id, updates):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current task details
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        current_task = cursor.fetchone()
        
        if not current_task:
            conn.close()
            return False, "Task not found"
        
        # Update modified date
        updates['modified_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build update query
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
        
        # Execute update
        cursor.execute(query, list(updates.values()) + [task_id])
        
        # Create notification if assigned_to has changed
        if 'assigned_to' in updates and updates['assigned_to'] != current_task['assigned_to']:
            notification_id = str(uuid.uuid4())
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"You have been assigned a task: {current_task['title']}"
            
            cursor.execute('''
            INSERT INTO notifications (id, user_id, task_id, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                notification_id,
                updates['assigned_to'],
                task_id,
                message,
                now
            ))
        
        conn.commit()
        conn.close()
        return True, "Task updated successfully"
    except Exception as e:
        return False, f"Error updating task: {str(e)}"

def delete_task(task_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete related notifications first
        cursor.execute("DELETE FROM notifications WHERE task_id = ?", (task_id,))
        
        # Delete the task
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        
        conn.commit()
        conn.close()
        return True, "Task deleted successfully"
    except Exception as e:
        return False, f"Error deleting task: {str(e)}"

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
