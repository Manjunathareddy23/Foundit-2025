import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_utils import get_db_connection
from task_utils import add_task, get_tasks, update_task, delete_task
from export_utils import export_tasks_to_csv, export_tasks_to_json

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
