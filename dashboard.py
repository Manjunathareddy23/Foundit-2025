import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from task_utils import get_tasks, update_task
from statistics_utils import get_task_statistics
from notification_utils import get_notifications, mark_notification_as_read

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
