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

# --- Routes ---

@app.route('/')
def home():
    if "user" in session:
        return redirect(url_for('dashboard')) # Redirect logged-in users to dashboard
    return render_template("index.html")

# Signup Route
# app.py

# ... (other code) ...

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # ... (your existing POST logic) ...
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')

        if not fullname or not email or not password:
            flash("All fields are required!", "danger")
            # --- Pass is_signup=True when re-rendering ---
            return render_template("login.html", is_signup=True)

        hashed_password = generate_password_hash(password)
        today_iso = date.today().isoformat()

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (fullname, email, password, last_streak_update, last_daily_reset) VALUES (?, ?, ?, ?, ?)",
                (fullname, email, hashed_password, today_iso, today_iso)
            )
            conn.commit()
            conn.close()
            session['user'] = email
            flash("Account created successfully! Welcome! 🎉", "success")
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash("Email already exists. Please log in.", "warning")
            # --- Redirect to login, don't need is_signup=True here ---
            return redirect(url_for('login'))
        except Exception as e:
             flash(f"An error occurred: {e}", "danger")
             # --- Pass is_signup=True when re-rendering ---
             return render_template("login.html", is_signup=True)

    # --- Handle GET request for /signup ---
    return render_template("login.html", is_signup=True) # Pass flag to show signup form

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

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Mark lesson as completed ---
    try: # Wrap DB operations in try/except
        cursor.execute("INSERT OR REPLACE INTO progress (user_email, lesson_id, language, completed) VALUES (?, ?, ?, 1)",
                       (user_email, lesson_id, lang))
        print(f"User {user_email}: Marked lesson {lesson_id} ({lang}) as completed in progress table.")

        # --- Update User Stats (XP, Daily Progress, Streak) ---
        user_stats = cursor.execute(
            "SELECT xp, daily_progress, daily_goal, streak, last_streak_update FROM users WHERE email = ?",
            (user_email,)
        ).fetchone()

        if not user_stats:
             # This shouldn't happen if user is logged in, but good practice
             print(f"CRITICAL ERROR: User {user_email} not found in users table during lesson completion.")
             conn.rollback()
             conn.close()
             return jsonify({"error": "User data not found during update"}), 500

        # --- START DETAILED STREAK DEBUG ---
        print(f"--- Streak Check Start (User: {user_email}, Lesson: {lesson_id}, Lang: {lang}) ---")
        print(f"DB Values Read -> Streak: {user_stats['streak']}, Last Update STR: '{user_stats['last_streak_update']}'") # Added quotes for clarity

        new_xp = user_stats["xp"] + lesson_xp
        new_daily_progress = user_stats["daily_progress"] + lesson_xp
        current_streak = user_stats["streak"]
        # updated_streak = current_streak # Default assumption

        today = date.today()
        last_streak_update_str = user_stats["last_streak_update"]
        last_streak_date = None
        if last_streak_update_str: # Check if the string is not None or empty
            try:
                # Attempt to parse the date string
                last_streak_date = date.fromisoformat(last_streak_update_str)
            except (ValueError, TypeError) as e: # Catch potential errors during parsing
                print(f"WARNING: Could not parse last_streak_update date '{last_streak_update_str}' for user {user_email}. Error: {e}")
                last_streak_date = None # Ensure it's None if parsing fails
        else:
             print(f"DB Info -> last_streak_update was NULL or empty.")


        print(f"Parsed/Compared -> Today: {today}, Last Update DATE: {last_streak_date}")

        if last_streak_date == today:
            # If last update was today BUT current streak is 0, it means this is the FIRST activity today starting the streak.
            if current_streak == 0:
                print("Condition: First activity today. Starting streak at 1.")
                updated_streak = 1
            else:
                # Otherwise, already active today, maintain the existing streak.
                print("Condition: Already active today. Streak maintained.")
                updated_streak = current_streak
        elif last_streak_date == (today - timedelta(days=1)):
            # Active yesterday, INCREMENT streak
            print("Condition: Last update was yesterday. Incrementing streak.")
            updated_streak = current_streak + 1
        else: # Covers None (first time or failed parse) or date < yesterday (missed day/reset)
            # First activity ever OR missed day(s), RESET streak to 1
            print(f"Condition: New day (last update: {last_streak_date}) or missed day(s) or first activity. Setting streak to 1.")
            updated_streak = 1


        print(f"Result -> Current Streak: {current_streak}, Calculated New Streak: {updated_streak}")

        # Execute the database update
        cursor.execute(
            """UPDATE users
               SET xp = ?, daily_progress = ?, streak = ?, last_streak_update = ?
               WHERE email = ?""",
            (new_xp, new_daily_progress, updated_streak, today.isoformat(), user_email)
        )
        print(f"Executing DB Update -> New XP: {new_xp}, New Daily: {new_daily_progress}, New Streak: {updated_streak}, New Last Update: {today.isoformat()}")

        conn.commit()

        print(f"DB Commit executed successfully.")
        print("--- Streak Check End ---")
        # --- END DETAILED STREAK DEBUG ---


        # --- Fetch updated completed list for response ---
        cursor.execute("SELECT lesson_id FROM progress WHERE user_email = ? AND completed = 1 AND language = ?", (user_email, lang))
        completed_lessons = [row["lesson_id"] for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            "message": "Lesson completed!",
            "xp_earned": lesson_xp,
            "new_total_xp": new_xp,
            "new_streak": updated_streak,
            "completed_lessons": completed_lessons
        })

    except sqlite3.Error as db_err: # Catch potential SQLite errors during the whole process
         print(f"DATABASE ERROR during lesson completion for {user_email}: {db_err}")
         # Rollback any partial changes
         conn.rollback()
         conn.close()
         return jsonify({"error": "Database error during lesson completion."}), 500
    except Exception as e: # Catch any other unexpected errors
         print(f"UNEXPECTED ERROR during lesson completion for {user_email}: {e}")
         # Ensure connection is closed even on unexpected errors
         if conn:
             conn.rollback() # Rollback just in case
             conn.close()
         return jsonify({"error": "An unexpected error occurred."}), 500


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
@app.route('/profile')
def profile():
    if "user" not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('login'))

    user_email = session['user']
    user = get_user_data(user_email) # Use your existing helper

    if not user:
        flash("Could not retrieve user data.", "danger")
        return redirect(url_for('dashboard')) # Or login page

    # You'll need to create a templates/profile.html file later
    # For now, just return some text or render a basic template if you have one
    # return f"<h1>Profile Page for {user['fullname']}</h1><p>Email: {user['email']}</p><p>XP: {user['xp']}</p>"
    # Or, if you create a basic profile.html:
    # return render_template("profile.html", user=user)

    # Simplest fix for now - just return a message:
    flash("Profile page is under construction!", "info")
    return redirect(url_for('dashboard')) # Redirect back for now

@app.route('/settings')
def settings():
    if "user" not in session:
        flash("Please log in to view settings.", "warning")
        return redirect(url_for('login'))

    # Similar logic for settings if you have a settings link
    flash("Settings page is under construction!", "info")
    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    # Ensure the DB is initialized before running the app
    # Running database.py separately is often cleaner
    # init_db() # Or call it here if database.py isn't run separately
    print("Starting Flask app...")
    print(f"Available languages: {AVAILABLE_LANGUAGES}")
    app.run(debug=True) # debug=True enables auto-reloading and error pages