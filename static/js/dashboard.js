document.addEventListener("DOMContentLoaded", function () {
    const languageDropdown = document.querySelector(".dropbtn");
    const lessonContainer = document.getElementById("lesson-container");

    // Load selected language from localStorage or default to Spanish
    let selectedLanguage = localStorage.getItem("selectedLanguage") || "Spanish";
    updateLanguage(selectedLanguage);

    function updateLanguage(language) {
        localStorage.setItem("selectedLanguage", language); // Save selection in localStorage
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
                data.lessons.forEach(lesson => {
                    const lessonLink = document.createElement("a");
                    lessonLink.href = `/lesson/${lesson.lesson}?lang=${language}`;
                    lessonLink.classList.add("lesson-link");

                    const lessonDiv = document.createElement("div");
                    lessonDiv.classList.add("lesson");

                    const progressCircle = document.createElement("div");
                    progressCircle.classList.add("progress-circle");
                    progressCircle.innerText = lesson.lesson;

                    const lessonTitle = document.createElement("p");
                    lessonTitle.innerText = lesson.title;

                    lessonDiv.appendChild(progressCircle);
                    lessonDiv.appendChild(lessonTitle);
                    lessonLink.appendChild(lessonDiv);
                    lessonContainer.appendChild(lessonLink);
                });
            })
            .catch(error => console.error("Error fetching lessons:", error));
    }

    // Attach event listeners to language dropdown options
    document.querySelectorAll(".dropdown-content a").forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const selectedLang = this.innerText.trim().split(" ")[1]; // Extract language
            updateLanguage(selectedLang);
        });
    });
});
