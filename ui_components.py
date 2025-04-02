import streamlit as st
from auth_utils import login_user, register_user

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
                if not new_username or not new_password:
                    st.error("Username and password are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(new_username, new_password, new_email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
