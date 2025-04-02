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
