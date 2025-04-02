import json
import uuid
from datetime import datetime
from database import get_db_connection

def create_backup(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all tasks for the user
        cursor.execute("""
        SELECT * FROM tasks 
        WHERE assigned_to = ? OR assigned_by = ?
        """, (user_id, user_id))
        
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # Create backup file
        backup_data = {
            'tasks': tasks,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': user_id
        }
        
        backup_json = json.dumps(backup_data, indent=2)
        
        # Save backup info to database
        backup_id = str(uuid.uuid4())
        filename = f"backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
        INSERT INTO backups (id, user_id, filename, created_at, size)
        VALUES (?, ?, ?, ?, ?)
        """, (
            backup_id,
            user_id,
            filename,
            now,
            len(backup_json)
        ))
        
        conn.commit()
        conn.close()
        
        return True, backup_json, filename
    except Exception as e:
        return False, f"Error creating backup: {str(e)}", None

def restore_from_backup(backup_data, user_id):
    try:
        # Parse backup data
        backup = json.loads(backup_data)
        
        # Validate backup format
        if 'tasks' not in backup:
            return False, "Invalid backup format"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Process each task in the backup
        for task in backup['tasks']:
            # Check if task already exists
            cursor.execute("SELECT id FROM tasks WHERE id = ?", (task['id'],))
            existing_task = cursor.fetchone()
            
            if existing_task:
                # Update existing task
                task_id = task.pop('id')
                set_clause = ", ".join([f"{key} = ?" for key in task.keys()])
                query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
                cursor.execute(query, list(task.values()) + [task_id])
            else:
                # Insert new task
                placeholders = ", ".join(["?"] * len(task))
                columns = ", ".join(task.keys())
                query = f"INSERT INTO tasks ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(task.values()))
        
        # Commit transaction
        conn.commit()
        conn.close()
        
        return True, f"Successfully restored {len(backup['tasks'])} tasks"
    except Exception as e:
        # Rollback in case of error
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False, f"Error restoring backup: {str(e)}"
