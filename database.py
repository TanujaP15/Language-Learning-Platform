# database.py
import sqlite3
import os
from datetime import datetime, date # Import date

# Delete old database file if needed (Use with caution during development)
# if os.path.exists("database.db"):
#     print("⚠️ Removing existing database.db for schema update...")
#     os.remove("database.db")

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # --- Users Table ---
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_exists = cursor.fetchone()

    if not users_exists:
         print("📌 Creating new 'users' table...")
         cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                hearts INTEGER DEFAULT 5,
                last_heart_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                xp INTEGER DEFAULT 0,
                gems INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                last_streak_update DATE,  -- Store only the date
                daily_progress INTEGER DEFAULT 0,
                daily_goal INTEGER DEFAULT 10, -- Example goal
                last_daily_reset DATE       -- Store only the date
            )
         """)
    else:
         print(" Modyfing users table ")
         # Add columns if they don't exist (safer than dropping table)
         cursor.execute("PRAGMA table_info(users)")
         columns = [column[1] for column in cursor.fetchall()]

         if "xp" not in columns:
             cursor.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
         if "gems" not in columns:
             cursor.execute("ALTER TABLE users ADD COLUMN gems INTEGER DEFAULT 0")
         if "streak" not in columns:
             cursor.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
         if "last_streak_update" not in columns:
             # Use DATE type for simpler daily comparisons
             cursor.execute("ALTER TABLE users ADD COLUMN last_streak_update DATE")
         if "daily_progress" not in columns:
             cursor.execute("ALTER TABLE users ADD COLUMN daily_progress INTEGER DEFAULT 0")
         if "daily_goal" not in columns:
              cursor.execute("ALTER TABLE users ADD COLUMN daily_goal INTEGER DEFAULT 10") # Example goal
         if "last_daily_reset" not in columns:
             # Use DATE type for simpler daily comparisons
             cursor.execute("ALTER TABLE users ADD COLUMN last_daily_reset DATE")
         # Add hearts/last_heart_time if somehow missing from older schema
         if "hearts" not in columns:
             cursor.execute("ALTER TABLE users ADD COLUMN hearts INTEGER DEFAULT 5")
         if "last_heart_time" not in columns:
             cursor.execute("ALTER TABLE users ADD COLUMN last_heart_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    # --- Progress Table (Your existing logic is good) ---
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='progress'")
    progress_exists = cursor.fetchone()

    if progress_exists:
        cursor.execute("PRAGMA table_info(progress)")
        columns = [column[1] for column in cursor.fetchall()]

        if "language" not in columns:
            print("⚠️ Migrating 'progress' table to add 'language' column...")
            try:
                # Check if old_progress exists before trying to drop/rename
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='old_progress'")
                if cursor.fetchone():
                    cursor.execute("DROP TABLE old_progress") # Drop if leftover from failed migration

                cursor.execute("ALTER TABLE progress RENAME TO old_progress")
                cursor.execute("""
                    CREATE TABLE progress (
                        user_email TEXT NOT NULL,
                        lesson_id INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        completed BOOLEAN DEFAULT 0,
                        PRIMARY KEY (user_email, lesson_id, language),
                        FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE
                    )
                """)
                # Migrate old data (handle potential errors if old_progress doesn't exist)
                cursor.execute("INSERT INTO progress (user_email, lesson_id, language, completed) SELECT user_email, lesson_id, 'Spanish', completed FROM old_progress")
                cursor.execute("DROP TABLE old_progress")
                print("✅ Migration successful.")
            except sqlite3.Error as e:
                print(f"❌ Error during progress table migration: {e}")
                # Consider how to handle migration failure (e.g., restore backup, manual intervention)

    else:
        print("📌 Creating new 'progress' table...")
        cursor.execute("""
            CREATE TABLE progress (
                user_email TEXT NOT NULL,
                lesson_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                PRIMARY KEY (user_email, lesson_id, language),
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE
            )
        """)

    conn.commit()
    conn.close()

# Call the function to create/update the database
init_db()
print("✅ Database initialized/updated successfully!")