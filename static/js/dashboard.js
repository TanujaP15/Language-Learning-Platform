document.addEventListener("DOMContentLoaded", function () {
    const languageDropdown = document.querySelector(".dropbtn");
    const lessonContainer = document.getElementById("lesson-container");

    let selectedLanguage = localStorage.getItem("selectedLanguage") || "Spanish";

    updateLanguage(selectedLanguage);

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
                let completedLessons = data.completed || [];  // Fetch completed lessons from Flask

                data.lessons.forEach((lesson, index) => {
                    const lessonLink = document.createElement("a");
                    lessonLink.href = `/lesson/${lesson.lesson}?lang=${language}`;
                    lessonLink.classList.add("lesson-card");

                    // Lock lessons if previous lesson is not completed
                    if (!completedLessons.includes(lesson.lesson - 1) && lesson.lesson > 1) {
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

    document.querySelectorAll(".dropdown-content a").forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const selectedLang = this.innerText.trim().split(" ")[1];
            updateLanguage(selectedLang);
        });
    });
});
