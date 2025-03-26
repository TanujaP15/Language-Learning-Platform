document.addEventListener("DOMContentLoaded", function () {
    const languageDropdown = document.querySelector(".dropbtn");
    const lessonContainer = document.getElementById("lesson-container");
    const heartsContainer = document.getElementById("hearts-container");

    let selectedLanguage = localStorage.getItem("selectedLanguage") || "Spanish";

    updateLanguage(selectedLanguage);
    fetchHearts();

    function updateLanguage(language) {
        localStorage.setItem("selectedLanguage", language);
        languageDropdown.innerHTML = getFlag(language) + " " + language;
        fetchLessons(language);
    }

    function getFlag(language) {
        const flags = {
            "French": "🇫🇷",
            "Spanish": "🇪🇸",
            "German": "🇩🇪",
            "Japanese": "🇯🇵"
        };
        return flags[language] || "🌐";
    }

    function fetchLessons(language) {
        fetch(`/dashboard?lang=${language}`, { headers: { "X-Requested-With": "XMLHttpRequest" } })  
            .then(response => response.json())
            .then(data => {
                lessonContainer.innerHTML = "";
                let completedLessons = data.completed || JSON.parse(localStorage.getItem("completedLessons")) || [];  // Fetch completed lessons from Flask
                let hearts = data.hearts || 0;  //fetch hearts count

                data.lessons.forEach((lesson, index) => {
                    const lessonLink = document.createElement("a");
                    lessonLink.href = hearts > 0 ? `/lesson/${lesson.lesson}?lang=${language}`: "#";
                    lessonLink.classList.add("lesson-card");

                    // Lock lessons if previous lesson is not completed
                    if ((!completedLessons.includes(lesson.lesson - 1) && lesson.lesson > 1) || hearts === 0){
                        lessonLink.classList.add("locked");
                        lessonLink.href = "#"; // Prevent navigation for locked lessons
                    }

                    const progressCircle = document.createElement("div");
                    progressCircle.classList.add("progress-circle");
                    progressCircle.innerText = lesson.lesson;

                    const lessonTitle = document.createElement("p");
                    lessonTitle.classList.add("lesson-title");
                    lessonTitle.innerText = lesson.title;

                    if (completedLessons.includes(lesson.lesson)) {
                        lessonLink.classList.add("completed");
                        lessonLink.innerHTML += " ✅";
                    }

                    lessonLink.appendChild(progressCircle);
                    lessonLink.appendChild(lessonTitle);
                    lessonContainer.appendChild(lessonLink);
                });
            })
            .catch(error => console.error("Error fetching lessons:", error));
    }

    function fetchHearts() {
        fetch(`/get_hearts`, { headers: { "X-Requested-With": "XMLHttpRequest" } })  
            .then(response => response.json())
            .then(data => {
                document.getElementById("hearts-container").innerHTML = `❤️ x${data.hearts}`;
                
                // Show countdown timer only if hearts are not full
                if (data.hearts < 5 && data.time_left > 0) {
                    startHeartCountdown(data.time_left);
                } else {
                    document.getElementById("heart-timer").innerText = "";
                }
            })
            .catch(error => console.error("Error fetching hearts:", error));
    }
    
    // Countdown Timer
    function startHeartCountdown(timeLeft) {
        let timerElement = document.getElementById("heart-timer");
        
        function updateTimer() {
            let minutes = Math.floor(timeLeft / 60);
            let seconds = timeLeft % 60;
            timerElement.innerText = `Next heart in: ${minutes}m ${seconds}s`;
            
            if (timeLeft > 0) {
                timeLeft--;
                setTimeout(updateTimer, 1000);
            } else {
                fetchHearts();  // Refresh hearts when countdown ends
            }
        }
        
        updateTimer();
    }
    
    // Auto-refresh hearts every 5 sec
    setInterval(fetchHearts, 5000);
    

    document.querySelectorAll(".dropdown-content a").forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const selectedLang = this.innerText.trim().split(" ")[1];
            updateLanguage(selectedLang);
        });
    });
});
