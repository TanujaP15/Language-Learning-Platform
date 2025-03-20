// Change Language Function
function changeLanguage(language) {
    document.querySelector(".dropbtn").innerHTML = getFlag(language) + " " + language;
}

// Helper to Get Flag Emoji
function getFlag(language) {
    const flags = {
        "French": "🇫🇷",
        "Spanish": "🇪🇸",
        "German": "🇩🇪",
        "Japanese": "🇯🇵"
    };
    return flags[language] || "🌐";
}

// Redirect to Lesson Page
function goToLesson(lessonId) {
    window.location.href = `/lesson/${lessonId}`;
}
