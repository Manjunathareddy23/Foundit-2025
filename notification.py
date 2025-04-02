import uuid
from datetime import datetime
import streamlit as st
from database import get_db_connection

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
        
        return notifications  # Ensure you return the result

    except Exception as e:
        st.error(f"Error fetching notifications: {e}")  # Add an except block to catch errors
        return []

    finally:
        conn.close()  # Always close the connection

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

def mark_all_notifications_as_read(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error marking all notifications as read: {str(e)}")
        return False
