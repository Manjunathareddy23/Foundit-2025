import streamlit as st
from datetime import datetime
from streamlit_option_menu import option_menu

# Importing functions from other modules
from database import init_db
from auth import login_user, logout_user, register_user
from task import add_task, get_tasks, update_task, delete_task, get_task_statistics
from notification import get_notifications, mark_notification_as_read  # Fixed import statement
from backup import create_backup, restore_from_backup
from export import export_tasks_to_csv, export_tasks_to_json
from settings import get_user_settings, update_user_settings
from pages import (
    login_page,
    dashboard_page,
    add_task_page,
    view_tasks_page,
    statistics_page,
    settings_page,
    notifications_page
)

# Initialize database
init_db()

# Main application logic
def main():
    st.set_page_config(page_title="Advanced Task Manager", layout="wide")
    
    # Sidebar menu
    with st.sidebar:
        selected = option_menu(
            "Menu",
            ["Dashboard", "View Tasks", "Add Task", "Statistics", "Settings", "Notifications", "Logout"],
            icons=["house", "list-task", "plus-circle", "bar-chart-line", "gear", "bell", "box-arrow-right"],
            menu_icon="cast",
            default_index=0
        )
    
    # Page routing
    if selected == "Dashboard":
        dashboard_page()
    elif selected == "View Tasks":
        view_tasks_page()
    elif selected == "Add Task":
        add_task_page()
    elif selected == "Statistics":
        statistics_page()
    elif selected == "Settings":
        settings_page()
    elif selected == "Notifications":
        notifications_page()
    elif selected == "Logout":
        logout_user()
        st.sidebar.success("You have been logged out.")
        st.experimental_rerun()

if __name__ == "__main__":
    main()
