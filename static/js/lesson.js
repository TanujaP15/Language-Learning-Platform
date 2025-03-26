let currentQuestionIndex = 0;
let hearts = 5; // Default hearts (updated from server)

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
            updateHearts();
        });
}

// Update hearts display
function updateHearts() {
    document.getElementById("hearts-container").innerText = `❤️ x${hearts}`;
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

    if (q.type === "matching") {
        let correct = true;
        Object.keys(q.pairs).forEach(key => {
            let userInputField = document.getElementById(key);
            if (!userInputField) return; // Prevent errors if input not found
        
            let userInput = userInputField.value.trim();
            if (userInput.toLowerCase() !== q.pairs[key].toLowerCase()) {
                correct = false;
            }
        });
        isCorrect = correct;
    } else {
        let userAnswer = selectedOption || document.getElementById("user-answer")?.value?.trim() || "";
        if (!userAnswer) {
            alert("⚠️ Please enter an answer!");
            return;
        }

        let correctAnswers = Array.isArray(q.answer) ? q.answer.map(ans => ans.toLowerCase().trim()) : [q.answer.toLowerCase().trim()];
        isCorrect = correctAnswers.includes(userAnswer.toLowerCase());
    }

    if (isCorrect) {
        feedbackContainer.innerHTML = "<p class='text-success'>✅ Correct!</p>";
    } else {
        feedbackContainer.innerHTML = `<p class='text-danger'>❌ Incorrect! Correct answer: <strong>${q.answer}</strong></p>`;
        
        // Lose a heart if the answer is wrong
        fetch("/lose_heart", { method: "POST" })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    hearts = data.hearts;
                    updateHearts();
                    if (hearts === 0) {
                        alert("❌ No hearts left! Please wait for hearts to regenerate.");
                        window.location.href = "/dashboard";
                    }
                } else {
                    alert("Error updating hearts. Please try again.");
                }
            })
            .catch(error => {
                console.error("Error losing heart:", error);
                alert("Network error. Please try again.");
            });

    }

    document.getElementById("next-btn").style.display = "block"; 
}

// Move to next question
function nextQuestion() {
    currentQuestionIndex++;
    document.getElementById("next-btn").style.display = "none";
    loadQuestion();
}
