import sqlite3
import uuid
import hashlib
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('task_manager.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        created_at TEXT NOT NULL,
        last_login TEXT,
        theme TEXT DEFAULT 'light'
    )
    ''')
    
    # Create tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        due_date TEXT,
        created_date TEXT NOT NULL,
        modified_date TEXT NOT NULL,
        assigned_by TEXT,
        assigned_to TEXT NOT NULL,
        tags TEXT,
        recurring TEXT,
        recurrence_end_date TEXT,
        reminder TEXT,
        time_estimate INTEGER,
        time_spent INTEGER DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (assigned_to) REFERENCES users (id)
    )
    ''')
    
    # Create notifications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        task_id TEXT,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        read INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    ''')
    
    # Create settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        setting_key TEXT NOT NULL,
        setting_value TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, setting_key)
    )
    ''')
    
    # Create backup table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS backups (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        created_at TEXT NOT NULL,
        size INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create default admin user if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_id = str(uuid.uuid4())
        hashed_password = hashlib.sha256("admin".encode()).hexdigest()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (id, username, password, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (admin_id, "admin", hashed_password, "admin@example.com", now)
        )
    
    conn.commit()
    conn.close()
