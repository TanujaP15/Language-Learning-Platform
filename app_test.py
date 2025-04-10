import sqlite3
import json
import os
import math # Needed for ceil, floor
import hashlib # For profile color generation
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, timedelta, date # Import date

load_dotenv()

HEART_REGEN_TIME_SECONDS = 120 # Example: 2 minutes (120 seconds) per heart
MAX_HEARTS = 5
XP_LEVELS = [0, 50, 120, 250, 500, 1000, 2000] # XP required to *reach* the next level (level 0 needs 0, level 1 needs 50, etc.)
LEADERBOARD_LIMIT = 30 # How many users to show on the leaderboard
HEART_REFILL_COST_GEMS = 50
LESSON_GEM_REWARD = 1       # Gems awarded per lesson completion
LEVEL_UP_GEM_REWARD = 50  
ALL_ACHIEVEMENTS = {
    # Key: Unique Identifier
    # Value: Dictionary with achievement details
    'STREAK_3': {
        'name': 'On Fire!', 'description': 'Maintain a 3-day streak.', 'icon': 'fas fa-fire',
        'criteria_type': 'streak', 'criteria_value': 3,
        'reward_gems': 10, 'reward_xp': 20
    },
    'STREAK_7': {
        'name': 'Week Streak', 'description': 'Maintain a 7-day streak.', 'icon': 'fas fa-calendar-week',
        'criteria_type': 'streak', 'criteria_value': 7,
        'reward_gems': 25, 'reward_xp': 50
    },
    'LEVEL_5': {
        'name': 'Level 5 Reached', 'description': 'Reach Level 5.', 'icon': 'fas fa-star',
        'criteria_type': 'level', 'criteria_value': 5,
        'reward_gems': 15, 'reward_xp': 30
    },
    'LESSONS_1': {
        'name': 'First Steps', 'description': 'Complete your first lesson.', 'icon': 'fas fa-shoe-prints',
        'criteria_type': 'lessons_total', 'criteria_value': 1,
        'reward_gems': 5, 'reward_xp': 10
    },
    'LESSONS_10':{
        'name': 'Getting Started', 'description': 'Complete 10 lessons (total).', 'icon': 'fas fa-seedling',
        'criteria_type': 'lessons_total', 'criteria_value': 10,
        'reward_gems': 20, 'reward_xp': 40
    },
    # Add more achievements:
}

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "a_default_secret_key_for_dev") # Provide default for dev

# Load lessons.json
try:
    with open("lessons.json", "r", encoding="utf-8") as file:
        lessons_data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading lessons.json: {e}")
    lessons_data = {} # Default to empty if error

# --- Database Setup ---
DATABASE = "database.db"

# Make sure the database is initialized by running database.py first
# Or include the init_db logic here if preferred.

# Database Connection Helper
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON") # Ensure foreign key constraints are enforced
    return conn

# Available languages (Consider deriving from lessons_data keys)
AVAILABLE_LANGUAGES = list(set(k.split('-')[0] for k in lessons_data.keys())) or ["Spanish", "French", "German", "Japanese"] # Derive from keys or fallback

