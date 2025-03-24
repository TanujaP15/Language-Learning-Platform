from flask import Flask, render_template, request, jsonify, redirect, url_for
import json

app = Flask(__name__)

# Load lessons.json with error handling
try:
    with open("lessons.json", "r", encoding="utf-8") as file:
        lessons_data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading lessons.json: {e}")
    lessons_data = {}

# Available languages
AVAILABLE_LANGUAGES = ["Spanish", "French", "German", "Japanese"]

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Dummy authentication (Replace with actual validation)
        if email == "user@example.com" and password == "password123":
            return redirect(url_for('dashboard'))
        
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    lang = request.args.get("lang", "Spanish")  # Get language from query params (default to Spanish)
    lessons = lessons_data.get(f"{lang}-English", [])  # Fetch lessons dynamically

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  
        return jsonify({"lessons": lessons})  # Return lessons for AJAX calls

    return render_template("dashboard.html", lessons=lessons, language=lang)  # Render template for normal requests

@app.route('/lesson/<int:lesson_id>')
def lesson_page(lesson_id):
    lang = request.args.get("lang", "Spanish")   #Default to Spanish
    lessons = lessons_data.get(f"{lang}-English", [])

    lesson = next((lesson for lesson in lessons if lesson.get("lesson") == lesson_id), None)
    if lesson:
        return render_template("lesson.html", lesson=lesson, language=lang)
    
    return jsonify({"error": "Lesson not found", "lesson_id": lesson_id}), 404

if __name__ == "__main__":
    app.run(debug=True)
