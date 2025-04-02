import streamlit as st
from streamlit_option_menu import option_menu
import os
from datetime import datetime

# Import modules
from db_utils import init_db
from auth_utils import login_user, logout_user
from ui_components import login_page
from dashboard import dashboard_page
from task_pages import add_task_page, view_tasks_page
from statistics_page import statistics_page
from settings_page import settings_page
from notifications_page import notifications_page
from notification_utils import get_notifications

# Function to load and apply CSS
def load_css(file_name):
    with open(file_name, 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Main application
def main():
    # Initialize session state variables if they don't exist
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"
    
    # Initialize database
    init_db()
    
    # Check if user is logged in
    if not st.session_state.logged_in:
        login_page()
    else:
        # Create sidebar navigation
        with st.sidebar:
            selected = option_menu(
                "Task Manager", 
                ["Dashboard", "Add Task", "View Tasks", "Statistics", "Settings", "Notifications"],
                icons=['house', 'plus-circle', 'list-task', 'graph-up', 'gear', 'bell'],
                menu_icon="check-circle",
                default_index=0,
            )
            
            # Get unread notification count
            unread_notifications = get_notifications(st.session_state.user_id, unread_only=True)
            notification_count = len(unread_notifications)
            
            # Display notification badge if there are unread notifications
            if notification_count > 0:
                st.sidebar.markdown(f"<span class='notification-badge'>{notification_count}</span>", unsafe_allow_html=True)
            
            # Logout button
            if st.button("Logout"):
                logout_user()
                st.experimental_rerun()
        
        # Determine which page to show based on navigation or session state
        if 'current_page' in st.session_state:
            if st.session_state.current_page == "add_task":
                add_task_page()
                st.session_state.current_page = None
            elif st.session_state.current_page == "view_tasks":
                view_tasks_page()
                st.session_state.current_page = None
            elif st.session_state.current_page == "task_details":
                view_tasks_page()
                st.session_state.current_page = None
            else:
                if selected == "Dashboard":
                    dashboard_page()
                elif selected == "Add Task":
                    add_task_page()
                elif selected == "View Tasks":
                    view_tasks_page()
                elif selected == "Statistics":
                    statistics_page()
                elif selected == "Settings":
                    settings_page()
                elif selected == "Notifications":
                    notifications_page()
        else:
            if selected == "Dashboard":
                dashboard_page()
            elif selected == "Add Task":
                add_task_page()
            elif selected == "View Tasks":
                view_tasks_page()
            elif selected == "Statistics":
                statistics_page()
            elif selected == "Settings":
                settings_page()
            elif selected == "Notifications":
                notifications_page()

if __name__ == "__main__":
    # Set page config
    st.set_page_config(
        page_title="Advanced Task Manager",
        page_icon="✓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load CSS if it exists
    if os.path.exists("style.css"):
        load_css("style.css")
    
    main()
