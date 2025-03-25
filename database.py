import sqlite3

# Delete old corrupted database file (if needed)
try:
    conn = sqlite3.connect("database.db")
    conn.close()
except sqlite3.DatabaseError:
    import os
    os.remove("database.db")

# Initialize a new database
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Call the function to create the database
init_db()

print("✅ Database initialized successfully!")
