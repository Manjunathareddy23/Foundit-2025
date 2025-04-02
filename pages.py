import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from auth import login_user, logout_user, register_user
from task import add_task, get_tasks, update_task, delete_task, get_task_statistics
from notification import get_notifications, mark_notification_as_read, mark_all_notifications_as_read
from backup import create_backup, restore_from_backup
from export import export_tasks_to_csv, export_tasks_to_json
from settings import get_user_settings, update_user_settings

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
                if not new_username or new_password:
                    st.error("Username and password are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(new_username, new_password, new_email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

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
                    st.write(f"**Due Date:** {selected_task['
