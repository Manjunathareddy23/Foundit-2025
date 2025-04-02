Here's the complete, fixed Streamlit application for an Advanced Task Manager with Tailwind CSS styling:

```python
# app.py - Main Streamlit application file

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
def apply_custom_css():
    # Load the Tailwind-inspired CSS
    st.markdown("""
    <style>
    /* Base styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary-color: #3b82f6;
        --primary-color-hover: #2563eb;
        --secondary-color: #64748b;
        --accent-color: #10b981;
        --warning-color: #f59e0b;
        --danger-color: #ef4444;
        --success-color: #22c55e;
        --dark-bg: #1e293b;
        --dark-surface: #334155;
        --dark-text: #f8fafc;
        --light-bg: #f1f5f9;
        --light-surface: #ffffff;
        --light-text: #0f172a;
    }
    
    .stApp {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: var(--light-surface);
        border-right: 1px solid #e2e8f0;
    }
    
    .dark section[data-testid="stSidebar"] {
        background-color: var(--dark-surface);
        border-right: 1px solid #475569;
    }
    
    /* Main area styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header styling */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600 !important;
        color: var(--light-text);
    }
    
    .dark h1, .dark h2, .dark h3, .dark h4, .dark h5, .dark h6 {
        color: var(--dark-text);
    }
    
    h1 {
        font-size: 2rem !important;
        margin-bottom: 1.5rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
        margin-bottom: 1.25rem !important;
    }
    
    h3 {
        font-size: 1.25rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Button styling */
    button[kind="primary"] {
        background-color: var(--primary-color) !important;
        border-radius: 0.375rem !important;
        border: none !important;
        color: white !important;
        font-weight: 500 !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    button[kind="primary"]:hover {
        background-color: var(--primary-color-hover) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    }
    
    button[kind="secondary"] {
        background-color: var(--secondary-color) !important;
        border-radius: 0.375rem !important;
        border: none !important;
        color: white !important;
        font-weight: 500 !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    button[kind="secondary"]:hover {
        opacity: 0.9 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0
