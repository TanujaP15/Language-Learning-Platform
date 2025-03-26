import sqlite3
import os

# Delete old corrupted database file (if needed)
if os.path.exists("database.db"):
    os.remove("database.db")  # Delete the old database to apply schema changes

# Initialize a new database
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Create users table with hearts and last_heart_time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            hearts INTEGER DEFAULT 5,
            last_heart_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create progress table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            user_email TEXT NOT NULL,
            lesson_id INTEGER NOT NULL,
            completed BOOLEAN DEFAULT 0,
            PRIMARY KEY (user_email, lesson_id),
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    """)

    conn.commit()
    conn.close()

# Call the function to create the database
init_db()

print("✅ Database initialized successfully with hearts and lesson tracking!")
