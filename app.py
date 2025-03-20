from flask import Flask, render_template, request, jsonify, redirect, url_for
import json

app = Flask(__name__)

# Load lessons.json with error handling
try:
    with open("lessons.json", "r", encoding="utf-8") as file:
        lessons_data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading lessons.json: {e}")
    lessons_data = {}  # Fallback to an empty dictionary

# Extract Spanish lessons safely
spanish_lessons = lessons_data.get("Spanish-English", [])

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Dummy authentication (Replace this with actual user validation)
        if email == "user@example.com" and password == "password123":
            return redirect(url_for('dashboard'))
        
    #     return render_template("login.html", error="Invalid credentials. Try again.")

    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    if not spanish_lessons:
        return "No lessons found", 404
    
    first_lesson = spanish_lessons[0] if spanish_lessons else None
    return render_template("dashboard.html", lesson=first_lesson)

@app.route('/lesson/<int:lesson_id>')
def lesson_page(lesson_id):
    lesson = next((lesson for lesson in spanish_lessons if lesson.get("lesson") == lesson_id), None)
    
    if lesson:
        return render_template("lesson.html", lesson=lesson)
    
    return jsonify({"error": "Lesson not found", "lesson_id": lesson_id}), 404

# Custom 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)
