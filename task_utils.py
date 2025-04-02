import streamlit as st
import uuid
from datetime import datetime, timedelta
from db_utils import get_db_connection
from notification_utils import create_notification

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
            message = f"You have been assigned a new task: {task_data['title']}"
            create_notification(task_data.get('assigned_to'), task_id, message)
        
        conn.commit()
        conn.close()
        
        # Handle recurring tasks
        if task_data.get('recurring', 'None') != 'None':
            create_recurring_tasks(task_id, task_data)
        
        return True, "Task added successfully", task_id
    except Exception as e:
        return False, f"Error adding task: {str(e)}", None

def create_recurring_tasks(parent_task_id, task_data):
    try:
        # Get the parent task
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (parent_task_id,))
        parent_task = cursor.fetchone()
        conn.close()
        
        if not parent_task:
            return False
        
        # Convert due_date to datetime
        if not parent_task['due_date']:
            return False
        
        due_date = datetime.strptime(parent_task['due_date'], "%Y-%m-%d")
        end_date = None
        
        if task_data.get('recurrence_end_date'):
            end_date = datetime.strptime(task_data['recurrence_end_date'], "%Y-%m-%d")
        
        # Determine the recurrence pattern and number of instances to create
        recurring_type = task_data.get('recurring', 'None')
        instances_to_create = 0
        
        if recurring_type == 'Daily':
            if end_date:
                instances_to_create = (end_date - due_date).days
            else:
                instances_to_create = 30  # Create a month of daily tasks
        elif recurring_type == 'Weekly':
            if end_date:
                instances_to_create = ((end_date - due_date).days // 7)
            else:
                instances_to_create = 12  # Create 3 months of weekly tasks
        elif recurring_type == 'Monthly':
            if end_date:
                instances_to_create = ((end_date.year - due_date.year) * 12 + 
                                      end_date.month - due_date.month)
            else:
                instances_to_create = 6  # Create 6 months of monthly tasks
        elif recurring_type == 'Yearly':
            if end_date:
                instances_to_create = (end_date.year - due_date.year)
            else:
                instances_to_create = 3  # Create 3 years of yearly tasks
        
        # Create recurring task instances
        for i in range(1, instances_to_create + 1):
            new_task = dict(task_data)
            
            if recurring_type == 'Daily':
                new_due_date = due_date + timedelta(days=i)
            elif recurring_type == 'Weekly':
                new_due_date = due_date + timedelta(weeks=i)
            elif recurring_type == 'Monthly':
                new_month = ((due_date.month - 1 + i) % 12) + 1
                new_year = due_date.year + ((due_date.month - 1 + i) // 12)
                new_due_date = due_date.replace(year=new_year, month=new_month)
            elif recurring_type == 'Yearly':
                new_due_date = due_date.replace(year=due_date.year + i)
            
            new_task['due_date'] = new_due_date.strftime("%Y-%m-%d")
            new_task['title'] = f"{task_data['title']} ({i+1})"
            
            add_task(new_task)
        
        return True
    except Exception as e:
        st.error(f"Error creating recurring tasks: {str(e)}")
        return False

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
            message = f"You have been assigned a task: {current_task['title']}"
            create_notification(updates['assigned_to'], task_id, message)
        
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
