import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
from datetime import datetime, timedelta
import json
import os
import sqlite3
import uuid
import time
import hashlib
import base64
from io import StringIO, BytesIO
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# Function to load and apply CSS
def load_css(file_name):
    with open(file_name, 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize database connection
def get_db_connection():
    conn = sqlite3.connect('task_manager.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        created_at TEXT NOT NULL,
        last_login TEXT,
        theme TEXT DEFAULT 'light'
    )
    ''')
    
    # Create tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        due_date TEXT,
        created_date TEXT NOT NULL,
        modified_date TEXT NOT NULL,
        assigned_by TEXT,
        assigned_to TEXT NOT NULL,
        tags TEXT,
        recurring TEXT,
        recurrence_end_date TEXT,
        reminder TEXT,
        time_estimate INTEGER,
        time_spent INTEGER DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (assigned_to) REFERENCES users (id)
    )
    ''')
    
    # Create notifications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        task_id TEXT,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        read INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    ''')
    
    # Create settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        setting_key TEXT NOT NULL,
        setting_value TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, setting_key)
    )
    ''')
    
    # Create backup table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS backups (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        created_at TEXT NOT NULL,
        size INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create default admin user if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_id = str(uuid.uuid4())
        hashed_password = hashlib.sha256("admin".encode()).hexdigest()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (id, username, password, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (admin_id, "admin", hashed_password, "admin@example.com", now)
        )
    
    conn.commit()
    conn.close()

# User Authentication Functions
def register_user(username, password, email=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False, "Username already exists"
        
        # Check if email already exists (if provided)
        if email:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return False, "Email already exists"
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "INSERT INTO users (id, username, password, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, hashed_password, email, now)
        )
        
        conn.commit()
        conn.close()
        return True, "User registered successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"

def login_user(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user by username
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return False, "Invalid username or password"
        
        # Verify password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if user['password'] != hashed_password:
            conn.close()
            return False, "Invalid username or password"
        
        # Update last login time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user['id']))
        
        conn.commit()
        conn.close()
        
        # Set session variables
        st.session_state.user_id = user['id']
        st.session_state.username = user['username']
        st.session_state.logged_in = True
        st.session_state.theme = user['theme'] or 'light'
        
        return True, "Login successful"
    except Exception as e:
        return False, f"Error: {str(e)}"

def logout_user():
    for key in ['user_id', 'username', 'logged_in', 'theme']:
        if key in st.session_state:
            del st.session_state[key]

# Task Management Functions
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

# Notification Functions
def get_notifications(user_id, unread_only=False):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]
        
        if unread_only:
            query += " AND read = 0"
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        notifications = [dict(row) for row in cursor.fetchall()]
        
        # Get task details for each notification
        for notification in notifications:
            if notification['task_id']:
                cursor.execute("SELECT title FROM tasks WHERE id = ?", (notification['task_id'],))
                task = cursor.fetchone()
                if task:
                    notification['task_title'] = task['title']
                else:
                    notification['task_title'] = "Unknown Task"
        
        conn.close()
        return notifications
    except Exception as e:
        st.error(f"Error fetching notifications: {str(e)}")
        return []

def mark_notification_as_read(notification_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error marking notification as read: {str(e)}")
        return False

# Backup and Restore Functions
def create_backup(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all tasks for the user
        cursor.execute("""
        SELECT * FROM tasks 
        WHERE assigned_to = ? OR assigned_by = ?
        """, (user_id, user_id))
        
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # Create backup file
        backup_data = {
            'tasks': tasks,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': user_id
        }
        
        backup_json = json.dumps(backup_data, indent=2)
        
        # Save backup info to database
        backup_id = str(uuid.uuid4())
        filename = f"backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
        INSERT INTO backups (id, user_id, filename, created_at, size)
        VALUES (?, ?, ?, ?, ?)
        """, (
            backup_id,
            user_id,
            filename,
            now,
            len(backup_json)
        ))
        
        conn.commit()
        conn.close()
        
        return True, backup_json, filename
    except Exception as e:
        return False, f"Error creating backup: {str(e)}", None

def restore_from_backup(backup_data, user_id):
    try:
        # Parse backup data
        backup = json.loads(backup_data)
        
        # Validate backup format
        if 'tasks' not in backup:
            return False, "Invalid backup format"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Process each task in the backup
        for task in backup['tasks']:
            # Check if task already exists
            cursor.execute("SELECT id FROM tasks WHERE id = ?", (task['id'],))
            existing_task = cursor.fetchone()
            
            if existing_task:
                # Update existing task
                task_id = task.pop('id')
                set_clause = ", ".join([f"{key} = ?" for key in task.keys()])
                query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
                cursor.execute(query, list(task.values()) + [task_id])
            else:
                # Insert new task
                placeholders = ", ".join(["?"] * len(task))
                columns = ", ".join(task.keys())
                query = f"INSERT INTO tasks ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(task.values()))
        
        # Commit transaction
        conn.commit()
        conn.close()
        
        return True, f"Successfully restored {len(backup['tasks'])} tasks"
    except Exception as e:
        # Rollback in case of error
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False, f"Error restoring backup: {str(e)}"

# Export Functions
def export_tasks_to_csv(tasks):
    try:
        df = pd.DataFrame(tasks)
        csv = df.to_csv(index=False)
        return csv
    except Exception as e:
        st.error(f"Error exporting to CSV: {str(e)}")
        return None

def export_tasks_to_json(tasks):
    try:
        return json.dumps(tasks, indent=2)
    except Exception as e:
        st.error(f"Error exporting to JSON: {str(e)}")
        return None

# Settings Functions
def get_user_settings(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT setting_key, setting_value FROM settings WHERE user_id = ?", (user_id,))
        settings = {row['setting_key']: row['setting_value'] for row in cursor.fetchall()}
        
        # Get user theme
        cursor.execute("SELECT theme FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user and user['theme']:
            settings['theme'] = user['theme']
        else:
            settings['theme'] = 'light'
        
        conn.close()
        return settings
    except Exception as e:
        st.error(f"Error fetching settings: {str(e)}")
        return {}

def update_user_settings(user_id, settings):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update theme in users table
        if 'theme' in settings:
            cursor.execute("UPDATE users SET theme = ? WHERE id = ?", (settings['theme'], user_id))
            # Update session state
            st.session_state.theme = settings['theme']
            # Remove from settings dict to avoid duplication
            theme = settings.pop('theme', None)
        
        # Update other settings
        for key, value in settings.items():
            # Check if setting already exists
            cursor.execute("SELECT id FROM settings WHERE user_id = ? AND setting_key = ?", (user_id, key))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("UPDATE settings SET setting_value = ? WHERE user_id = ? AND setting_key = ?", 
                              (value, user_id, key))
            else:
                setting_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO settings (id, user_id, setting_key, setting_value) VALUES (?, ?, ?, ?)",
                              (setting_id, user_id, key, value))
        
        conn.commit()
        conn.close()
        return True, "Settings updated successfully"
    except Exception as e:
        return False, f"Error updating settings: {str(e)}"

# UI Components and Pages
def login_page():
    st.title("Advanced Task Manager")
    st.subheader("Login to your account")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    success, message = login_user(username, password)
                    if success:
                        st.success(message)
                        st.experimental_rerun()
                    else:
                        st.error(message)
    
    with col2:
        with st.form("register_form"):
            st.subheader("New User? Register Here")
            new_username = st.text_input("Username")
            new_email = st.text_input("Email (optional)")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            register = st.form_submit_button("Register")
            
            if register:
                if not new_username or not new_password:
                    st.error("Username and password are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(new_username, new_password, new_email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

Here's the continuation of the `dashboard_page()` function and the rest of the code:

```python
def dashboard_page():
    st.title(f"Welcome, {st.session_state.username}!")
    
    # Get task statistics
    stats = get_task_statistics(st.session_state.user_id)
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tasks", stats.get('total', 0))
    
    with col2:
        st.metric("Completed", stats.get('completed', 0))
    
    with col3:
        st.metric("Pending", stats.get('pending', 0))
    
    with col4:
        st.metric("Overdue", stats.get('overdue', 0))
    
    # Display task distribution charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Task Status Distribution")
        
        if stats.get('status_distribution'):
            status_df = pd.DataFrame({
                'Status': list(stats['status_distribution'].keys()),
                'Count': list(stats['status_distribution'].values())
            })
            
            fig = px.pie(status_df, values='Count', names='Status', 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tasks available for status distribution")
    
    with col2:
        st.subheader("Task Priority Distribution")
        
        if stats.get('priority_distribution'):
            priority_df = pd.DataFrame({
                'Priority': list(stats['priority_distribution'].keys()),
                'Count': list(stats['priority_distribution'].values())
            })
            
            fig = px.bar(priority_df, x='Priority', y='Count', 
                        color='Priority', color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tasks available for priority distribution")
    
    # Display upcoming tasks and overdue tasks
    st.subheader("Task Timeline")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Due Today")
        tasks_due_today = get_tasks(
            st.session_state.user_id, 
            filters={'due_date': datetime.now().strftime("%Y-%m-%d"), 'status': 'Pending'}
        )
        
        if tasks_due_today:
            for task in tasks_due_today:
                with st.expander(f"{task['title']} - {task['priority']} Priority"):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Tags:** {task['tags']}")
                    st.write(f"**Assigned to:** {task['assigned_to_name']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Mark Complete", key=f"complete_today_{task['id']}"):
                            success, message = update_task(task['id'], {'status': 'Completed'})
                            if success:
                                st.success(message)
                                st.experimental_rerun()
                            else:
                                st.error(message)
                    with col2:
                        if st.button("View Details", key=f"view_today_{task['id']}"):
                            st.session_state.selected_task = task['id']
                            st.session_state.current_page = "task_details"
                            st.experimental_rerun()
        else:
            st.info("No tasks due today")
    
    with col2:
        st.markdown("#### Overdue")
        today = datetime.now().date()
        overdue_tasks = []
        
        all_tasks = get_tasks(st.session_state.user_id, filters={'status': 'Pending'})
        for task in all_tasks:
            if task['due_date']:
                due_date = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                if due_date < today:
                    overdue_tasks.append(task)
        
        if overdue_tasks:
            for task in overdue_tasks:
                with st.expander(f"{task['title']} - Due: {task['due_date']}"):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Priority:** {task['priority']}")
                    st.write(f"**Tags:** {task['tags']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Mark Complete", key=f"complete_overdue_{task['id']}"):
                            success, message = update_task(task['id'], {'status': 'Completed'})
                            if success:
                                st.success(message)
                                st.experimental_rerun()
                            else:
                                st.error(message)
                    with col2:
                        if st.button("View Details", key=f"view_overdue_{task['id']}"):
                            st.session_state.selected_task = task['id']
                            st.session_state.current_page = "task_details"
                            st.experimental_rerun()
        else:
            st.info("No overdue tasks")
    
    # Display task trend over time
    st.subheader("Task Creation Trend")
    
    if stats.get('task_trend'):
        # Convert to DataFrame
        trend_data = []
        for date, count in stats['task_trend'].items():
            trend_data.append({'Date': date, 'Tasks': count})
        
        trend_df = pd.DataFrame(trend_data)
        trend_df['Date'] = pd.to_datetime(trend_df['Date'])
        trend_df = trend_df.sort_values('Date')
        
        # Create line chart
        fig = px.line(trend_df, x='Date', y='Tasks', 
                     title='Tasks Created Over Time',
                     markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No task trend data available")
    
    # Display notifications
    st.subheader("Recent Notifications")
    notifications = get_notifications(st.session_state.user_id, unread_only=True)
    
    if notifications:
        for notification in notifications[:5]:  # Show only the 5 most recent
            with st.expander(f"{notification['message']} - {notification['created_at']}"):
                if notification.get('task_title'):
                    st.write(f"**Task:** {notification['task_title']}")
                
                if st.button("Mark as Read", key=f"read_{notification['id']}"):
                    if mark_notification_as_read(notification['id']):
                        st.success("Notification marked as read")
                        st.experimental_rerun()
    else:
        st.info("No unread notifications")

def add_task_page():
    st.title("Add New Task")
    
    # Check if we're editing a task
    editing = False
    task_data = {}
    
    if 'selected_task' in st.session_state and st.session_state.selected_task:
        editing = True
        # Get task details
        tasks = get_tasks(st.session_state.user_id)
        task_data = next((t for t in tasks if t['id'] == st.session_state.selected_task), None)
        
        if task_data:
            st.subheader(f"Editing Task: {task_data['title']}")
        else:
            st.error("Task not found!")
            st.session_state.selected_task = None
            return
    
    # Get all users for assignment
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Create a form for task input
    with st.form("task_form"):
        title = st.text_input("Title", value=task_data.get('title', ''))
        description = st.text_area("Description", value=task_data.get('description', ''))
        
        col1, col2 = st.columns(2)
        
        with col1:
            priority = st.selectbox(
                "Priority", 
                ["Low", "Medium", "High"],
                index=["Low", "Medium", "High"].index(task_data.get('priority', 'Medium')) if task_data.get('priority') else 1
            )
            
            status = st.selectbox(
                "Status", 
                ["Pending", "In Progress", "Completed"],
                index=["Pending", "In Progress", "Completed"].index(task_data.get('status', 'Pending')) if task_data.get('status') else 0
            )
            
            due_date = st.date_input(
                "Due Date",
                value=datetime.strptime(task_data.get('due_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d') if task_data.get('due_date') else datetime.now()
            )
        
        with col2:
            assigned_to = st.selectbox(
                "Assign To",
                options=[user['id'] for user in users],
                format_func=lambda x: next((user['username'] for user in users if user['id'] == x), x),
                index=[user['id'] for user in users].index(task_data.get('assigned_to', st.session_state.user_id)) if task_data.get('assigned_to') in [user['id'] for user in users] else [user['id'] for user in users].index(st.session_state.user_id)
            )
            
            tags = st.text_input("Tags (comma separated)", value=task_data.get('tags', ''))
            
            time_estimate = st.number_input(
                "Estimated Time (hours)", 
                min_value=0.0, 
                value=float(task_data.get('time_estimate', 0) or 0) / 60,
                step=0.5
            )
        
        # Advanced options expander
        with st.expander("Advanced Options"):
            col1, col2 = st.columns(2)
            
            with col1:
                recurring = st.selectbox(
                    "Recurring",
                    ["None", "Daily", "Weekly", "Monthly", "Yearly"],
                    index=["None", "Daily", "Weekly", "Monthly", "Yearly"].index(task_data.get('recurring', 'None')) if task_data.get('recurring') else 0
                )
                
                if recurring != "None":
                    recurrence_end_date = st.date_input(
                        "Recurrence End Date",
                        value=datetime.strptime(task_data.get('recurrence_end_date', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')), '%Y-%m-%d') if task_data.get('recurrence_end_date') else (datetime.now() + timedelta(days=30))
                    )
                else:
                    recurrence_end_date = None
            
            with col2:
                reminder = st.selectbox(
                    "Reminder",
                    ["None", "1 hour before", "1 day before", "1 week before"],
                    index=["None", "1 hour before", "1 day before", "1 week before"].index(task_data.get('reminder', 'None')) if task_data.get('reminder') else 0
                )
                
                time_spent = st.number_input(
                    "Time Spent (hours)",
                    min_value=0.0,
                    value=float(task_data.get('time_spent', 0) or 0) / 60,
                    step=0.5
                )
            
            notes = st.text_area("Notes", value=task_data.get('notes', ''))
        
        # Submit button
        submit_button = st.form_submit_button("Save Task")
        
        if submit_button:
            if not title:
                st.error("Title is required!")
            else:
                # Prepare task data
                new_task_data = {
                    'title': title,
                    'description': description,
                    'priority': priority,
                    'status': status,
                    'due_date': due_date.strftime('%Y-%m-%d'),
                    'assigned_to': assigned_to,
                    'tags': tags,
                    'time_estimate': int(time_estimate * 60),  # Convert to minutes
                    'recurring': recurring,
                    'notes': notes
                }
                
                if recurring != "None" and recurrence_end_date:
                    new_task_data['recurrence_end_date'] = recurrence_end_date.strftime('%Y-%m-%d')
                
                if reminder != "None":
                    new_task_data['reminder'] = reminder
                
                if time_spent > 0:
                    new_task_data['time_spent'] = int(time_spent * 60)  # Convert to minutes
                
                if editing:
                    # Update existing task
                    success, message = update_task(st.session_state.selected_task, new_task_data)
                    if success:
                        st.success(message)
                        # Clear selected task
                        st.session_state.selected_task = None
                        # Redirect to tasks page
                        st.session_state.current_page = "view_tasks"
                        st.experimental_rerun()
                    else:
                        st.error(message)
                else:
                    # Add new task
                    success, message, _ = add_task(new_task_data)
                    if success:
                        st.success(message)
                        # Redirect to tasks page
                        st.session_state.current_page = "view_tasks"
                        st.experimental_rerun()
                    else:
                        st.error(message)
    
    # Cancel button for editing
    if editing:
        if st.button("Cancel"):
            st.session_state.selected_task = None
            st.session_state.current_page = "view_tasks"
            st.experimental_rerun()

def view_tasks_page():
    st.title("View Tasks")
    
    # Filters
    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            filter_status = st.selectbox(
                "Status",
                ["All", "Pending", "In Progress", "Completed"]
            )
        
        with col2:
            filter_priority = st.selectbox(
                "Priority",
                ["All", "Low", "Medium", "High"]
            )
        
        with col3:
            filter_tags = st.text_input("Tags")
        
        with col4:
            filter_search = st.text_input("Search")
        
        # Apply filters button
        col1, col2 = st.columns([1, 4])
        with col1:
            apply_filters = st.button("Apply Filters")
        with col2:
            clear_filters = st.button("Clear Filters")
    
    # Build filters dictionary
    filters = {}
    if apply_filters:
        if filter_status != "All":
            filters['status'] = filter_status
        
        if filter_priority != "All":
            filters['priority'] = filter_priority
        
        if filter_tags:
            filters['tags'] = filter_tags
        
        if filter_search:
            filters['search'] = filter_search
    
    if clear_filters:
        # Reset all filters
        st.experimental_rerun()
    
    # Get tasks with filters
    tasks = get_tasks(st.session_state.user_id, filters=filters)
    
    # Display tasks
    if tasks:
        # Sorting options
        col1, col2 = st.columns([1, 4])
        with col1:
            sort_by = st.selectbox(
                "Sort By",
                ["due_date", "priority", "status", "title"]
            )
        with col2:
            sort_order = st.radio(
                "Order",
                ["Ascending", "Descending"],
                horizontal=True
            )
        
        # Sort tasks
        tasks = get_tasks(
            st.session_state.user_id, 
            filters=filters,
            sort_by=sort_by,
            sort_order="asc" if sort_order == "Ascending" else "desc"
        )
        
        # Display tasks in a table
        task_df = pd.DataFrame([
            {
                'Title': t['title'],
                'Priority': t['priority'],
                'Status': t['status'],
                'Due Date': t['due_date'],
                'Assigned To': t['assigned_to_name'],
                'Tags': t['tags']
            } for t in tasks
        ])
        
        st.dataframe(task_df, use_container_width=True)
        
        # Export options
        st.subheader("Export Tasks")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export as CSV"):
                csv_data = export_tasks_to_csv(tasks)
                if csv_data:
                    st.download_button(
                        "Download CSV",
                        csv_data,
                        "tasks.csv",
                        "text/csv"
                    )
        
        with col2:
            if st.button("Export as JSON"):
                json_data = export_tasks_to_json(tasks)
                if json_data:
                    st.download_button(
                        "Download JSON",
                        json_data,
                        "tasks.json",
                        "application/json"
                    )
        
        # Task details section
        st.subheader("Task Details")
        selected_task_id = st.selectbox(
            "Select a task to view details",
            options=[t['id'] for t in tasks],
            format_func=lambda x: next((t['title'] for t in tasks if t['id'] == x), x)
        )
        
        if selected_task_id:
            selected_task = next((t for t in tasks if t['id'] == selected_task_id), None)
            
            if selected_task:
                with st.expander("Task Details", expanded=True):
                    st.write(f"**Title:** {selected_task['title']}")
                    st.write(f"**Description:** {selected_task['description']}")
                    st.write(f"**Priority:** {selected_task['priority']}")
                    st.write(f"**Status:** {selected_task['status']}")
                    st.write(f"**Due Date:** {selected_task['due_date']}")
                    st.write(f"**Assigned To:** {selected_task['assigned_to_name']}")
                    st.write(f"**Tags:** {selected_task['tags']}")
                    
                    if selected_task.get('notes'):
                        st.write(f"**Notes:** {selected_task['notes']}")
                    
                    # Task actions
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Edit Task"):
                            st.session_state.selected_task = selected_task_id
                            st.session_state.current_page = "add_task"
                            st.experimental_rerun()
                    
                    with col2:
                        if selected_task['status'] != 'Completed':
                            if st.button("Mark as Complete"):
                                success, message = update_task(selected_task_id, {'status': 'Completed'})
                                if success:
                                    st.success(message)
                                    st.experimental_rerun()
                                else:
                                    st.error(message)
                        else:
                            if st.button("Mark as Pending"):
                                success, message = update_task(selected_task_id, {'status': 'Pending'})
                                if success:
                                    st.success(message)
                                    st.experimental_rerun()
                                else:
                                    st.error(message)
                    
                    with col3:
                        if st.button("Delete Task"):
                            st.session_state.confirm_delete = selected_task_id
                            st.experimental_rerun()
                
                # Confirm delete dialog
                if 'confirm_delete' in st.session_state and st.session_state.confirm_delete == selected_task_id:
                    st.warning("Are you sure you want to delete this task? This action cannot be undone.")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Yes, Delete"):
                            success, message = delete_task(selected_task_id)
                            if success:
                                st.success(message)
                                st.session_state.confirm_delete = None
                                st.experimental_rerun()
                            else:
                                st.error(message)
                    
                    with col2:
                        if st.button("Cancel"):
                            st.session_state.confirm_delete = None
                            st.experimental_rerun()
    else:
        st.info("No tasks found. Add a new task to get started!")
        
        if st.button("Add New Task"):
            st.session_state.current_page = "add_task"
            st.experimental_rerun()

def statistics_page():
    st.title("Task Statistics and Reports")
    
    # Get task statistics
    stats = get_task_statistics(st.session_state.user_id)
    
    # Summary metrics
    st.subheader("Task Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tasks", stats.get('total', 0))
    
    with col2:
        completion_rate = stats.get('completion_rate', 0)
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    with col3:
        st.metric("Overdue Tasks", stats.get('overdue', 0))
    
    with col4:
        st.metric("Due This Week", stats.get('due_this_week', 0))
    
    # Task status breakdown
    st.subheader("Task Status Breakdown")
    col1, col2 = st.columns(2)
    
    with col1:
        status_data = {
            'Completed': stats.get('completed', 0),
            'In Progress': stats.get('in_progress', 0),
            'Pending': stats.get('pending', 0)
        }
        
        status_df = pd.DataFrame({
            'Status': list(status_data.keys()),
            'Count': list(status_data.values())
        })
        
        fig = px.pie(status_df, values='Count', names='Status',
                    title='Tasks by Status',
                    color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        priority_data = {
            'High': stats.get('priority_high', 0),
            'Medium': stats.get('priority_medium', 0),
            'Low': stats.get('priority_low', 0)
        }
        
        priority_df = pd.DataFrame({
            'Priority': list(priority_data.keys()),
            'Count': list(priority_data.values())
        })
        
        fig = px.bar(priority_df, x='Priority', y='Count',
                    title='Tasks by Priority',
                    color='Priority',
                    color_discrete_sequence=px.colors.qualitative.Bold)
        st.plotly_chart(fig, use_container_width=True)
    
    # Task trend over time
    st.subheader("Task Creation Trend")
    
    if stats.get('task_trend'):
        trend_data = []
        for date, count in stats['task_trend'].items():
            trend_data.append({'Date': date, 'Tasks': count})
        
        trend_df = pd.DataFrame(trend_data)
        trend_df['Date'] = pd.to_datetime(trend_df['Date'])
        trend_df = trend_df.sort_values('Date')
        
        fig = px.line(trend_df, x='Date', y='Tasks',
                     title='Tasks Created Over Time',
                     markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No task trend data available")
    
    # Time efficiency
    st.subheader("Time Efficiency")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Estimated Time (hours)", round(stats.get('estimated_time', 0) / 60, 1))
    
    with col2:
        st.metric("Time Spent (hours)", round(stats.get('time_spent', 0) / 60, 1))
    
    if stats.get('estimated_time', 0) > 0:
        efficiency = (stats.get('time_spent', 0) / stats.get('estimated_time', 0)) * 100
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=efficiency,
            title={'text': "Time Efficiency"},
            gauge={
                'axis': {'range': [0, 200], 'tickwidth': 1},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 80], 'color': "lightgreen"},
                    {'range': [80, 120], 'color': "yellow"},
                    {'range': [120, 200], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 100
                }
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No time data available for efficiency calculation")

def settings_page():
    st.title("Settings")
    
    # Get current user settings
    settings = get_user_settings(st.session_state.user_id)
    
    # Tabs for different settings categories
    tab1, tab2, tab3 = st.tabs(["Appearance", "Backup & Restore", "Account"])
    
    with tab1:
        st.subheader("Appearance Settings")
        
        # Theme selection
        theme = st.selectbox(
            "Theme",
            ["light", "dark", "custom"],
            index=["light", "dark", "custom"].index(settings.get('theme', 'light')) if settings.get('theme') in ["light", "dark", "custom"] else 0
        )
        
        # Custom theme options
        if theme == "custom":
            primary_color = st.color_picker("Primary Color", settings.get('primary_color', '#3b82f6'))
            secondary_color = st.color_picker("Secondary Color", settings.get('secondary_color', '#64748b'))
            background_color = st.color_picker("Background Color", settings.get('background_color', '#f1f5f9'))
            text_color = st.color_picker("Text Color", settings.get('text_color', '#0f172a'))
        
        # Save appearance settings
        if st.button("Save Appearance Settings"):
            new_settings = {'theme': theme}
            
            if theme == "custom":
                new_settings['primary_color'] = primary_color
                new_settings['secondary_color'] = secondary_color
                new_settings['background_color'] = background_color
                new_settings['text_color'] = text_color
            
            success, message = update_user_settings(st.session_state.user_id, new_settings)
            if success:
                st.success(message)
                st.experimental_rerun()
            else:
                st.error(message)
    
    with tab2:
        st.subheader("Backup & Restore")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Create Backup")
            
            if st.button("Create Backup"):
                success, backup_data, filename = create_backup(st.session_state.user_id)
                
                if success:
                    st.success(f"Backup created: {filename}")
                    st.download_button(
                        "Download Backup",
                        backup_data,
                        filename,
                        "application/json"
                    )
                else:
                    st.error(backup_data)  # Error message is in backup_data
        
        with col2:
            st.markdown("#### Restore from Backup")
            
            uploaded_file = st.file_uploader("Upload Backup File", type=["json"])
            
            if uploaded_file is not None:
                if st.button("Restore from Backup"):
                    backup_data = uploaded_file.getvalue().decode('utf-8')
                    success, message = restore_from_backup(backup_data, st.session_state.user_id)
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    with tab3:
        st.subheader("Account Settings")
        
        # Get user details
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (st.session_state.user_id,))
        user = dict(cursor.fetchone())
        conn.close()
        
        # Display account info
        st.markdown("#### Account Information")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Email:** {user['email'] or 'Not set'}")
        st.write(f"**Account Created:** {user['created_at']}")
        st.write(f"**Last Login:** {user['last_login']}")
        
        # Change password
        st.markdown("#### Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submit = st.form_submit_button("Change Password")
            
            if submit:
                if not current_password or not new_password or not confirm_password:
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    # Verify current password
                    hashed_current = hashlib.sha256(current_password.encode()).hexdigest()
                    
                    if hashed_current != user['password']:
                        st.error("Current password is incorrect")
                    else:
                        # Update password
                        hashed_new = hashlib.sha256(new_password.encode()).hexdigest()
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_new, st.session_state.user_id))
                        conn.commit()
                        conn.close()
                        
                        st.success("Password changed successfully")


def notifications_page():
    st.title("Notifications")
    
    # Get notifications
    notifications = get_notifications(st.session_state.user_id)
    
    if not notifications:
        st.info("You have no notifications.")
    else:
        # Display each notification
        for notification in notifications:
            with st.container():
                col1, col2 = st.columns([10, 1])
                
                with col1:
                    st.markdown(f"**{notification['title']}**")
                    st.write(notification['message'])
                    st.text(f"Received: {notification['timestamp']}")
                
                with col2:
                    if not notification.get('read', False):
                        if st.button("Mark as Read", key=f"read_{notification['id']}"):
                            mark_notification_as_read(notification['id'])
                            st.experimental_rerun()
                
                st.divider()
        
        # Add a button to mark all as read
        if st.button("Mark All as Read"):
            mark_all_notifications_as_read(st.session_state.user_id)
            st.success("All notifications marked as read.")
            st.experimental_rerun()

    
