document.addEventListener("DOMContentLoaded", function() {
    console.log("Dashboard Loaded");

    document.querySelectorAll(".lesson-link").forEach(button => {
        button.addEventListener("click", function() {
            alert("Opening Lesson: " + this.dataset.lesson);
        });
    });
});
