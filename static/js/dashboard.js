document.addEventListener("DOMContentLoaded", function () {
    // DOM Elements
    const languageBtn = document.querySelector(".language-btn");
    const languageDropdown = document.querySelector(".language-dropdown");
    const lessonContainer = document.querySelector(".lessons-path");
    const heartsContainer = document.querySelector(".hearts-container"); // Get container
    const heartsDisplay = document.querySelector(".hearts-display .hearts-count");
    const heartTimerText = document.querySelector(".heart-timer .timer-text"); // Target the text span
    const profileMenu = document.querySelector(".profile-menu");
    const profileDropdown = document.querySelector(".profile-dropdown");
    const profileIcon = document.querySelector(".profile-icon"); // Get profile icon too

    // --- Declare countdownInterval in the outer scope ---
    let countdownInterval = null;

    // Initialize
    let selectedLanguage = localStorage.getItem("selectedLanguage") || "Spanish";

    // --- Define getFlag function ---
    function getFlag(language) {
        const flags = {
            "French": "🇫🇷",
            "Spanish": "🇪🇸",
            "German": "🇩🇪",
            "Japanese": "🇯🇵"
        };
        return flags[language] || "🌐"; // Default flag
    }

    // --- Define showErrorToast function ---
    function showErrorToast(message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'error-toast show'; // Add classes for styling and initial visibility
        toast.textContent = message;

        // Append to body
        document.body.appendChild(toast);

        // Automatically remove after a delay
        setTimeout(() => {
            toast.classList.remove('show'); // Start fade out
            // Remove from DOM after fade out transition completes
            setTimeout(() => {
                if (toast.parentNode) { // Check if it hasn't been removed already
                    toast.parentNode.removeChild(toast);
                }
            }, 500); // Match this duration to your CSS transition time
        }, 3000); // Display duration (3 seconds)

        /* Add basic CSS for .error-toast in your dashboard.css:
        .error-toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #dc3545; // Red background
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 1050; // Ensure it's above other elements
            opacity: 0;
            transition: opacity 0.5s ease;
            white-space: nowrap; // Prevent wrapping on small screens if needed
        }
        .error-toast.show {
            opacity: 1;
        }
        */
    }


    // --- Now continue with the rest of the initialization and functions ---

    updateLanguageDisplay(selectedLanguage); // Update display first
    fetchLessons(selectedLanguage); // Fetch lessons for the initial language

    // Initialize Hearts from HTML data attributes
    if (heartsContainer) {
        const initialHearts = parseInt(heartsContainer.getAttribute('data-initial-hearts'), 10);
        const initialTimeLeft = parseInt(heartsContainer.getAttribute('data-initial-time-left'), 10);
        if (heartsDisplay) {
            heartsDisplay.textContent = `x${initialHearts}`;
        }
        if (initialHearts < 5 && initialTimeLeft > 0) {
            const expiration = localStorage.getItem("heartExpiration");
            if (expiration) {
                const remaining = Math.max(0, Math.floor((parseInt(expiration) - Date.now()) / 1000));
                if (remaining > 0) {
                    startHeartCountdown(remaining); // Safe to call now
                } else {
                    localStorage.removeItem("heartExpiration");
                    startHeartCountdown(initialTimeLeft); // Safe to call now
                }
            } else {
                startHeartCountdown(initialTimeLeft); // Safe to call now
            }
        } else {
            if (heartTimerText) heartTimerText.textContent = '';
             if (document.getElementById('heart-timer')) {
                 document.getElementById('heart-timer').style.display = 'none';
             }
        }
    } else {
         fetchHearts(); // Fallback
    }


    // Update language display (without fetching lessons yet)
    function updateLanguageDisplay(language) {
         localStorage.setItem("selectedLanguage", language);
         const flagIcon = languageBtn.querySelector(".flag-icon");
         const languageName = languageBtn.querySelector(".language-name");

         flagIcon.textContent = getFlag(language); // Use the defined function
         languageName.textContent = language;
    }


    // Update language display AND fetch lessons
    function switchLanguage(language) {
        updateLanguageDisplay(language);
        fetchLessons(language);
    }


    // Fetch lessons for selected language (with logging)
    function fetchLessons(language) {
        console.log(`Fetching lessons for: ${language}`);
        if (lessonContainer) lessonContainer.innerHTML = '<p><i>Loading lessons...</i></p>';

        fetch(`/dashboard?lang=${language}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(response => {
            console.log("Fetch response received, status:", response.status);
            if (!response.ok) {
                return response.text().then(text => {
                    console.error("Fetch error response text:", text);
                    throw new Error(`HTTP error! status: ${response.status}, message: ${text}`);
                });
            }
            console.log("Response OK, attempting to parse JSON...");
            return response.json();
        })
        .then(data => {
            console.log("JSON parsed successfully:", data);
            if (!data || typeof data !== 'object') {
                 throw new Error("Received invalid data structure from server.");
            }
            if (data.lessons === undefined || data.completed === undefined || data.hearts === undefined || data.time_left === undefined) {
                 console.error("Data received is missing expected keys:", data);
                 throw new Error("Incomplete data received from server.");
            }

            console.log("Calling renderLessons and updateHeartsDisplay...");
            renderLessons(data.lessons, data.completed, data.hearts);
            updateHeartsDisplay(data.hearts, data.time_left); // This calls startHeartCountdown if needed
            console.log("Rendering complete.");
        })
        .catch(error => {
            console.error("Error caught in fetchLessons chain:", error);
            showErrorToast(`Failed to load lessons: ${error.message}`); // Use the defined function
            if(lessonContainer) lessonContainer.innerHTML = '<p class="text-danger">Could not load lessons. Check console for details.</p>';
        });
    }

    // Render lessons to the DOM
    function renderLessons(lessons, completedLessons = [], currentHearts = 0) {
        if (!lessonContainer) return;
        lessonContainer.innerHTML = '';

         if (!lessons || lessons.length === 0) {
             lessonContainer.innerHTML = '<p>No lessons available for this language yet.</p>';
             return;
         }

        lessons.forEach((lesson, index) => {
             const isCompleted = completedLessons.includes(lesson.lesson);
             const isLocked = (lesson.lesson > 1 && !completedLessons.includes(lesson.lesson - 1)) || currentHearts === 0;
             const isClickable = !isLocked;

             const lessonNode = document.createElement('div');
             lessonNode.className = `path-node ${isCompleted ? 'completed' : ''} ${isLocked ? 'locked' : ''}`;

             const lessonElement = document.createElement(isClickable ? 'a' : 'div');
             lessonElement.className = 'lesson-card';
             if (isClickable) {
                lessonElement.href = `/lesson/${lesson.lesson}?lang=${selectedLanguage}`;
             } else if (isLocked && currentHearts === 0 && !isCompleted) {
                  lessonElement.title = "You need hearts to start a lesson!";
             } else if (isLocked && !isCompleted) {
                  lessonElement.title = "Complete the previous lesson first!";
             }

             const lessonIcon = document.createElement('div');
             lessonIcon.className = 'lesson-icon';
             if (isCompleted) {
                lessonIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
             } else if (isLocked) {
                lessonIcon.innerHTML = '<i class="fas fa-lock"></i>';
             } else {
                const span = document.createElement('span');
                span.textContent = lesson.lesson;
                lessonIcon.appendChild(span);
             }

             const lessonTitle = document.createElement('h3');
             lessonTitle.className = 'lesson-title';
             lessonTitle.textContent = lesson.title;

             const lessonXP = document.createElement('div');
             lessonXP.className = 'lesson-xp';
             lessonXP.innerHTML = `<i class="fas fa-star"></i> ${lesson.xp || '??'} XP`; // Default if xp missing

             lessonElement.appendChild(lessonIcon);
             lessonElement.appendChild(lessonTitle);
             lessonElement.appendChild(lessonXP);

             lessonNode.appendChild(lessonElement);
             lessonContainer.appendChild(lessonNode);

             if (index < lessons.length - 1) {
                const connector = document.createElement('div');
                connector.className = `path-connector ${isCompleted ? 'completed' : ''}`;
                lessonContainer.appendChild(connector);
             }
        });
    }

    // Fetch hearts data
    function fetchHearts() {
        fetch(`/get_hearts`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
             console.log("fetchHearts received:", data);
            updateHeartsDisplay(data.hearts, data.time_left);
        })
        .catch(error => {
            console.error("Error fetching hearts:", error);
            // Consider showing toast here too if important
            // showErrorToast("Could not refresh heart count.");
        });
    }

    // Update hearts display and start timer if needed (Corrected Logic)
    function updateHeartsDisplay(hearts, timeLeft) {
         console.log(`Updating hearts: ${hearts}, Time left: ${timeLeft}`);
        if (heartsDisplay) {
            heartsDisplay.textContent = `x${hearts}`;
        }

        const heartTimerContainer = document.getElementById('heart-timer');
        if (!heartTimerContainer || !heartTimerText) return;

        if (hearts < 5 && timeLeft > 0) {
             heartTimerContainer.style.display = 'flex';
             const currentEndTime = parseInt(localStorage.getItem("heartExpiration") || '0', 10);
             const expectedEndTime = Date.now() + timeLeft * 1000;

             // Check if timer needs starting/restarting
             if (Math.abs(currentEndTime - expectedEndTime) > 5000 || !countdownInterval) {
                  console.log("Starting/Restarting countdown.");
                  startHeartCountdown(timeLeft);
             } else {
                  console.log("Countdown already running and is recent.");
             }

        } else {
             console.log("Clearing countdown interval and hiding timer.");
             if (countdownInterval) {
                  clearInterval(countdownInterval);
                  countdownInterval = null;
             }
             localStorage.removeItem("heartExpiration");
             if (heartTimerText) heartTimerText.textContent = '';
             heartTimerContainer.style.display = 'none';
        }
    }


    // Heart countdown timer (Corrected Logic)
    function startHeartCountdown(durationSeconds) {
        console.log("startHeartCountdown called with duration:", durationSeconds);

        // Clear existing interval using the outer scope variable
        if (countdownInterval) {
             console.log("Clearing existing interval ID:", countdownInterval);
            clearInterval(countdownInterval);
             countdownInterval = null;
        }

        if (durationSeconds <= 0) {
             if (heartTimerText) heartTimerText.textContent = '';
              if (document.getElementById('heart-timer')) document.getElementById('heart-timer').style.display = 'none';
             return;
        }

        let endTime = Date.now() + durationSeconds * 1000;
        localStorage.setItem("heartExpiration", endTime);

         const timerContainer = document.getElementById('heart-timer');
         if (timerContainer) {
              timerContainer.style.display = 'flex';
         }

        function updateCountdown() {
            const now = Date.now();
            const remaining = Math.max(0, Math.floor((endTime - now) / 1000));

            if (heartTimerText) {
                 if (remaining <= 0) {
                     heartTimerText.textContent = '00:00';
                     // Clear the interval using the outer scope variable
                     if (countdownInterval) {
                          clearInterval(countdownInterval);
                          countdownInterval = null;
                     }
                     localStorage.removeItem("heartExpiration");
                     console.log("Timer finished naturally, fetching hearts...");
                     fetchHearts(); // Refresh state only when timer ends
                     return;
                 }

                 const minutes = Math.floor(remaining / 60);
                 const seconds = remaining % 60;
                 heartTimerText.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
             } else {
                   // Element not found, ensure timer stops
                   if (countdownInterval) {
                        clearInterval(countdownInterval);
                        countdownInterval = null;
                        localStorage.removeItem("heartExpiration");
                   }
             }
        }

        updateCountdown(); // Run immediately
        // Assign interval ID to the outer scope variable (NO let/const)
        countdownInterval = setInterval(updateCountdown, 1000);
        console.log("Set new interval ID:", countdownInterval);
    }

    // Check for existing timer on page load (Corrected Logic)
    function checkExistingTimer() {
        const expiration = localStorage.getItem("heartExpiration");
        if (expiration) {
            const remaining = Math.max(0, Math.floor((parseInt(expiration) - Date.now()) / 1000));
            console.log(`Existing timer check. Remaining: ${remaining}`);
            if (remaining > 0) {
                const minutes = Math.floor(remaining / 60);
                const seconds = remaining % 60;
                if(heartTimerText) heartTimerText.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                 if (document.getElementById('heart-timer')) document.getElementById('heart-timer').style.display = 'flex';
                startHeartCountdown(remaining); // Restart timer correctly
            } else {
                console.log("Stored timer expired. Removing expiration.");
                localStorage.removeItem("heartExpiration");
                 if (heartTimerText) heartTimerText.textContent = '';
                  const timerContainer = document.getElementById('heart-timer');
                  if (timerContainer) timerContainer.style.display = 'none';
                 fetchHearts(); // Fetch fresh status if expired on load
            }
        } else {
             console.log("No existing timer found in localStorage.");
              // Ensure timer is hidden if no timer running and hearts might be full
              if (heartsContainer) {
                   const initialHearts = parseInt(heartsContainer.getAttribute('data-initial-hearts'), 10);
                   if (initialHearts >= 5) {
                        const timerContainer = document.getElementById('heart-timer');
                        if (timerContainer) timerContainer.style.display = 'none';
                   }
              }
        }
    }


    // Event Listeners
    document.querySelectorAll(".language-option").forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const selectedLang = this.getAttribute('data-lang');
            switchLanguage(selectedLang);
            if (languageDropdown) languageDropdown.style.display = 'none';
        });
    });

    if (languageBtn) {
        languageBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            if (languageDropdown) {
                const isDisplayed = languageDropdown.style.display === "block";
                languageDropdown.style.display = isDisplayed ? "none" : "block";
                if (!isDisplayed && profileDropdown && profileDropdown.style.display === "block") {
                    profileDropdown.style.display = "none";
                }
            }
        });
    }

    if (profileIcon) { // Check if profileIcon exists
        profileIcon.addEventListener("click", function(e) {
            e.stopPropagation();
            if (profileDropdown) {
                const isDisplayed = profileDropdown.style.display === "block";
                profileDropdown.style.display = isDisplayed ? "none" : "block";
                if (!isDisplayed && languageDropdown && languageDropdown.style.display === "block") {
                    languageDropdown.style.display = "none";
                }
            }
        });
    }

    // Close dropdowns if clicking outside
    document.addEventListener("click", function(e) {
        // Close language dropdown
        if (languageDropdown && languageDropdown.style.display === "block" && !languageBtn?.contains(e.target) && !languageDropdown.contains(e.target)) {
            languageDropdown.style.display = "none";
        }
        // Close profile dropdown
        if (profileDropdown && profileDropdown.style.display === "block" && !profileIcon?.contains(e.target) && !profileDropdown.contains(e.target)) {
            profileDropdown.style.display = "none";
        }
    });

    // Check existing timer on initial load *after* setting up initial display
    checkExistingTimer();

}); // End DOMContentLoaded