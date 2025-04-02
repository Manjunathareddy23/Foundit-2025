import streamlit as st
import hashlib
import uuid
from datetime import datetime
from db_utils import get_db_connection

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
