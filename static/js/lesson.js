let currentQuestionIndex = 0;
const questions = JSON.parse('{{ lesson.questions | tojson | safe }}'); // Load questions from Flask
const totalQuestions = questions.length;

function loadQuestion() {
    if (currentQuestionIndex >= totalQuestions) {
        document.querySelector(".quiz-container").innerHTML = "<h2>Lesson Complete! 🎉</h2>";
        return;
    }

    let questionData = questions[currentQuestionIndex];
    document.getElementById("question-text").innerText = questionData.question;
    let answerArea = document.getElementById("answer-area");
    answerArea.innerHTML = ""; // Clear previous question

    switch (questionData.type) {
        case "translation":
        case "fill_in_blank":
        case "sentence_transformation":
            answerArea.innerHTML = `<input type="text" id="user-answer" placeholder="Type your answer...">`;
            break;

        case "multiple_choice":
            questionData.options.forEach(option => {
                let optionDiv = document.createElement("div");
                optionDiv.classList.add("option");
                optionDiv.innerHTML = `<label><input type="radio" name="answer" value="${option}"> ${option}</label>`;
                answerArea.appendChild(optionDiv);
            });
            break;

        case "matching":
            let matchItems = Object.entries(questionData.pairs);
            matchItems.forEach(([key, value]) => {
                answerArea.innerHTML += `
                    <div class="match-item">
                        <span class="word">${key}</span> ➝ <input type="text" class="match-answer" data-answer="${value}" placeholder="Match here">
                    </div>
                `;
            });
            break;
    }
}

function checkAnswer() {
    let questionData = questions[currentQuestionIndex];
    let correctAnswer = questionData.answer;
    let userAnswer = "";

    if (questionData.type === "multiple_choice") {
        let selectedOption = document.querySelector("input[name='answer']:checked");
        if (!selectedOption) {
            alert("Please select an option!");
            return;
        }
        userAnswer = selectedOption.value;
    } else if (questionData.type === "matching") {
        let allCorrect = true;
        document.querySelectorAll(".match-answer").forEach(input => {
            if (input.value.trim().toLowerCase() !== input.dataset.answer.toLowerCase()) {
                allCorrect = false;
                input.style.border = "2px solid red";
            } else {
                input.style.border = "2px solid green";
            }
        });

        if (allCorrect) {
            alert("✅ Correct! Moving to next question...");
            currentQuestionIndex++;
            loadQuestion();
        } else {
            alert("❌ Some matches are incorrect! Try again.");
        }
        return;
    } else {
        userAnswer = document.getElementById("user-answer").value.trim();
        if (userAnswer === "") {
            alert("Please enter an answer!");
            return;
        }
    }

    if (userAnswer.toLowerCase() === correctAnswer.toLowerCase()) {
        alert("✅ Correct! Moving to next question...");
        currentQuestionIndex++;
        loadQuestion();
    } else {
        alert("❌ Try Again!");
    }
}

// Load the first question when the page loads
window.onload = loadQuestion;
