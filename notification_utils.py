import streamlit as st
import uuid
from datetime import datetime
from db_utils import get_db_connection

def create_notification(user_id, task_id, message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        notification_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        INSERT INTO notifications (id, user_id, task_id, message, created_at)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            notification_id,
            user_id,
            task_id,
            message,
            now
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating notification: {str(e)}")
        return False

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
