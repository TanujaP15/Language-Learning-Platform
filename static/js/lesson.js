let currentQuestionIndex = 0;

document.addEventListener("DOMContentLoaded", function () {
    loadQuestion();
});

function loadQuestion() {
    if (currentQuestionIndex >= lessonQuestions.length) {
        document.getElementById("question-container").innerHTML = "<h2>🎉 Lesson Complete!</h2>";
        document.getElementById("options-container").innerHTML = "";
        document.getElementById("feedback").innerHTML = "";
        
        // Mark lesson as completed
        fetch(`/complete_lesson/${lessonId}`, { method: "POST" })
            .then(response => response.json())
            .then(data => {
                console.log(data.message);
                alert("Lesson Completed! Next lesson unlocked.");
                window.location.href = "/dashboard";  // Redirect to dashboard
            });
    

        return;
    }

    let q = lessonQuestions[currentQuestionIndex];
    document.getElementById("question-container").innerHTML = `<h2>${q.question}</h2>`;
    let optionsContainer = document.getElementById("options-container");
    optionsContainer.innerHTML = "";
    document.getElementById("feedback").innerHTML = "";
    document.getElementById("next-btn").style.display = "none";  // Hide Next button initially

    if (q.type === "translation" || q.type === "fill_in_blank" || q.type === "sentence_transformation") {
        optionsContainer.innerHTML = `<input type="text" id="user-answer" class="form-control" placeholder="Your answer">
                                      <button class="btn btn-primary mt-2" onclick="checkAnswer()">Submit</button>`;
    } else if (q.type === "multiple_choice") {
        q.options.forEach(option => {
            optionsContainer.innerHTML += `<button class="btn btn-outline-primary m-2" onclick="checkAnswer('${option}')">${option}</button>`;
        });
    } else if (q.type === "matching") {
        Object.keys(q.pairs).forEach(key => {
            optionsContainer.innerHTML += `<p>${key} → <input type="text" id="${key}" class="form-control" placeholder="Your answer"></p>`;
        });
        optionsContainer.innerHTML += `<button class="btn btn-primary mt-2" onclick="checkAnswer()">Submit</button>`;
    }
}

function checkAnswer(selectedOption = null) {
    let q = lessonQuestions[currentQuestionIndex];
    let userAnswer = selectedOption || document.getElementById("user-answer")?.value?.trim() || "";
    let feedbackContainer = document.getElementById("feedback");

    let isCorrect = false;

    if (q.type === "matching") {
        let correct = true;
        Object.keys(q.pairs).forEach(key => {
            let userInput = document.getElementById(key).value.trim();
            if (userInput.toLowerCase() !== q.pairs[key].toLowerCase()) correct = false;
        });
        isCorrect = correct;
    } else if (q.type === "multiple_choice" || q.type === "fill_in_blank" || q.type === "translation" || q.type === "sentence_transformation") {
        let correctAnswers = Array.isArray(q.answer) ? q.answer.map(ans => ans.toLowerCase().trim()) : [q.answer.toLowerCase().trim()];
        isCorrect = correctAnswers.includes(userAnswer.toLowerCase());
    }

    if (isCorrect) {
        feedbackContainer.innerHTML = "<p class='text-success'>✅ Correct!</p>";
    }  else {
        fetch("/lose_heart", { method: "POST" }) // Lose heart if wrong
            .then(response => response.json())
            .then(data => {
                document.getElementById("hearts-container").innerText = `❤️ x${data.hearts}`;

                if (data.hearts === 0) {
                    alert("No hearts left! Wait for hearts to regenerate.");
                    window.location.href = "/dashboard";
                }
            });

        feedbackContainer.innerHTML = `<p class='text-danger'>❌ Incorrect! Correct answer: <strong>${q.answer}</strong></p>`;
    }

    // ✅ Show "Next Question" button regardless of correctness
    document.getElementById("next-btn").style.display = "block";
}

function nextQuestion() {
    currentQuestionIndex++;
    document.getElementById("next-btn").style.display = "none";
    loadQuestion();
}
