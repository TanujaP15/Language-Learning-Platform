let currentQuestionIndex = 0;
let hearts = 5; // Default hearts (updated from server)
let heartRegenerationTime = 900;

document.addEventListener("DOMContentLoaded", function () {
    fetchHearts();  // Get hearts count from server
    loadQuestion();
});

// Fetch current hearts from server
function fetchHearts() {
    fetch("/get_hearts")
        .then(response => response.json())
        .then(data => {
            hearts = data.hearts;
            heartRegenerationTime = data.time_left || 900;
            updateHearts();
            if (hearts === 0) startHeartTimer();
        });
}

// Update hearts display
function updateHearts() {
    let heartContainer = document.getElementById("hearts-container");
    heartContainer.innerHTML = "";
    for (let i = 0; i < hearts; i++) {
        heartContainer.innerHTML += "❤️";
    }
    if (hearts === 0) {
        heartContainer.innerHTML += ` <span id="heart-timer">⌛ ${formatTime(heartRegenerationTime)}</span>`;
        startHeartTimer();
    }
}


// Start the heart regeneration timer
function startHeartTimer() {
    let timerElement = document.getElementById("heart-timer");
    let timer = setInterval(() => {
        if (heartRegenerationTime <= 0) {
            clearInterval(timer);
            fetchHearts();
        } else {
            heartRegenerationTime--;
            timerElement.innerText = `⌛ ${formatTime(heartRegenerationTime)}`;
        }
    }, 1000);
}

// Format time as MM:SS
function formatTime(seconds) {
    let minutes = Math.floor(seconds / 60);
    let secs = seconds % 60;
    return `${minutes}:${secs < 10 ? "0" : ""}${secs}`;
}

function updateProgress() {
    let progress = ((currentQuestionIndex + 1) / lessonQuestions.length) * 100;
    document.getElementById("progress-bar").style.width = `${progress}%`;
}

// Load question dynamically
function loadQuestion() {
    if (currentQuestionIndex >= lessonQuestions.length) {
        document.getElementById("question-container").innerHTML = "<h2>🎉 Lesson Complete!</h2>";
        document.getElementById("answer-area").innerHTML = "";
        document.getElementById("feedback").innerHTML = "";
        
        fetch(`/complete_lesson/${lessonId}`, { method: "POST" })
            .then(response => response.json())
            .then(data => {
                console.log(data.message);
                alert("Lesson Completed! Next lesson unlocked.");
                
                // Update completed lessons in localStorage
                localStorage.setItem("completedLessons", JSON.stringify(data.completed_lessons));
                
                window.location.href = "/dashboard";
            });
        return;
    }

    let q = lessonQuestions[currentQuestionIndex];
    document.getElementById("question-container").innerHTML = `<h2>${q.question}</h2>`;
    updateProgress();
    let answerArea = document.getElementById("answer-area");
    answerArea.innerHTML = "";
    document.getElementById("feedback").innerHTML = "";
    document.getElementById("next-btn").style.display = "none";  
    document.getElementById("check-answer-btn").disabled = true; // Disable submit until input is given

    if (q.type === "translation" || q.type === "fill_in_blank" || q.type === "sentence_transformation") {
        answerArea.innerHTML = `<input type="text" id="user-answer" class="form-control" placeholder="Your answer" oninput="enableSubmit()">`;
        answerArea.innerHTML += `<button id="check-answer-btn" class="btn btn-primary mt-2" onclick="checkAnswer()">Submit</button>`;
    } else if (q.type === "multiple_choice") {
        q.options.forEach(option => {
            answerArea.innerHTML += `<button class="btn btn-outline-primary m-2" onclick="checkAnswer('${option}')">${option}</button>`;
        });
    } else if (q.type === "matching") {
        Object.keys(q.pairs).forEach(key => {
            answerArea.innerHTML += `<p>${key} → 
            <input type="text" id="${key}" class="form-control" placeholder="Your answer" oninput="enableSubmit()"></p>`;
        });
        answerArea.innerHTML += `<button id="check-answer-btn" class="btn btn-primary mt-2" onclick="checkAnswer()">Submit</button>`;
        document.getElementById("check-answer-btn").disabled = true; // Initially disabled
    }
}

// Enable the submit button when all inputs have values
function enableSubmit() {
    let allFilled = true;
    
    let userInputField = document.getElementById("user-answer");
    if (userInputField && userInputField.value.trim() === "") {
        allFilled = false;
    }

    document.querySelectorAll("#answer-area input").forEach(input => {
        if (input.value.trim() === "") {
            allFilled = false;
        }
    });

    document.getElementById("check-answer-btn").disabled = !allFilled;
}

// Check user's answer
function checkAnswer(selectedOption = null) {
    let q = lessonQuestions[currentQuestionIndex];
    let feedbackContainer = document.getElementById("feedback");
    let isCorrect = false;

    if (!q) {
        console.error("Question not found!");
        return;
    }

    if (q.type === "matching") {
        isCorrect = checkMatchingAnswer(q.pairs);
    } else {
        let userAnswer = selectedOption || document.getElementById("user-answer")?.value?.trim();
        if (!userAnswer) {
            alert("⚠️ Please enter an answer!");
            return;
        }
        isCorrect = checkTextAnswer(userAnswer, q.answer);
    }

    showFeedback(isCorrect, q.answer);
    if (!isCorrect) handleIncorrectAnswer();
    
    document.getElementById("next-btn").style.display = "block";
}

// ✅ Helper function to check Matching type answers
function checkMatchingAnswer(correctPairs) {
    return Object.keys(correctPairs).every(key => {
        let userInputField = document.getElementById(key);
        return userInputField && userInputField.value.trim().toLowerCase() === correctPairs[key].toLowerCase();
    });
}

// ✅ Helper function to check text-based answers (translation, fill in blank, etc.)
function checkTextAnswer(userAnswer, correctAnswer) {
    let correctAnswers = Array.isArray(correctAnswer) ? 
        correctAnswer.map(ans => ans.toLowerCase().trim()) : 
        [correctAnswer.toLowerCase().trim()];
    
    return correctAnswers.includes(userAnswer.toLowerCase());
}

// ✅ Display correct or incorrect feedback
function showFeedback(isCorrect, correctAnswer) {
    let feedbackContainer = document.getElementById("feedback");
    feedbackContainer.innerHTML = isCorrect ? 
        "<p class='text-success'>✅ Correct!</p>" : 
        `<p class='text-danger'>❌ Incorrect! Correct answer: <strong>${correctAnswer}</strong></p>`;
}

// ✅ Handle incorrect answers (lose a heart, animate UI)
function handleIncorrectAnswer() {
    fetch("/lose_heart", { method: "POST" })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                hearts = data.hearts; // Update hearts count from server
                updateHearts(); // Update UI
                animateHeartLoss();
            } else {
                console.error("Error losing heart:", data.error);
            }
        })
        .catch(error => console.error("Fetch error:", error));
}


// Animate heart loss in the navbar
function animateHeartLoss() {
    let heartContainer = document.getElementById("hearts-container");
    let lostHeart = document.createElement("span");
    lostHeart.innerHTML = "💔";
    lostHeart.style.color = "red";
    lostHeart.style.marginLeft = "5px";
    lostHeart.style.transition = "opacity 0.5s ease-in-out";
    heartContainer.appendChild(lostHeart);

    setTimeout(() => {
        lostHeart.style.opacity = "0";
        setTimeout(() => lostHeart.remove(), 500);
    }, 500);
}

// Move to next question
function nextQuestion() {
    currentQuestionIndex++;
    document.getElementById("next-btn").style.display = "none";
    loadQuestion();
}
