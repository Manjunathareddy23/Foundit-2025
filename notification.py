import uuid
from datetime import datetime
import streamlit as st
from database import get_db_connection

def get_notifications(user_id, unread_only=False):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM notifications WHERE user_id = ?"
        params
