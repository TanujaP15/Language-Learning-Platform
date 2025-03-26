import sqlite3
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash  # Secure passwords

app = Flask(__name__)
app.secret_key = "d4f40074b6653f5d389ea76ab38b0ba349e1d020b6d5333e29e10f2de110d5df"  # Required for session management

# Load lessons.json with error handling
try:
    with open("lessons.json", "r", encoding="utf-8") as file:
        lessons_data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading lessons.json: {e}")
    lessons_data = {}

# Database Connection Helper
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # Allows fetching rows as dictionaries
    return conn

# Available languages
AVAILABLE_LANGUAGES = ["Spanish", "French", "German", "Japanese"]

# Initialize Database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

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

init_db()  # Ensure database is initialized

# Home Route
@app.route('/')
def home():
    return render_template("index.html")

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']

        if not fullname or not email or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)  # Encrypt password

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (fullname, email, password) VALUES (?, ?, ?)", 
                           (fullname, email, hashed_password))
            conn.commit()
            conn.close()
            
            session['user'] = email  # Auto-login after signup
            flash("Account created successfully! 🎉", "success")
            return redirect(url_for('dashboard'))
        
        except sqlite3.IntegrityError:
            flash("User already exists. Try logging in.", "warning")
            return redirect(url_for('login'))

    return render_template("login.html")

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):  # Verify password
            session['user'] = user["email"]  # Store email in session
            flash("Login successful! ✅", "success")
            return redirect(url_for('dashboard'))
        
        flash("Invalid credentials. Please try again.", "danger")
        return redirect(url_for('login'))

    return render_template("login.html")

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove user session
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for('login'))

    lang = request.args.get("lang", "Spanish")
    lessons = lessons_data.get(f"{lang}-English", [])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT lesson_id FROM progress WHERE user_email = ? AND completed = 1", (session["user"],))
    completed_lessons = [row["lesson_id"] for row in cursor.fetchall()]
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  
        return jsonify({"lessons": lessons, "completed": completed_lessons})  # ✅ Return completed lessons

    return render_template("dashboard.html", lessons=lessons, language=lang, user=session["user"], completed_lessons=completed_lessons)

# Lesson Route
@app.route('/lesson/<int:lesson_id>')
def lesson_page(lesson_id):
    if "user" not in session:  # Redirect if user is not logged in
        flash("Please log in to access lessons.", "warning")
        return redirect(url_for('login'))

    lang = request.args.get("lang", "Spanish")  # Default to Spanish
    lessons = lessons_data.get(f"{lang}-English", [])

    lesson = next((lesson for lesson in lessons if lesson.get("lesson") == lesson_id), None)
    if lesson:
        return render_template("lesson.html", lesson=lesson, language=lang)
    
    return jsonify({"error": "Lesson not found", "lesson_id": lesson_id}), 404

@app.route('/complete_lesson/<int:lesson_id>', methods=['POST'])
def complete_lesson(lesson_id):
    if "user" not in session:
        return jsonify({"error": "User not logged in"}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the lesson is already completed
    cursor.execute("SELECT completed FROM progress WHERE user_email = ? AND lesson_id = ?", (session["user"], lesson_id))
    row = cursor.fetchone()

    if row and row["completed"]:
        conn.close()
        return jsonify({"message": "Lesson already completed!"})

    # Mark lesson as completed
    cursor.execute("INSERT OR REPLACE INTO progress (user_email, lesson_id, completed) VALUES (?, ?, 1)", 
                   (session["user"], lesson_id))
    conn.commit()
    
    # Unlock next lesson
    next_lesson = lesson_id + 1
    cursor.execute("INSERT OR IGNORE INTO progress (user_email, lesson_id, completed) VALUES (?, ?, 0)", 
                   (session["user"], next_lesson))
    
    conn.commit()
    conn.close()

    return jsonify({"message": "Lesson marked as completed!", "next_lesson": next_lesson})


if __name__ == "__main__":
    app.run(debug=True)
