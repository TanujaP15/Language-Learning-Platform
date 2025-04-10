# database.py
import sqlite3
import os
from datetime import datetime, date # Import date

ALL_ACHIEVEMENTS = {
    'STREAK_3': { 'name': 'On Fire!', 'description': 'Maintain a 3-day streak.', 'icon': 'fas fa-fire', 'criteria_type': 'streak', 'criteria_value': 3, 'reward_gems': 10, 'reward_xp': 20 },
    'STREAK_7': { 'name': 'Week Streak', 'description': 'Maintain a 7-day streak.', 'icon': 'fas fa-calendar-week', 'criteria_type': 'streak', 'criteria_value': 7, 'reward_gems': 25, 'reward_xp': 50 },
    'LEVEL_5':  { 'name': 'Level 5 Reached', 'description': 'Reach Level 5.', 'icon': 'fas fa-star', 'criteria_type': 'level', 'criteria_value': 5, 'reward_gems': 15, 'reward_xp': 30 },
    'LESSONS_1': { 'name': 'First Steps', 'description': 'Complete your first lesson.', 'icon': 'fas fa-shoe-prints', 'criteria_type': 'lessons_total', 'criteria_value': 1, 'reward_gems': 5, 'reward_xp': 10 },
    'LESSONS_10':{ 'name': 'Getting Started', 'description': 'Complete 10 lessons (total).', 'icon': 'fas fa-seedling', 'criteria_type': 'lessons_total', 'criteria_value': 10, 'reward_gems': 20, 'reward_xp': 40 },
}


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # --- Users Table ---
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
                gems INTEGER DEFAULT 50, -- <<< CHANGED DEFAULT TO 50
                streak INTEGER DEFAULT 0,
                last_streak_update DATE,
                daily_progress INTEGER DEFAULT 0,
                daily_goal INTEGER DEFAULT 10,
                last_daily_reset DATE,
                join_date DATE DEFAULT CURRENT_DATE
            )
         """)
    else:
         print(" Checking/Modifying existing 'users' table...")
         cursor.execute("PRAGMA table_info(users)")
         columns = [column[1] for column in cursor.fetchall()]

         # Add columns if they don't exist
         if "xp" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
         if "gems" not in columns:
              print("    -> Adding 'gems' column with DEFAULT 50...")
              cursor.execute("ALTER TABLE users ADD COLUMN gems INTEGER DEFAULT 50") # <<< ADDED DEFAULT HERE TOO
         if "streak" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
         if "last_streak_update" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN last_streak_update DATE")
         if "daily_progress" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN daily_progress INTEGER DEFAULT 0")
         if "daily_goal" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN daily_goal INTEGER DEFAULT 10")
         if "last_daily_reset" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN last_daily_reset DATE")
         if "hearts" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN hearts INTEGER DEFAULT 5")
         if "last_heart_time" not in columns: cursor.execute("ALTER TABLE users ADD COLUMN last_heart_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
         if "join_date" not in columns:
             print("    -> Adding 'join_date' column...")
             cursor.execute("ALTER TABLE users ADD COLUMN join_date DATE DEFAULT CURRENT_DATE")

    # --- Progress Table ---
    # ... (keep existing progress table logic) ...
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='progress'")
    progress_exists = cursor.fetchone()

    if progress_exists:
        cursor.execute("PRAGMA table_info(progress)")
        columns = [column[1] for column in cursor.fetchall()]

        if "language" not in columns:
            print("⚠️ Migrating 'progress' table to add 'language' column...")
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='old_progress'")
                if cursor.fetchone(): cursor.execute("DROP TABLE old_progress")
                cursor.execute("ALTER TABLE progress RENAME TO old_progress")
                cursor.execute("""
                    CREATE TABLE progress ( /* ... schema ... */ )
                """) # Keep schema as before
                cursor.execute("INSERT INTO progress (user_email, lesson_id, language, completed) SELECT user_email, lesson_id, 'Spanish', completed FROM old_progress")
                cursor.execute("DROP TABLE old_progress")
                print("✅ Migration successful.")
            except sqlite3.Error as e: print(f"❌ Error during progress table migration: {e}")
    else:
        print("📌 Creating new 'progress' table...")
        cursor.execute("""
            CREATE TABLE progress (
                user_email TEXT NOT NULL,
                lesson_id INTEGER NOT NULL,
                language TEXT NOT NULL,          -- Include language from the start
                completed BOOLEAN DEFAULT 0,
                PRIMARY KEY (user_email, lesson_id, language), -- Composite primary key
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE
            )
        """) # Keep schema as before


    # --- Achievements Tables ---
    print(" Checking/Creating 'achievements' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            achievement_key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT,
            reward_xp INTEGER DEFAULT 0,
            reward_gems INTEGER DEFAULT 0,
            criteria_type TEXT NOT NULL,
            criteria_value INTEGER NOT NULL
        )
    """)
    print(" Populating 'achievements' table...")
    added_count = 0
    for key, ach_data in ALL_ACHIEVEMENTS.items():
        try:
            cursor.execute(
                """INSERT INTO achievements (achievement_key, name, description, icon, reward_xp, reward_gems, criteria_type, criteria_value)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(achievement_key) DO UPDATE SET
                       name=excluded.name, description=excluded.description, icon=excluded.icon,
                       reward_xp=excluded.reward_xp, reward_gems=excluded.reward_gems,
                       criteria_type=excluded.criteria_type, criteria_value=excluded.criteria_value
                """, # Use UPSERT (SQLite 3.24+) to insert or update
                (key, ach_data['name'], ach_data['description'], ach_data.get('icon'),
                 ach_data.get('reward_xp', 0), ach_data.get('reward_gems', 0),
                 ach_data['criteria_type'], ach_data['criteria_value'])
            )
            if cursor.rowcount > 0: # Check if a row was actually inserted/updated
                added_count += 1
        except sqlite3.Error as e:
             # Fallback for older SQLite without UPSERT support
            if "syntax error" in str(e) and "ON CONFLICT" in str(e).upper():
                try:
                     # Try simple INSERT OR IGNORE first
                    cursor.execute(
                        "INSERT OR IGNORE INTO achievements VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (key, ach_data['name'], ach_data['description'], ach_data.get('icon'),
                         ach_data.get('reward_xp', 0), ach_data.get('reward_gems', 0),
                         ach_data['criteria_type'], ach_data['criteria_value'])
                    )
                    # Could add separate UPDATE logic here if needed, but IGNORE is simpler
                except sqlite3.Error as ie:
                    print(f" Error inserting/ignoring achievement {key}: {ie}")
            else:
                 print(f" Error populating achievement {key}: {e}")

    if added_count > 0: print(f" Added/Updated {added_count} achievements.")

    print(" Checking/Creating 'user_achievements' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_email TEXT NOT NULL,
            achievement_key TEXT NOT NULL,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_email, achievement_key),
            FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE,
            FOREIGN KEY (achievement_key) REFERENCES achievements(achievement_key) ON DELETE CASCADE
        )
    """)
    # --- END Achievements Tables ---

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("✅ Database schema initialization/update complete!")