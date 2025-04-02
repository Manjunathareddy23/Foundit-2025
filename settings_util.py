def update_user_settings(user_id, settings):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update theme in users table
        if 'theme' in settings:
            cursor.execute("UPDATE users SET theme = ? WHERE id = ?", (settings['theme'], user_id))
            # Update session state
            st.session_state.theme = settings['theme']
            # Remove from settings dict to avoid duplication
            theme = settings.pop('theme', None)
        
        # Update other settings
        for key, value in settings.items():
            # Check if setting already exists
            cursor.execute("SELECT id FROM settings WHERE user_id = ? AND setting_key = ?", (user_id, key))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("UPDATE settings SET setting_value = ? WHERE user_id = ? AND setting_key = ?", 
                              (value, user_id, key))
            else:
                setting_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO settings (id, user_id, setting_key, setting_value) VALUES (?, ?, ?, ?)",
                              (setting_id, user_id, key, value))
        
        conn.commit()
        conn.close()
        return True, "Settings updated successfully"
    except Exception as e:
        return False, f"Error updating settings: {str(e)}"