# --- Helper Functions ---
def get_user_data(email):
    """Fetches all relevant user data."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user

def update_hearts(user_email):
    """Checks and updates regenerated hearts, returns current hearts and time left."""
    conn = get_db_connection()
    user = conn.execute("SELECT hearts, last_heart_time FROM users WHERE email = ?", (user_email,)).fetchone()

    if not user:
        conn.close()
        return None, None # Indicate user not found

    current_hearts = user["hearts"]
    time_left_seconds = 0
    updated_last_heart_time_str = user["last_heart_time"] # Keep original if no change

    if current_hearts < MAX_HEARTS:
        try:
            # Ensure last_heart_time is parsed correctly, handle potential None or format issues
            last_heart_time_str = user["last_heart_time"]
            if last_heart_time_str:
                 # Adjust parsing based on how TIMESTAMP DEFAULT CURRENT_TIMESTAMP stores it
                 # It might be 'YYYY-MM-DD HH:MM:SS' or include fractions of seconds
                 try:
                      last_heart_time = datetime.strptime(last_heart_time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                 except ValueError:
                      # Fallback or log error if format is unexpected
                      print(f"Warning: Could not parse last_heart_time '{last_heart_time_str}' for user {user_email}. Using current time.")
                      last_heart_time = datetime.now() # Or handle differently

            else: # If null for some reason, treat as if regeneration starts now
                 last_heart_time = datetime.now()
                 updated_last_heart_time_str = last_heart_time.strftime("%Y-%m-%d %H:%M:%S")


            now = datetime.now()
            time_diff_seconds = (now - last_heart_time).total_seconds()

            if time_diff_seconds >= HEART_REGEN_TIME_SECONDS:
                hearts_to_regen = math.floor(time_diff_seconds / HEART_REGEN_TIME_SECONDS)
                potential_new_hearts = current_hearts + hearts_to_regen
                actual_new_hearts = min(potential_new_hearts, MAX_HEARTS)
                gained_hearts = actual_new_hearts - current_hearts

                if gained_hearts > 0:
                    # Calculate the time when the *last* heart needed for regen was gained
                    seconds_for_gained_hearts = gained_hearts * HEART_REGEN_TIME_SECONDS
                    # Important: The new 'last_heart_time' should reflect the start of the timer for the *next* heart
                    # If we gained multiple hearts, the timer starts from when the last one was gained.
                    effective_last_regen_time = last_heart_time + timedelta(seconds=(hearts_to_regen * HEART_REGEN_TIME_SECONDS))

                    # Ensure effective time is not in the future if calculation is slightly off
                    effective_last_regen_time = min(effective_last_regen_time, now)

                    updated_last_heart_time_str = effective_last_regen_time.strftime("%Y-%m-%d %H:%M:%S")

                    conn.execute("UPDATE users SET hearts = ?, last_heart_time = ? WHERE email = ?",
                                 (actual_new_hearts, updated_last_heart_time_str, user_email))
                    conn.commit()
                    current_hearts = actual_new_hearts
                    print(f"User {user_email}: Regenerated {gained_hearts} hearts. New count: {current_hearts}. New last_heart_time: {updated_last_heart_time_str}")


            # Calculate time left for the *next* heart after potential regeneration
            if current_hearts < MAX_HEARTS:
                 # Use the potentially updated last_heart_time
                 last_time = datetime.strptime(updated_last_heart_time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                 time_since_last = (datetime.now() - last_time).total_seconds()
                 time_left_seconds = max(0, math.ceil(HEART_REGEN_TIME_SECONDS - time_since_last))

        except Exception as e:
            print(f"Error during heart regeneration for {user_email}: {e}")
            # Keep current_hearts and time_left_seconds as 0 in case of error

    conn.close()
    # print(f"User {user_email}: Hearts={current_hearts}, Time Left={time_left_seconds}s")
    return current_hearts, int(time_left_seconds)


def check_daily_reset_and_streak(user_email):
    """Handles daily progress reset and streak logic. Returns updated streak."""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT streak, last_streak_update, daily_progress, last_daily_reset FROM users WHERE email = ?",
        (user_email,)
    ).fetchone()

    if not user:
        conn.close()
        return 0 # Or raise error

    today = date.today()
    current_streak = user["streak"]
    updated_streak = current_streak # Assume no change initially
    needs_update = False

    # --- Daily Goal Reset ---
    last_reset_str = user["last_daily_reset"]
    last_reset_date = None
    if last_reset_str:
        try:
            last_reset_date = date.fromisoformat(last_reset_str)
        except ValueError:
             print(f"Warning: Could not parse last_daily_reset date '{last_reset_str}' for user {user_email}.")

    if last_reset_date is None or last_reset_date < today:
        print(f"User {user_email}: Resetting daily progress for {today}.")
        conn.execute("UPDATE users SET daily_progress = 0, last_daily_reset = ? WHERE email = ?",
                     (today.isoformat(), user_email))
        needs_update = True

    # --- Streak Check (only if daily reset happened or first login of day) ---
    last_streak_update_str = user["last_streak_update"]
    last_streak_date = None
    if last_streak_update_str:
         try:
             last_streak_date = date.fromisoformat(last_streak_update_str)
         except ValueError:
             print(f"Warning: Could not parse last_streak_update date '{last_streak_update_str}' for user {user_email}.")


    if last_streak_date is None:
         # No previous activity, streak remains 0 until first completion
         updated_streak = 0
    elif last_streak_date < (today - timedelta(days=1)):
         # Missed more than a day
         if current_streak > 0:
              print(f"User {user_email}: Streak reset from {current_streak} to 0.")
              updated_streak = 0
              # Update streak in DB immediately if it resets *before* activity
              conn.execute("UPDATE users SET streak = 0 WHERE email = ?", (user_email,))
              needs_update = True # Ensure commit happens
    # else: streak is maintained (either updated yesterday or will be updated today by complete_lesson)

    if needs_update:
        conn.commit()

    conn.close()
    return updated_streak # Return the potentially reset streak


def calculate_level_xp(current_xp):
    """Calculates level, XP percentage, and next level XP."""
    level = 0
    for i, threshold in enumerate(XP_LEVELS):
        if current_xp >= threshold:
            level = i + 1 # Level 1 is reached at XP_LEVELS[0], Level 2 at XP_LEVELS[1] etc.
        else:
            break # Found the current level range

    # Handle max level
    if level > len(XP_LEVELS):
        level = len(XP_LEVELS) # Max level reached
        current_level_xp = XP_LEVELS[-1]
        next_level_xp = current_level_xp # Or indicate max
        xp_percentage = 100
    elif level == 0: # Should only happen if XP < XP_LEVELS[0] (which is 0)
        current_level_xp = 0
        next_level_xp = XP_LEVELS[0] if XP_LEVELS else 0 # XP needed for Level 1
        xp_percentage = 0 if next_level_xp == 0 else (current_xp / next_level_xp) * 100
        level = 1 # Display as Level 1 even if 0 XP
    else:
        current_level_xp = XP_LEVELS[level-1] # XP required to start this level
        next_level_xp = XP_LEVELS[level]      # XP required to reach next level
        xp_in_level = current_xp - current_level_xp
        xp_needed_for_level = next_level_xp - current_level_xp
        xp_percentage = (xp_in_level / xp_needed_for_level) * 100 if xp_needed_for_level > 0 else 100

    return level, math.floor(xp_percentage), next_level_xp # Return calculated values

def get_profile_color(text):
    """Generates a simple hex color based on text input."""
    if not text: return "#cccccc" # Default grey
    hash_object = hashlib.md5(text.encode())
    hex_dig = hash_object.hexdigest()
    # Take first 6 hex digits for color, ensure reasonable brightness/saturation
    r = int(hex_dig[0:2], 16)
    g = int(hex_dig[2:4], 16)
    b = int(hex_dig[4:6], 16)
    # Simple adjustment: boost lower values, clamp high values
    r = min(200, max(50, r))
    g = min(200, max(50, g))
    b = min(200, max(50, b))
    return f"#{r:02x}{g:02x}{b:02x}"

def check_and_award_achievements(user_email, conn):
    """
    Checks user stats against defined achievements and awards if necessary.
    Requires an active database connection `conn` to be passed in for transaction control.
    Returns a list of newly earned achievement details (dictionaries).
    """
    newly_earned = []
    try:
        cursor = conn.cursor() # Use cursor from the passed connection

        # Get current user stats needed for checks
        user = cursor.execute("SELECT streak, xp, email FROM users WHERE email = ?", (user_email,)).fetchone()
        if not user:
             print(f"ERROR: User {user_email} not found during achievement check.")
             return [] # Return empty if user not found

        current_level, _, _ = calculate_level_xp(user['xp'])

        # Get total lessons completed (across all languages)
        total_lessons = cursor.execute(
            "SELECT COUNT(DISTINCT lesson_id || '-' || language) as count FROM progress WHERE user_email = ? AND completed = 1", (user_email,)
        ).fetchone()['count'] or 0

        # Get achievements already earned by the user
        earned_keys = {row['achievement_key'] for row in cursor.execute(
            "SELECT achievement_key FROM user_achievements WHERE user_email = ?", (user_email,)
        ).fetchall()}

        # Iterate through defined achievements
        for key, achievement in ALL_ACHIEVEMENTS.items():
            if key in earned_keys: continue # Skip if already earned

            criteria_met = False
            crit_type = achievement['criteria_type']
            crit_val = achievement['criteria_value']
            crit_extra = achievement.get('criteria_extra') # For language-specific criteria

            # --- Check Criteria ---
            if crit_type == 'streak' and user['streak'] >= crit_val:
                criteria_met = True
            elif crit_type == 'level' and current_level >= crit_val:
                criteria_met = True
            elif crit_type == 'lessons_total' and total_lessons >= crit_val:
                 criteria_met = True
            elif crit_type == 'lessons_language' and crit_extra:
                 # Need to query lessons completed for a specific language
                 lang_lessons = cursor.execute(
                     "SELECT COUNT(*) as count FROM progress WHERE user_email = ? AND language = ? AND completed = 1",
                     (user_email, crit_extra)
                 ).fetchone()['count'] or 0
                 if lang_lessons >= crit_val:
                      criteria_met = True
            # Add more elif blocks for other criteria_type values ('perfect_lesson', etc.)

            # --- Award if criteria met ---
            if criteria_met:
                print(f"User {user_email} potentially earned achievement: {key}")
                try:
                    # Insert into user_achievements
                    cursor.execute("INSERT INTO user_achievements (user_email, achievement_key) VALUES (?, ?)",
                                 (user_email, key))

                    # Award rewards (if any)
                    reward_xp = achievement.get('reward_xp', 0)
                    reward_gems = achievement.get('reward_gems', 0)
                    if reward_xp > 0 or reward_gems > 0:
                        cursor.execute("UPDATE users SET xp = xp + ?, gems = gems + ? WHERE email = ?",
                                     (reward_xp, reward_gems, user_email))
                        print(f"Awarded: {reward_xp} XP, {reward_gems} Gems for {key}")

                    # Use **achievement to create a copy and add key if needed
                    earned_detail = {**achievement, 'achievement_key': key}
                    newly_earned.append(earned_detail)
                    # Add to earned_keys immediately to prevent duplicate checks within this call
                    earned_keys.add(key)

                except sqlite3.IntegrityError:
                     # This can happen in rare race conditions or if logic has error. Ignore.
                     print(f"Info: User {user_email} likely already earned {key} (IntegrityError). Skipping.")
                except sqlite3.Error as award_err:
                     print(f"DATABASE ERROR awarding achievement {key} for {user_email}: {award_err}")
                     # Should we rollback everything? For now, just log and continue checking others.
                     # conn.rollback() # Careful with rollback inside loop if called from other transactions

        # No commit here - commit is handled by the calling function (e.g., complete_lesson_api)
        return newly_earned

    except sqlite3.Error as check_err:
        print(f"DATABASE ERROR checking achievements for {user_email}: {check_err}")
        return [] # Return empty on error
    except Exception as e:
         print(f"UNEXPECTED ERROR checking achievements for {user_email}: {e}")
         return []


# --- Routes ---

@app.route('/')
def home():
    if "user" in session:
        return redirect(url_for('dashboard')) # Redirect logged-in users to dashboard
    return render_template("index.html")

# Signup Route
# app.py

# ... (other code) ...

# app.py

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')

        if not fullname or not email or not password:
            flash("All fields are required!", "danger")
            return render_template("login.html", is_signup=True)

        hashed_password = generate_password_hash(password)
        today_iso = date.today().isoformat() # Format as YYYY-MM-DD

        try:
            conn = get_db_connection()
            # *** ADD join_date to INSERT statement and VALUES ***
            conn.execute(
                """INSERT INTO users
                   (fullname, email, password, last_streak_update, last_daily_reset, join_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (fullname, email, hashed_password, today_iso, today_iso, today_iso) # Pass today_iso for join_date
            )
            conn.commit()
            conn.close()

            session['user'] = email
            flash("Account created successfully! Welcome! 🎉", "success")
            return redirect(url_for('dashboard'))

        except sqlite3.IntegrityError:
            flash("Email already exists. Please log in.", "warning")
            return redirect(url_for('login'))
        except Exception as e:
             flash(f"An error occurred: {e}", "danger")
             return render_template("login.html", is_signup=True)

    return render_template("login.html", is_signup=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # ... (your existing POST logic) ...
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
             flash("Email and password are required.", "danger")
             # --- Pass is_signup=False when re-rendering ---
             return render_template("login.html", is_signup=False)

        user = get_user_data(email)

        if user and check_password_hash(user["password"], password):
            session['user'] = user["email"]
            check_daily_reset_and_streak(user["email"])
            flash("Login successful! Welcome back! ✅", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            # --- Pass is_signup=False when re-rendering ---
            return render_template("login.html", is_signup=False)

    # --- Handle GET request for /login ---
    return render_template("login.html", is_signup=False) # Pass flag to show login form

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# --- API Endpoints (for JS) ---

@app.route("/get_hearts")
def get_hearts_api(): # Renamed to avoid conflict if needed
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401 # Use 401 Unauthorized

    user_email = session["user"]
    hearts, time_left = update_hearts(user_email) # Use the helper

    if hearts is None:
         return jsonify({"error": "User not found"}), 404

    return jsonify({"hearts": hearts, "time_left": time_left})

@app.route("/lose_heart", methods=["POST"])
def lose_heart_api(): # Renamed
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_email = session["user"]
    conn = get_db_connection()
    user = conn.execute("SELECT hearts FROM users WHERE email = ?", (user_email,)).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    current_hearts = user["hearts"]
    new_hearts = current_hearts

    if current_hearts > 0:
        new_hearts = current_hearts - 1
        # Update last_heart_time when a heart is lost to reset the timer correctly
        conn.execute("UPDATE users SET hearts = ?, last_heart_time = ? WHERE email = ?",
                     (new_hearts, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_email))
        conn.commit()
        print(f"User {user_email}: Lost a heart. New count: {new_hearts}")


    conn.close()
    # Fetch time_left after losing heart
    _, time_left = update_hearts(user_email)
    return jsonify({"hearts": new_hearts, "time_left": time_left}) # Return time_left too

@app.route('/shop/buy_hearts', methods=['POST'])
def buy_hearts():
    """Allows users to spend gems to refill hearts."""
    if "user" not in session:
        return jsonify({"error": "Not authorized", "success": False}), 401

    user_email = session['user']

    conn = get_db_connection()
    try:
        # Use cursor for transaction control
        cursor = conn.cursor()
        user = cursor.execute("SELECT hearts, gems FROM users WHERE email = ?", (user_email,)).fetchone()

        if not user:
            return jsonify({"error": "User not found", "success": False}), 404

        current_hearts = user['hearts']
        current_gems = user['gems']

        if current_hearts >= MAX_HEARTS:
            return jsonify({"error": "Your hearts are already full!", "success": False, "code": "HEARTS_FULL"}), 400

        if current_gems < HEART_REFILL_COST_GEMS:
            return jsonify({"error": f"Not enough gems! You need {HEART_REFILL_COST_GEMS}.", "success": False, "code": "INSUFFICIENT_GEMS"}), 400

        # --- Perform Purchase ---
        new_gems = current_gems - HEART_REFILL_COST_GEMS
        new_hearts = MAX_HEARTS

        cursor.execute("UPDATE users SET gems = ?, hearts = ? WHERE email = ?",
                     (new_gems, new_hearts, user_email))
        conn.commit() # Commit the purchase

        print(f"User {user_email}: Bought hearts refill. Gems: {current_gems} -> {new_gems}, Hearts: {current_hearts} -> {new_hearts}")

        # Fetch updated time_left (will be 0 now)
        _, time_left = update_hearts(user_email)

        return jsonify({
            "success": True,
            "message": "Hearts refilled successfully!",
            "new_gems": new_gems,
            "new_hearts": new_hearts,
            "time_left": time_left
        })

    except sqlite3.Error as e:
        print(f"DATABASE ERROR during buy_hearts for {user_email}: {e}")
        conn.rollback()
        return jsonify({"error": "Database error during purchase.", "success": False}), 500
    finally:
        if conn: conn.close()

# app.py

# ... (keep all other imports, constants, functions like get_db_connection, etc.) ...

@app.route('/complete_lesson/<int:lesson_id>', methods=['POST'])
def complete_lesson_api(lesson_id):
    if "user" not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_email = session["user"]
    lang = request.args.get("lang", "Spanish")

    lang_key = f"{lang}-English"
    if lang_key not in lessons_data:
         return jsonify({"error": f"Invalid language specified: {lang}"}), 400

    lesson_info = next((l for l in lessons_data[lang_key] if l.get("lesson") == lesson_id), None)
    if not lesson_info:
         return jsonify({"error": "Lesson details not found"}), 404

    lesson_xp = lesson_info.get("xp", 10)
    lesson_gems = 1 # Award 1 gem per lesson

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # --- Mark lesson as completed FIRST ---
        # Use INSERT OR REPLACE to handle potential re-completion attempts safely
        cursor.execute("INSERT OR REPLACE INTO progress (user_email, lesson_id, language, completed) VALUES (?, ?, ?, 1)",
                       (user_email, lesson_id, lang))
        print(f"User {user_email}: Marked lesson {lesson_id} ({lang}) as completed in progress table.")

        # --- Get Current User Stats for Update ---
        user_stats = cursor.execute(
            "SELECT xp, daily_progress, daily_goal, streak, last_streak_update FROM users WHERE email = ?",
            (user_email,)
        ).fetchone()

        if not user_stats:
             print(f"CRITICAL ERROR: User {user_email} not found in users table during lesson completion update.")
             conn.rollback() # Rollback lesson completion mark
             return jsonify({"error": "User data not found during update"}), 500

        # --- START DETAILED STREAK DEBUG & REFINED LOGIC ---
        print(f"\n--- Streak Check Start (User: {user_email}, Lesson: {lesson_id}, Lang: {lang}) ---")
        print(f"DB Values Read -> Streak: {user_stats['streak']}, Last Update STR: '{user_stats['last_streak_update']}'") # Added quotes for clarity

        old_level, _, _ = calculate_level_xp(user_stats["xp"]) # Calculate level *before* adding XP
        new_xp = user_stats["xp"] + lesson_xp
        new_daily_progress = user_stats["daily_progress"] + lesson_xp
        current_streak = user_stats["streak"] # Streak value *before* this lesson's update
        updated_streak = current_streak # Default: assume no change initially

        today = date.today()
        last_streak_update_str = user_stats["last_streak_update"]
        last_streak_date = None

        if last_streak_update_str: # Check if the string exists and is not empty
            try:
                # Attempt to parse the date string (assuming YYYY-MM-DD)
                last_streak_date = date.fromisoformat(last_streak_update_str)
            except (ValueError, TypeError) as e: # Catch potential errors during parsing
                print(f"WARNING: Could not parse last_streak_update date '{last_streak_update_str}' for user {user_email}. Error: {e}")
                last_streak_date = None # Ensure it's None if parsing fails
        else:
             print(f"DB Info -> last_streak_update was NULL or empty.")

        print(f"Parsed/Compared -> Today: {today}, Last Update DATE: {last_streak_date}")

        # --- Refined Streak Logic ---
        if last_streak_date == today:
            # Activity already happened today.
            # If streak is 0, it means it was reset *today* before this activity,
            # so this is the *first* successful activity today, start streak at 1.
            # Otherwise, maintain the current streak.
            if current_streak == 0:
                print("Condition: First activity today after reset/signup? Starting streak at 1.")
                updated_streak = 1
            else:
                print("Condition: Already active today. Streak maintained.")
                updated_streak = current_streak # No change needed
        elif last_streak_date == (today - timedelta(days=1)):
            # Activity occurred yesterday, increment streak.
            print("Condition: Last update was yesterday. Incrementing streak.")
            updated_streak = current_streak + 1
        else:
            # Covers several cases:
            # 1. last_streak_date is None (first ever activity, or DB error).
            # 2. last_streak_date is older than yesterday (missed one or more days).
            # In both cases, the streak starts/restarts at 1.
            print(f"Condition: New day (last update: {last_streak_date}) or missed day(s) or first activity. Setting streak to 1.")
            updated_streak = 1
        # --- End Refined Streak Logic ---

        print(f"Result -> Current Streak (Before Update): {current_streak}, Calculated New Streak: {updated_streak}")
        # --- END DETAILED STREAK DEBUG ---


        # --- Check for Level Up AFTER calculating new XP ---
        new_level, _, _ = calculate_level_xp(new_xp)
        gems_from_level_up = 0
        if new_level > old_level:
            gems_from_level_up = 50 # Award 50 gems for leveling up (example)
            print(f"User {user_email} leveled up: {old_level} -> {new_level}! Awarding {gems_from_level_up} gems.")

        # --- Total Gems to Add ---
        total_gems_to_add = lesson_gems + gems_from_level_up

        # --- Execute the Database Update ---
        # Always update last_streak_update to today's date when activity occurs
        today_iso = today.isoformat()
        cursor.execute(
            """UPDATE users
               SET xp = ?, daily_progress = ?, streak = ?, last_streak_update = ?, gems = gems + ?
               WHERE email = ?""",
            (new_xp, new_daily_progress, updated_streak, today_iso, total_gems_to_add, user_email)
        )
        print(f"Executing DB Update -> New XP: {new_xp}, New Daily: {new_daily_progress}, New Streak: {updated_streak}, New Last Update: {today_iso}, Gems Added: {total_gems_to_add}")

        # --- Check for Achievements AFTER stats are updated ---
        newly_earned_achievements = check_and_award_achievements(user_email, conn)

        # --- Commit Transaction ---
        conn.commit()
        print("Transaction Committed.")

        # Fetch updated completed list for response
        cursor.execute("SELECT lesson_id FROM progress WHERE user_email = ? AND completed = 1 AND language = ?", (user_email, lang))
        completed_lessons = [row["lesson_id"] for row in cursor.fetchall()]

        # Prepare JSON response
        response_data = {
            "message": "Lesson completed!",
            "xp_earned": lesson_xp,
            "new_total_xp": new_xp,
            "new_streak": updated_streak, # Return the calculated streak
            "completed_lessons": completed_lessons,
            "new_achievements": newly_earned_achievements
        }
        return jsonify(response_data)

    # --- Error Handling ---
    except sqlite3.Error as db_err:
         print(f"DATABASE ERROR during lesson completion for {user_email}: {db_err}")
         conn.rollback() # Rollback changes on error
         return jsonify({"error": "Database error during lesson completion."}), 500
    except Exception as e:
         print(f"UNEXPECTED ERROR during lesson completion for {user_email}: {e}")
         conn.rollback() # Rollback changes on error
         return jsonify({"error": "An unexpected error occurred."}), 500
    finally:
        # Ensure connection is always closed
        if conn: conn.close()

# ... (rest of your app.py, including check_and_award_achievements, etc.) ...

# --- Page Routes ---

# app.py

# ... (keep all other imports and functions) ...

@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for('login'))

    user_email = session['user']

    # --- Pre-computation/Checks (Run for BOTH HTML and AJAX) ---
    try:
        check_daily_reset_and_streak(user_email)
        current_hearts, time_left_seconds = update_hearts(user_email)

        if current_hearts is None: # Handle case where user might have been deleted
            session.pop('user', None)
            flash("An error occurred fetching your data. Please log in again.", "danger")
            return redirect(url_for('login'))

        user = get_user_data(user_email)
        if not user:
            session.pop('user', None)
            flash("Could not retrieve user data.", "danger")
            return redirect(url_for('login'))

        # --- Language and Lessons (Needed for both) ---
        lang = request.args.get("lang", "Spanish")
        if lang not in AVAILABLE_LANGUAGES:
             lang = AVAILABLE_LANGUAGES[0] if AVAILABLE_LANGUAGES else "Spanish"

        lang_key = f"{lang}-English"
        lessons = lessons_data.get(lang_key, []) # Get lessons for the selected language

        # --- Get Completed Lessons for the *Selected* Language (Needed for both) ---
        conn = get_db_connection()
        completed_rows = conn.execute(
            "SELECT lesson_id FROM progress WHERE user_email = ? AND language = ? AND completed = 1",
            (user_email, lang) # Filter by language!
        ).fetchall()
        completed_lessons = [row["lesson_id"] for row in completed_rows]
        conn.close()

    except Exception as e:
         # Catch potential errors during data fetching before deciding HTML vs JSON
         print(f"ERROR fetching dashboard data for {user_email}: {e}")
         flash("An error occurred while loading dashboard data. Please try again.", "danger")
         # Determine if it was likely an AJAX request based on headers even during error
         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
              return jsonify({"error": "Failed to fetch dashboard data"}), 500
         else:
              # For HTML request, maybe redirect to login or show error page
              return redirect(url_for('login'))


    # --- Handle AJAX Request ---
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Ensure all required variables were successfully fetched above
            print(f"DEBUG: AJAX request for dashboard. Lang: {lang}, User: {user_email}") # Add Debug Print
            print(f"DEBUG: Data for JSON -> lessons count: {len(lessons)}, completed: {completed_lessons}, hearts: {current_hearts}, time_left: {time_left_seconds}")

            return jsonify({
                "lessons": lessons,               # Already filtered by lang
                "completed": completed_lessons,   # Already filtered by lang
                "hearts": current_hearts,
                "time_left": time_left_seconds
            })
        except Exception as e:
             # Catch error specifically during jsonify or if data is bad
             print(f"ERROR during jsonify in dashboard AJAX for {user_email}: {e}")
             # Send a specific JSON error response with 500 status
             return jsonify({"error": "Internal server error preparing data"}), 500

    # --- Render Full HTML Page (If not AJAX) ---
    try:
        level, xp_percentage, next_level_xp = calculate_level_xp(user["xp"])
        goal_percentage = (user["daily_progress"] / user["daily_goal"]) * 100 if user["daily_goal"] > 0 else 0
        goal_percentage = min(100, math.floor(goal_percentage))
        profile_color = get_profile_color(user["fullname"] or user["email"])

        return render_template(
            "dashboard.html",
            user=user["fullname"] or user["email"],
            hearts=current_hearts,
            time_left_if_regenerating=time_left_seconds,
            gems=user["gems"],
            streak=user["streak"], # Streak already checked/updated
            level=level,
            xp_percentage=xp_percentage,
            current_xp=user["xp"],
            next_level_xp=next_level_xp,
            daily_progress=user["daily_progress"],
            daily_goal=user["daily_goal"],
            goal_percentage=goal_percentage,
            profile_color=profile_color,
            lessons=lessons,               # Already filtered by lang
            language=lang,                 # Pass current language
            completed_lessons=completed_lessons, # Already filtered by lang
            available_languages=AVAILABLE_LANGUAGES
        )
    except Exception as e:
         # Catch potential errors during HTML rendering calculation
         print(f"ERROR rendering dashboard HTML for {user_email}: {e}")
         flash("An error occurred while displaying the dashboard.", "danger")
         return redirect(url_for('login'))

# ... (rest of app.py)



@app.route('/leaderboard')
def leaderboard():
    if "user" not in session:
        flash("Please log in to view the leaderboard.", "warning")
        return redirect(url_for('login'))

    user_email = session['user'] # Get current user's email for highlighting

    try:
        conn = get_db_connection()
        # Fetch top users ordered by XP, assign rank
        # Using RANK() window function for tie handling (requires SQLite 3.25+)
        query = """
            SELECT
                email,
                fullname,
                xp,
                RANK() OVER (ORDER BY xp DESC) as rank
            FROM users
            ORDER BY rank ASC, fullname ASC -- Sort by rank, then name for ties
            LIMIT ?
        """
        leaderboard_data = conn.execute(query, (LEADERBOARD_LIMIT,)).fetchall()
        conn.close()

        # Prepare data for template, adding profile color
        leaderboard_list = []
        for user_row in leaderboard_data:
            user_dict = dict(user_row) # Convert row object to dictionary
            # Generate profile color based on fullname or email
            display_name = user_dict['fullname'] or user_dict['email']
            user_dict['profile_color'] = get_profile_color(display_name)
            # Get first initial for icon
            user_dict['initial'] = (display_name[0] if display_name else '?').upper()
            leaderboard_list.append(user_dict)

        # Optional: Find current user's rank if not in top list (more complex query)
        # For now, we just highlight if they appear in the top LEADERBOARD_LIMIT

    except sqlite3.OperationalError as e:
         # Handle cases where RANK() might not be supported (older SQLite)
         if "window functions are not supported" in str(e).lower() or "no such function: rank" in str(e).lower():
              print("WARNING: RANK() window function not supported. Falling back to manual ranking (might be slow).")
              conn = get_db_connection()
              # Fetch without RANK()
              query_fallback = """
                    SELECT email, fullname, xp
                    FROM users
                    ORDER BY xp DESC, fullname ASC
                    LIMIT ?
              """
              leaderboard_data = conn.execute(query_fallback, (LEADERBOARD_LIMIT,)).fetchall()
              conn.close()
              # Manually add rank and color
              leaderboard_list = []
              rank_counter = 1
              for user_row in leaderboard_data:
                   user_dict = dict(user_row)
                   user_dict['rank'] = rank_counter # Simple rank, doesn't handle ties like RANK()
                   display_name = user_dict['fullname'] or user_dict['email']
                   user_dict['profile_color'] = get_profile_color(display_name)
                   user_dict['initial'] = (display_name[0] if display_name else '?').upper()
                   leaderboard_list.append(user_dict)
                   rank_counter += 1
         else:
              # Re-raise other operational errors
              print(f"ERROR fetching leaderboard data: {e}")
              flash("Could not load the leaderboard due to a database error.", "danger")
              return redirect(url_for('dashboard')) # Redirect on error

    except Exception as e:
        print(f"ERROR fetching leaderboard data: {e}")
        flash("An error occurred while loading the leaderboard.", "danger")
        return redirect(url_for('dashboard')) # Redirect on error


    return render_template(
        "leaderboard.html",
        leaderboard_data=leaderboard_list,
        current_user_email=user_email # Pass current user's email for highlighting
    )


@app.route('/lesson/<int:lesson_id>')
def lesson_page(lesson_id):
    if "user" not in session:
        flash("Please log in to access lessons.", "warning")
        return redirect(url_for('login'))

    user_email = session['user']
    lang = request.args.get("lang", "Spanish") # Get language

    # --- Check Hearts ---
    # Update hearts status before allowing lesson access
    current_hearts, _ = update_hearts(user_email)
    if current_hearts is None: # User not found
        flash("Could not verify user data.", "error")
        return redirect(url_for('login'))

    if current_hearts <= 0:
        flash("You're out of hearts! Wait for them to regenerate or visit the shop.", "warning")
        # Redirect back to dashboard, maybe with a query param indicating no hearts?
        return redirect(url_for('dashboard', lang=lang, error='no_hearts'))

    # --- Check Lesson Prerequisite ---
    if lesson_id > 1:
        required_lesson_id = lesson_id - 1
        conn = get_db_connection()
        completion = conn.execute(
            "SELECT 1 FROM progress WHERE user_email = ? AND lesson_id = ? AND language = ? AND completed = 1",
            (user_email, required_lesson_id, lang)
        ).fetchone()
        conn.close()
        if not completion:
            flash(f"Please complete Lesson {required_lesson_id} first.", "warning")
            return redirect(url_for('dashboard', lang=lang))


    # --- Load Lesson Data ---
    lang_key = f"{lang}-English"
    lessons = lessons_data.get(lang_key, [])
    lesson = next((l for l in lessons if l.get("lesson") == lesson_id), None)

    if lesson:
        # Optional: Deduct heart immediately upon starting lesson?
        # Or deduct only upon making a mistake (more complex)?
        # For simplicity, let's assume mistakes trigger /lose_heart calls from lesson.js
        return render_template("lesson.html", lesson=lesson, language=lang, current_hearts=current_hearts) # Pass hearts

    flash(f"Lesson {lesson_id} not found for {lang}.", "error")
    return redirect(url_for('dashboard', lang=lang))

# Add routes for profile, settings if needed
# app.py

# app.py

@app.route('/profile')
def profile():
    if "user" not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('login'))

    user_email = session['user']
    user_info = get_user_data(user_email)

    if not user_info:
        flash("Could not retrieve your profile data.", "danger")
        session.pop('user', None)
        return redirect(url_for('login'))

    # --- Calculate Derived Stats ---
    level, xp_percentage, next_level_xp = calculate_level_xp(user_info["xp"])
    profile_color = get_profile_color(user_info["fullname"] or user_info["email"])
    formatted_join_date = "Join date not recorded"
    try:
        if "join_date" in user_info.keys() and user_info["join_date"]:
            join_dt = datetime.strptime(user_info["join_date"], "%Y-%m-%d")
            formatted_join_date = f"Member since {join_dt.strftime('%B %d, %Y')}"
    except (KeyError, ValueError, TypeError): pass

    # --- Fetch Achievements (List and Count) ---
    earned_achievements_list = []
    earned_achievements_count = 0 # Initialize count
    try:
        conn_ach = get_db_connection()
        if conn_ach:
             # Fetch details for listing
             earned_rows = conn_ach.execute(
                  """SELECT ua.achievement_key, a.name, a.description, a.icon FROM user_achievements ua
                     JOIN achievements a ON ua.achievement_key = a.achievement_key
                     WHERE ua.user_email = ? ORDER BY ua.earned_at DESC""", (user_email,)
              ).fetchall()
             earned_achievements_list = [dict(row) for row in earned_rows]
             # Get the count separately (more efficient than len() if list is large)
             count_result = conn_ach.execute("SELECT COUNT(*) as count FROM user_achievements WHERE user_email = ?", (user_email,)).fetchone()
             earned_achievements_count = count_result['count'] if count_result else 0
             conn_ach.close()
    except Exception as e:
         print(f"Error fetching profile achievements: {e}")

    # --- Get Completed Lessons Count (Total across all languages) ---
    total_lessons_completed = 0
    try:
        conn_lessons = get_db_connection()
        if conn_lessons:
            # Count distinct lessons (lesson_id + language combination)
            count_result = conn_lessons.execute(
                "SELECT COUNT(DISTINCT lesson_id || '-' || language) as count FROM progress WHERE user_email = ? AND completed = 1",
                (user_email,)
            ).fetchone()
            total_lessons_completed = count_result['count'] if count_result else 0
            conn_lessons.close()
    except Exception as e:
        print(f"Error fetching completed lessons count for profile: {e}")

    # --- Prepare data for the template ---
    profile_data = {
        "fullname": user_info["fullname"] or user_email,
        "email": user_email,
        "join_date_formatted": formatted_join_date,
        "profile_color": profile_color,
        "initial": (user_info["fullname"] or user_email)[0].upper(),
        "level": level,
        "xp": user_info["xp"],
        "xp_percentage": xp_percentage,
        "next_level_xp": next_level_xp,
        "streak": user_info["streak"],
        "gems": user_info["gems"],
        "earned_achievements": earned_achievements_list, # Pass the list for display later
        "achievements_count": earned_achievements_count, # <<< Pass the count
        "lessons_done_count": total_lessons_completed    # <<< Pass the count
    }

    return render_template("profile.html", **profile_data)

