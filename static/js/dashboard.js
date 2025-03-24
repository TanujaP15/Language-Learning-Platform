document.addEventListener("DOMContentLoaded", function () {
    const languageDropdown = document.querySelector(".dropbtn");
    const lessonContainer = document.getElementById("lesson-container");

    function changeLanguage(language) {
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

    function goToLesson(lessonId) {
        const selectedLanguage = languageDropdown.innerText.trim().split(" ")[1]; 
        window.location.href = `/lesson/${lessonId}?lang=${selectedLanguage}`;
    }

    function fetchLessons(language) {
        fetch(`/dashboard?lang=${language}`)
            .then(response => response.json())
            .then(data => {
                lessonContainer.innerHTML = "";
                data.lessons.forEach(lesson => {
                    const lessonDiv = document.createElement("div");
                    lessonDiv.classList.add("lesson");
                    lessonDiv.onclick = () => goToLesson(lesson.lesson);

                    const progressCircle = document.createElement("div");
                    progressCircle.classList.add("progress-circle");
                    progressCircle.innerText = lesson.lesson;

                    const lessonTitle = document.createElement("p");
                    lessonTitle.innerText = lesson.title;

                    lessonDiv.appendChild(progressCircle);
                    lessonDiv.appendChild(lessonTitle);
                    lessonContainer.appendChild(lessonDiv);
                });
            });
    }

    // Default language is Spanish
    changeLanguage("Spanish");
});
