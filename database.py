import sqlite3
import os

# Delete old database file if needed
if os.path.exists("database.db"):
    os.remove("database.db")  # Delete the old database to apply schema changes

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

    # Check if progress table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='progress'")
    progress_exists = cursor.fetchone()

    if progress_exists:
        # Check if language column already exists
        cursor.execute("PRAGMA table_info(progress)")
        columns = [column[1] for column in cursor.fetchall()]

        if "language" not in columns:
            print("⚠️ Migrating database to add 'language' column...")

            # Rename old progress table
            cursor.execute("ALTER TABLE progress RENAME TO old_progress")

            # Create new progress table with language column
            cursor.execute("""
                CREATE TABLE progress (
                    user_email TEXT NOT NULL,
                    lesson_id INTEGER NOT NULL,
                    language TEXT NOT NULL,  -- New column
                    completed BOOLEAN DEFAULT 0,
                    PRIMARY KEY (user_email, lesson_id, language),
                    FOREIGN KEY (user_email) REFERENCES users(email)
                )
            """)

            # Migrate old data (assuming Spanish as default)
            cursor.execute("""
                INSERT INTO progress (user_email, lesson_id, language, completed)
                SELECT user_email, lesson_id, 'Spanish', completed FROM old_progress
            """)

            # Drop old table
            cursor.execute("DROP TABLE old_progress")

    else:
        print("📌 Creating new 'progress' table...")

        # Create progress table with language column
        cursor.execute("""
            CREATE TABLE progress (
                user_email TEXT NOT NULL,
                lesson_id INTEGER NOT NULL,
                language TEXT NOT NULL,  -- New column
                completed BOOLEAN DEFAULT 0,
                PRIMARY KEY (user_email, lesson_id, language),
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        """)

    conn.commit()
    conn.close()

# Call the function to create/update the database
init_db()

print("✅ Database initialized successfully with hearts and per-language lesson tracking!")