# --- Settings Page Routes ---

@app.route('/settings', methods=['GET'])
def settings():
    """Displays the settings page."""
    if "user" not in session:
        flash("Please log in to access settings.", "warning")
        return redirect(url_for('login'))

    user_email = session['user']
    user_info = get_user_data(user_email)

    if not user_info:
        flash("Could not retrieve your profile data.", "danger")
        session.pop('user', None) # Log out if data missing
        return redirect(url_for('login'))

    return render_template(
        "settings.html",
        current_fullname=user_info["fullname"],
        current_email=user_info["email"]
    )

@app.route('/settings/update_profile', methods=['POST'])
def update_profile():
    """Handles updating user's full name and email."""
    if "user" not in session:
        return jsonify({"error": "Not authorized"}), 401 # Return JSON error for potential JS calls

    user_email = session['user']
    new_fullname = request.form.get('fullname')
    new_email = request.form.get('email')

    if not new_fullname:
        flash("Full name cannot be empty.", "danger")
        return redirect(url_for('settings'))

    if not new_email:
         flash("Email cannot be empty.", "danger")
         return redirect(url_for('settings'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if email is being changed and if the new email already exists for *another* user
    if new_email.lower() != user_email.lower():
        cursor.execute("SELECT 1 FROM users WHERE email = ? AND email != ?", (new_email.lower(), user_email.lower()))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("That email address is already taken by another user.", "warning")
            conn.close()
            return redirect(url_for('settings'))
        else:
             # Update email if it's valid and different
            try:
                cursor.execute("UPDATE users SET fullname = ?, email = ? WHERE email = ?",
                               (new_fullname, new_email.lower(), user_email))
                conn.commit()
                # IMPORTANT: Update the email in the session!
                session['user'] = new_email.lower()
                flash("Profile updated successfully!", "success")
            except sqlite3.Error as e:
                 conn.rollback()
                 flash(f"Database error updating profile: {e}", "danger")
            finally:
                conn.close()
    else:
        # Only update fullname if email hasn't changed
        try:
            cursor.execute("UPDATE users SET fullname = ? WHERE email = ?", (new_fullname, user_email))
            conn.commit()
            flash("Full name updated successfully!", "success")
        except sqlite3.Error as e:
             conn.rollback()
             flash(f"Database error updating full name: {e}", "danger")
        finally:
             conn.close()

    # --- SECURITY NOTE ---
    # In a production app, changing email should trigger a verification email
    # to the NEW address before the change is finalized in the database and session.
    # This prevents hijacking accounts by changing the email to one the attacker controls.
    # This basic implementation updates it directly for simplicity here.

    return redirect(url_for('settings'))


@app.route('/settings/update_password', methods=['POST'])
def update_password():
    """Handles updating the user's password."""
    if "user" not in session:
        return jsonify({"error": "Not authorized"}), 401

    user_email = session['user']
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # --- Basic Validation ---
    if not current_password or not new_password or not confirm_password:
        flash("All password fields are required.", "danger")
        return redirect(url_for('settings'))

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for('settings'))

    if len(new_password) < 6: # Example minimum length
         flash("New password must be at least 6 characters long.", "danger")
         return redirect(url_for('settings'))

    # --- Verify Current Password ---
    user_info = get_user_data(user_email)
    if not user_info:
        flash("Could not retrieve user data.", "danger")
        return redirect(url_for('settings')) # Or redirect to login

    if not check_password_hash(user_info['password'], current_password):
        flash("Incorrect current password.", "danger")
        return redirect(url_for('settings'))

    # --- Update Password ---
    try:
        new_hashed_password = generate_password_hash(new_password)
        conn = get_db_connection()
        conn.execute("UPDATE users SET password = ? WHERE email = ?", (new_hashed_password, user_email))
        conn.commit()
        conn.close()
        flash("Password updated successfully!", "success")
    except sqlite3.Error as e:
        flash(f"Database error updating password: {e}", "danger")
        # Ensure connection is closed even on error
        if conn: conn.close()

    return redirect(url_for('settings'))


@app.route('/settings/delete_account', methods=['POST'])
def delete_account():
    """Handles deleting the user's account."""
    if "user" not in session:
         return jsonify({"error": "Not authorized"}), 401

    user_email = session['user']
    confirm_password = request.form.get('confirm_password_delete') # Match input name

    if not confirm_password:
        flash("Password confirmation is required to delete your account.", "danger")
        return redirect(url_for('settings'))

    # --- Verify Password ---
    user_info = get_user_data(user_email)
    if not user_info:
        flash("Could not retrieve user data for deletion.", "danger")
        return redirect(url_for('settings'))

    if not check_password_hash(user_info['password'], confirm_password):
        flash("Incorrect password. Account deletion cancelled.", "danger")
        return redirect(url_for('settings'))

    # --- PERFORM DELETION ---
    # IMPORTANT: Ensure ON DELETE CASCADE is set correctly on the 'progress' table's
    # foreign key in your database schema (database.py). If it is, deleting
    # the user should automatically delete their progress records.
    try:
        conn = get_db_connection()
        print(f"ATTEMPTING TO DELETE USER: {user_email}")
        conn.execute("DELETE FROM users WHERE email = ?", (user_email,))
        conn.commit()
        conn.close()
        print(f"SUCCESSFULLY DELETED USER: {user_email}")

        # Clear the session completely
        session.clear()

        flash("Your account has been permanently deleted.", "success")
        return redirect(url_for('login')) # Redirect to login page after deletion

    except sqlite3.Error as e:
        flash(f"Database error deleting account: {e}", "danger")
        print(f"DATABASE ERROR deleting account for {user_email}: {e}")
        # Ensure connection is closed even on error
        if conn: conn.close()
        return redirect(url_for('settings')) # Redirect back to settings on error


if __name__ == "__main__":
    # Ensure the DB is initialized before running the app
    # Running database.py separately is often cleaner
    # init_db() # Or call it here if database.py isn't run separately
    print("Starting Flask app...")
    print(f"Available languages: {AVAILABLE_LANGUAGES}")
    app.run(debug=True) # debug=True enables auto-reloading and error pages