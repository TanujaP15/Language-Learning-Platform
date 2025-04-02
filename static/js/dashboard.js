document.addEventListener("DOMContentLoaded", function () {
    const languageDropdown = document.querySelector(".dropbtn");
    const lessonContainer = document.getElementById("lesson-container");
    const heartsContainer = document.getElementById("hearts-container");
    const heartTimer = document.getElementById("heart-timer");

    let selectedLanguage = localStorage.getItem("selectedLanguage") || "Spanish";
    updateLanguage(selectedLanguage);
    fetchHearts();

    function updateLanguage(language) {
        localStorage.setItem("selectedLanguage", language);
        languageDropdown.innerHTML = `${getFlag(language)} ${language}`;
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
                let completedLessons = data.completed || JSON.parse(localStorage.getItem("completedLessons")) || [];
                let hearts = data.hearts || 0;
                
                data.lessons.forEach(lesson => {
                    const lessonLink = document.createElement("a");
                    lessonLink.href = hearts > 0 ? `/lesson/${lesson.lesson}?lang=${language}` : "#";
                    lessonLink.classList.add("lesson-card");

                    if ((!completedLessons.includes(lesson.lesson - 1) && lesson.lesson > 1) || hearts === 0) {
                        lessonLink.classList.add("locked");
                        lessonLink.href = "#";
                    }

                    lessonLink.innerHTML = `
                        <div class="progress-circle">${lesson.lesson}</div>
                        <p class="lesson-title">${lesson.title}</p>
                        ${completedLessons.includes(lesson.lesson) ? "✅" : ""}
                    `;

                    lessonContainer.appendChild(lessonLink);
                });
            })
            .catch(error => console.error("Error fetching lessons:", error));
    }

    function fetchHearts() {
        fetch(`/get_hearts`, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(response => response.json())
            .then(data => {
                heartsContainer.innerHTML = `❤️ x${data.hearts}`;
                
                if (data.hearts < 5 && data.time_left > 0) {
                    startHeartCountdown(data.time_left);
                } else {
                    heartTimer.innerText = "";
                }
            })
            .catch(error => console.error("Error fetching hearts:", error));
    }

    function startHeartCountdown(timeLeft) {
        let timerElement = document.getElementById("heart-timer");
    
        // Retrieve expiration timestamp if available
        let expirationTimestamp = localStorage.getItem("heartExpiration");
    
        if (!expirationTimestamp) {
            expirationTimestamp = Date.now() + timeLeft * 1000;
            localStorage.setItem("heartExpiration", expirationTimestamp);
        } else {
            expirationTimestamp = parseInt(expirationTimestamp);
        }
    
        function updateTimer() {
            let currentTime = Date.now();
            let remainingTime = Math.floor((expirationTimestamp - currentTime) / 1000);
    
            if (remainingTime > 0) {
                let minutes = Math.floor(remainingTime / 60);
                let seconds = remainingTime % 60;
                timerElement.innerText = `Next heart in: ${minutes}m ${seconds}s`;
    
                // Use requestAnimationFrame for smooth updates instead of setTimeout
                requestAnimationFrame(updateTimer);
            } else {
                localStorage.removeItem("heartExpiration"); // Clear storage when countdown ends
                fetchHearts(); // Refresh hearts
            }
        }
    
        updateTimer();
    }
    

    // setInterval(fetchHearts, 5000);

    document.querySelectorAll(".dropdown-content a").forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const selectedLang = this.innerText.trim().split(" ")[1];
            updateLanguage(selectedLang);
        });
    });
});
