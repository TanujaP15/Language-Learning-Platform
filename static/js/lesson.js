// static/js/lesson.js
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const questionInstruction = document.getElementById('question-instruction');
    const questionText = document.getElementById('question-text');
    const answerInputArea = document.getElementById('answer-input-area');
    const checkButton = document.getElementById('check-button');
    const continueButton = document.getElementById('continue-button');
    const feedbackArea = document.getElementById('feedback-area');
    const progressBar = document.getElementById('progress-bar');
    const heartsCountSpan = document.getElementById('hearts-count');
    const lessonTitleDisplay = document.getElementById('lesson-title-display');

    // --- State Variables ---
    let originalQuestions = []; // Store the initial list loaded from lessonData
    let questionsToAsk = [];    // The current pool of questions (initial or review)
    let currentQuestionIndex = 0;
    let currentHearts = 0;
    let lessonId = null;
    let language = '';
    let mistakeMadeOnCurrent = false; // Prevents losing multiple hearts on same question instance

    // --- State for Review Mode ---
    let incorrectlyAnsweredIndices = new Set(); // Store *original* indices of wrong answers in the current pass
    let inReviewMode = false;                // Flag for review rounds
    let reviewRoundCount = 0;                // Counter for review rounds (optional)

    // --- State for Matching Questions ---
    let matchCol1Selected = null; // Reference to the selected DOM element in column 1
    let userMatchedPairs = {};    // Stores user's confirmed matches {col1Value: col2Value} for the current question
    let itemsToMatchCount = 0;    // Total number of pairs for the current matching question

    // --- Initialization ---
    function initLesson() {
        // Load essential data from global variables set in lesson.html
        if (typeof lessonData !== 'undefined' && lessonData && lessonData.questions) {
            originalQuestions = lessonData.questions.map((q, index) => ({ ...q, originalIndex: index })); // Add original index
            questionsToAsk = [...originalQuestions]; // Start with all questions
            lessonId = lessonData.lesson;
            lessonTitleDisplay.textContent = lessonData.title;
        } else {
            console.error("Lesson data not found or invalid.");
            showError("Could not load lesson questions.");
            return; // Stop initialization
        }

        language = (typeof currentLanguage !== 'undefined') ? currentLanguage : 'Spanish'; // Default language
        currentHearts = (typeof initialHearts !== 'undefined') ? initialHearts : 0; // Default hearts

        updateHeartsDisplay();

        // Check if user can start the lesson
        if (currentHearts <= 0) {
            showError("You have no hearts left to start!", false); // Non-fatal error message
            // Disable interaction buttons if no hearts
            if(checkButton) checkButton.disabled = true;
            if(continueButton) continueButton.style.display = 'none';
            return; // Don't display first question if no hearts
        }

        if (questionsToAsk.length > 0) {
            displayQuestion(); // Display the first question
        } else {
            showError("No questions available in this lesson.");
        }

        // Attach event listeners
        if(checkButton) checkButton.addEventListener('click', handleCheckAnswer);
        if(continueButton) continueButton.addEventListener('click', handleContinue);
        // Enter key listener for text inputs
        answerInputArea.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'text') {
                if (!checkButton.disabled && checkButton.style.display !== 'none') {
                    handleCheckAnswer();
                }
            }
        });
    }

    // --- Display Logic ---
    function displayQuestion() {
        if (currentQuestionIndex >= questionsToAsk.length) {
            console.warn("DisplayQuestion called beyond current pool bounds.");
            handleEndOfPool(); // Trigger end-of-pool logic if this happens unexpectedly
            return;
        }

        const question = questionsToAsk[currentQuestionIndex];
        mistakeMadeOnCurrent = false; // Reset for new question instance

        // Reset state for new question display
        resetUIForNewQuestion();

        // Reset matching-specific state
        matchCol1Selected = null;
        userMatchedPairs = {};
        itemsToMatchCount = 0;

        // Set question text and instruction
        questionInstruction.textContent = getInstruction(question.type, inReviewMode);
        questionText.textContent = question.question || ''; // Display main text if available

        // Create input area based on type
        switch (question.type) {
            case 'translation':
            case 'sentence_transformation':
                createTextInput();
                break;
            case 'multiple_choice':
                createMultipleChoice(question.options);
                break;
            case 'fill_in_blank':
                 // FIB modifies questionText, ensure it's cleared before call if needed
                 questionText.textContent = ''; // Clear question text before creating FIB
                createFillInBlank(question.question);
                break;
            case 'matching':
                itemsToMatchCount = Object.keys(question.pairs || {}).length; // Get count safely
                createMatchingUI(question.pairs || {}); // Pass empty object if pairs missing
                break;
            default:
                questionInstruction.textContent = 'Error:';
                questionText.textContent = `Unsupported question type: ${question.type}`;
                // Disable interaction if type is unknown
                if(checkButton) checkButton.disabled = true;
        }

        // Focus appropriate input element
        focusFirstInput();

        updateProgress(); // Update progress bar
    }

    // --- Helper to reset UI elements before displaying next question ---
    function resetUIForNewQuestion() {
        if(answerInputArea) answerInputArea.innerHTML = ''; // Clear previous inputs/options
        if(feedbackArea) {
            feedbackArea.innerHTML = '';
            feedbackArea.className = 'feedback'; // Reset feedback classes
            feedbackArea.classList.remove('visible');
        }
        if(checkButton) {
            checkButton.disabled = true; // Usually disable initially, enable on input/selection
            checkButton.style.display = 'block'; // Show check button
        }
        if(continueButton) continueButton.style.display = 'none'; // Hide continue button
    }

    // --- Helper to focus the first available input ---
    function focusFirstInput() {
        // Prioritize inputs not of type radio, then check inside questionText (for FIB)
        const firstInput = answerInputArea.querySelector('input:not([type="radio"])') ||
                           (questionText && questionText.querySelector('input'));
        if (firstInput) {
            firstInput.focus();
        }
    }

    // --- Get Default Instruction Text ---
    function getInstruction(type, isReview = false) {
         const prefix = isReview ? 'Review: ' : '';
         switch (type) {
            case 'translation': return prefix + 'Translate this word/phrase:';
            case 'multiple_choice': return prefix + 'Select the correct option:';
            case 'fill_in_blank': return prefix + 'Fill in the blank:';
            case 'matching': return prefix + 'Match the pairs:';
            case 'sentence_transformation': return prefix + 'Translate this sentence:';
            default: return 'Question:';
         }
    }

    // --- Input Creation Functions ---
    function createTextInput(placeholder = "Type your answer here") {
        const input = document.createElement('input');
        input.type = 'text';
        input.id = 'text-answer';
        input.placeholder = placeholder;
        input.autocomplete = 'off';
        input.autocapitalize = 'none';
        input.classList.add('form-control', 'form-control-lg');
        answerInputArea.appendChild(input);
        // Enable check button when user types something
        input.addEventListener('input', () => {
            if(checkButton) checkButton.disabled = input.value.trim() === '';
        });
        if(checkButton) checkButton.disabled = true; // Initially disabled
    }

    function createFillInBlank(questionString) {
        const parts = questionString.split('____');
        // questionText is already cleared by resetUIForNewQuestion or displayQuestion
        let inputField = null;

        parts.forEach((part, index) => {
            questionText.appendChild(document.createTextNode(part));
            if (index < parts.length - 1) {
                inputField = document.createElement('input');
                inputField.type = 'text';
                inputField.id = 'text-answer'; // Use consistent ID
                inputField.classList.add('fill-blank-input');
                inputField.maxLength = 25;
                inputField.autocomplete = 'off';
                inputField.autocapitalize = 'none';
                inputField.style.width = '120px'; // Example styling
                questionText.appendChild(inputField);
            }
        });

        answerInputArea.innerHTML = ''; // No separate input area needed

        if (inputField && checkButton) {
             inputField.addEventListener('input', () => {
                 checkButton.disabled = inputField.value.trim() === '';
             });
             checkButton.disabled = true; // Initially disabled
        } else if (checkButton) {
             checkButton.disabled = true; // Disable if no input created
        }
    }

    function createMultipleChoice(options) {
        if (!options || options.length === 0) {
            answerInputArea.textContent = "Error: No options provided.";
             if(checkButton) checkButton.disabled = true;
            return;
        }
        options.forEach((option, index) => {
            const div = document.createElement('div');
            div.classList.add('mc-option');

            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'mc-answer';
            radio.value = option;
            radio.id = `option-${index}`;
            radio.classList.add('form-check-input');

            const label = document.createElement('label');
            label.htmlFor = `option-${index}`;
            label.appendChild(document.createTextNode(option));
            label.classList.add('form-check-label');

            div.appendChild(radio);
            div.appendChild(label);

            div.addEventListener('click', () => {
                if (!radio.checked) { radio.checked = true; }
                // Visually update selection
                document.querySelectorAll('.mc-option').forEach(el => el.classList.remove('selected'));
                div.classList.add('selected');
                // Enable check button since an option is now selected
                if(checkButton) checkButton.disabled = false;
            });

            answerInputArea.appendChild(div);
        });
         if(checkButton) checkButton.disabled = true; // Initially disabled until selection
    }

    function createMatchingUI(pairs) {
        if (!pairs || Object.keys(pairs).length === 0) {
             answerInputArea.textContent = "Error: No matching pairs provided.";
             if(checkButton) checkButton.disabled = true;
             return;
        }
        const keys = Object.keys(pairs);
        const values = Object.values(pairs);

        // Shuffle function
        function shuffle(array) { /* ... (same shuffle logic) ... */
              for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        }
        const shuffledValues = shuffle([...values]);

        const container = document.createElement('div');
        container.className = 'matching-container';
        const col1Div = document.createElement('div');
        col1Div.className = 'match-column'; col1Div.id = 'match-col-1';
        const col2Div = document.createElement('div');
        col2Div.className = 'match-column'; col2Div.id = 'match-col-2';

        // Create items and add listeners
        const createItem = (text, value, columnId) => {
            const item = document.createElement('button');
            item.className = 'match-item btn'; // Add btn class for basic styling/focus
            item.textContent = text;
            item.dataset.value = value;
            item.dataset.column = columnId;
            item.addEventListener('click', handleMatchItemClick);
            return item;
        };

        keys.forEach(key => col1Div.appendChild(createItem(key, key, '1')));
        shuffledValues.forEach(value => col2Div.appendChild(createItem(value, value, '2')));

        container.appendChild(col1Div);
        container.appendChild(col2Div);
        answerInputArea.appendChild(container);

        if(checkButton) checkButton.disabled = true; // Disabled until all pairs are matched
    }

    // --- Matching Click Handler ---
    function handleMatchItemClick(event) {
        const clickedItem = event.target;
        const column = clickedItem.dataset.column;
        const value = clickedItem.dataset.value;

        if (clickedItem.classList.contains('paired')) {
            // --- Unmatch Logic ---
            let keyToRemove = null;
            let valuePaired = null;

            // Find which pair this item belongs to
            if (column === '1') {
                keyToRemove = value;
                valuePaired = userMatchedPairs[keyToRemove];
            } else { // Clicked in column 2
                for (const key in userMatchedPairs) {
                    if (userMatchedPairs[key] === value) {
                        keyToRemove = key;
                        valuePaired = value;
                        break;
                    }
                }
            }

            if (keyToRemove !== null && valuePaired !== null) {
                delete userMatchedPairs[keyToRemove]; // Remove track

                // Find DOM elements
                const item1 = answerInputArea.querySelector(`#match-col-1 .match-item[data-value="${keyToRemove}"]`);
                const item2 = answerInputArea.querySelector(`#match-col-2 .match-item[data-value="${valuePaired}"]`);

                // Reset styles and enable
                if(item1) { item1.classList.remove('paired', 'selected'); item1.disabled = false; }
                if(item2) { item2.classList.remove('paired', 'selected'); item2.disabled = false; }

                console.log("Unmatched:", keyToRemove, valuePaired);
            }
            // Reset selections and disable check
            if(matchCol1Selected) matchCol1Selected.classList.remove('selected');
            matchCol1Selected = null;
            if(checkButton) checkButton.disabled = true;

        } else if (column === '1') {
            // --- Select in Column 1 ---
            if (matchCol1Selected && matchCol1Selected !== clickedItem) {
                matchCol1Selected.classList.remove('selected'); // Deselect previous
            }
            clickedItem.classList.toggle('selected'); // Toggle current
            matchCol1Selected = clickedItem.classList.contains('selected') ? clickedItem : null;

        } else if (column === '2') {
            // --- Select in Column 2 (Attempt Pair) ---
            if (matchCol1Selected) { // Can only pair if col 1 is selected
                const col1Value = matchCol1Selected.dataset.value;
                const col2Value = value; // Value of the clicked col 2 item

                // Store pair
                userMatchedPairs[col1Value] = col2Value;
                console.log("Matched Attempt:", userMatchedPairs);

                // Update UI: Mark as paired, disable, remove selection highlight
                matchCol1Selected.classList.add('paired');
                matchCol1Selected.classList.remove('selected');
                matchCol1Selected.disabled = true;

                clickedItem.classList.add('paired');
                clickedItem.disabled = true;

                // Reset col 1 selection
                matchCol1Selected = null;

                // Enable check button if all items are paired
                if (Object.keys(userMatchedPairs).length === itemsToMatchCount && checkButton) {
                    checkButton.disabled = false;
                }
            } else {
                // No selection in column 1 - maybe flash column 1 or give subtle feedback
                console.log("Select an item from the left column first.");
            }
        }
    }

    // --- Event Handlers ---
    function handleCheckAnswer() {
        // Allow checking even with 0 hearts if a mistake was *already* made on this question instance
        if (currentHearts <= 0 && !mistakeMadeOnCurrent) {
            showFeedback("You are out of hearts!", "incorrect");
            return;
        }

        const question = questionsToAsk[currentQuestionIndex];
        const originalIndex = question.originalIndex; // Get original index stored earlier
        let isOverallCorrect = false; // Assume incorrect initially

        // Disable check button immediately to prevent double clicks
        if(checkButton) checkButton.disabled = true;

        if (question.type === 'matching') {
            // --- Matching Check Logic ---
            const correctPairs = question.pairs;
            let correctMatchesCount = 0;
            isOverallCorrect = true; // Assume correct until a mismatch is found

            // Disable further interaction with matching items
            answerInputArea.querySelectorAll('.match-item').forEach(item => item.disabled = true);

            for (const key in userMatchedPairs) {
                const userValue = userMatchedPairs[key];
                const correctValue = correctPairs[key];

                const item1 = answerInputArea.querySelector(`#match-col-1 .match-item[data-value="${key}"]`);
                const item2 = answerInputArea.querySelector(`#match-col-2 .match-item[data-value="${userValue}"]`);

                if (userValue === correctValue) {
                    correctMatchesCount++;
                    if(item1) item1.classList.add('correct-pair');
                    if(item2) item2.classList.add('correct-pair');
                } else {
                    isOverallCorrect = false; // Mark overall as incorrect
                    if(item1) item1.classList.add('incorrect-pair');
                    if(item2) item2.classList.add('incorrect-pair');
                }
            }
            // Provide feedback specific to matching
             if (isOverallCorrect) {
                 showFeedback("All pairs matched correctly!", "correct");
             } else {
                  showFeedback(`Some pairs incorrect. (${correctMatchesCount}/${itemsToMatchCount} correct)`, "incorrect");
             }

        } else {
            // --- Check Logic for other types ---
            let userAnswer = getUserAnswer(question.type);
            const correctAnswer = question.answer;

            // Normalize strings for comparison
            let normalizedUserAnswer = userAnswer;
            let normalizedCorrectAnswer = correctAnswer;
            if (typeof userAnswer === 'string') normalizedUserAnswer = userAnswer.trim().toLowerCase();
            if (typeof correctAnswer === 'string') normalizedCorrectAnswer = correctAnswer.trim().toLowerCase();

            isOverallCorrect = (normalizedUserAnswer !== null && normalizedUserAnswer === normalizedCorrectAnswer);

             // Provide feedback for non-matching types
             if (isOverallCorrect) {
                showFeedback("Correct!", "correct");
             } else {
                 showFeedback(`Incorrect. Correct answer: ${correctAnswer}`, "incorrect");
             }
              // Style inputs for non-matching types
              styleInputFeedback(question.type, isOverallCorrect);
        } // End check logic branching

        // --- Common Actions After Checking ---
        if (isOverallCorrect) {
            // If in review mode and answered correctly, remove from the set for the *next* round
            if (inReviewMode) {
                incorrectlyAnsweredIndices.delete(originalIndex);
            }
        } else {
            // If incorrect, add the original index to the set for the review round
            incorrectlyAnsweredIndices.add(originalIndex);
            // Deduct heart only if it's the first mistake on this specific question instance
            if (!mistakeMadeOnCurrent) {
                loseHeart();
                mistakeMadeOnCurrent = true;
            }
        }

        // Hide check, show continue, focus continue
        if(checkButton) checkButton.style.display = 'none';
        if(continueButton) {
             continueButton.style.display = 'block';
             continueButton.focus();
        }

    } // End handleCheckAnswer

    function handleContinue() {
        currentQuestionIndex++; // Advance index within the current pool
        if (currentQuestionIndex < questionsToAsk.length) {
            displayQuestion(); // Display next question in the pool
        } else {
            handleEndOfPool(); // Reached end of the current pool (initial or review)
        }
    }

    // --- Helper to shuffle arrays ---
    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
    }

    // --- End of Pool / Review Logic ---
    function handleEndOfPool() {
         if (!inReviewMode) {
             // --- End of Initial Pass ---
             if (incorrectlyAnsweredIndices.size === 0) {
                 completeLesson(); // All correct first time!
             } else {
                 // --- Start FIRST Review Mode ---
                 console.log("Starting review mode for indices:", incorrectlyAnsweredIndices);
                 inReviewMode = true;
                 reviewRoundCount = 1; // Start counting review rounds
                 // Create review pool from original questions using incorrect indices
                 questionsToAsk = Array.from(incorrectlyAnsweredIndices).map(index => originalQuestions[index]);
                 shuffleArray(questionsToAsk); // Shuffle review questions
                 incorrectlyAnsweredIndices.clear(); // Clear set to track errors *within this review round*
                 currentQuestionIndex = 0; // Reset index for the new pool
                 lessonTitleDisplay.textContent = `${lessonData.title} (Review ${reviewRoundCount})`;
                 displayQuestion();
             }
         } else {
             // --- End of a Review Pass ---
             if (incorrectlyAnsweredIndices.size === 0) {
                 // All questions in *this* review round were correct!
                 completeLesson();
             } else {
                 // --- Start ANOTHER Review Pass ---
                 reviewRoundCount++;
                 console.log(`Starting review round ${reviewRoundCount} for indices:`, incorrectlyAnsweredIndices);
                 // Incorrect indices from the completed round are already in the set.
                 questionsToAsk = Array.from(incorrectlyAnsweredIndices).map(index => originalQuestions[index]);
                 shuffleArray(questionsToAsk);
                 incorrectlyAnsweredIndices.clear(); // Clear set for the *next* round
                 currentQuestionIndex = 0;
                 lessonTitleDisplay.textContent = `${lessonData.title} (Review ${reviewRoundCount})`;
                 displayQuestion();
             }
         }
    }

    // --- Answer Retrieval ---
    function getUserAnswer(type) {
        switch (type) {
            case 'translation':
            case 'sentence_transformation':
                const textInput = answerInputArea.querySelector('#text-answer');
                return textInput ? textInput.value : '';
            case 'fill_in_blank':
                 const fibInput = questionText.querySelector('#text-answer'); // Input is inside questionText
                 return fibInput ? fibInput.value : '';
            case 'multiple_choice':
                const selectedRadio = answerInputArea.querySelector('input[name="mc-answer"]:checked');
                return selectedRadio ? selectedRadio.value : null;
            case 'matching':
                 return userMatchedPairs; // Return the object of user's attempted pairs
            default:
                console.warn(`Getting answer for unknown type: ${type}`);
                return null;
        }
    }

    // --- UI Update Functions ---
    function updateProgress() {
        // Progress reflects movement through the *current* pool (initial or review)
        const progressPercent = questionsToAsk.length > 0 ? (currentQuestionIndex / questionsToAsk.length) * 100 : 0;
        if(progressBar) progressBar.style.width = `${Math.min(100, progressPercent)}%`;
    }

    function updateHeartsDisplay() {
        if (!heartsCountSpan) return;
        heartsCountSpan.textContent = `x${currentHearts}`;
         const heartIcon = heartsCountSpan.previousElementSibling;
         if (heartIcon) {
              heartIcon.style.color = currentHearts > 0 ? '#ff4b4b' : '#adb5bd';
              // Optional: Add animation for low hearts
              heartIcon.classList.toggle('fa-beat', currentHearts === 1 && currentHearts > 0);
              heartIcon.style.animationDuration = currentHearts === 1 ? '1s' : null; // Control speed
         }
    }

    function showFeedback(message, type) { // type = 'correct' or 'incorrect'
        if(!feedbackArea) return;
        feedbackArea.textContent = message;
        feedbackArea.className = `feedback ${type}`; // Apply base and type class
        feedbackArea.classList.add('visible');      // Make visible via CSS transition
    }

    function styleInputFeedback(questionType, isCorrect) {
        const correctClass = 'correct';
        const incorrectClass = 'incorrect';

        // Helper for text/fib inputs
        const styleTextInput = (inputElement) => {
            if (inputElement) {
                inputElement.classList.remove(correctClass, incorrectClass);
                inputElement.classList.add(isCorrect ? correctClass : incorrectClass);
            }
        };

        switch (questionType) {
            case 'translation':
            case 'sentence_transformation':
                styleTextInput(answerInputArea.querySelector('#text-answer'));
                break;
            case 'fill_in_blank':
                styleTextInput(questionText.querySelector('#text-answer'));
                break;
            case 'multiple_choice':
                const radios = answerInputArea.querySelectorAll('input[name="mc-answer"]');
                radios.forEach(radio => {
                    const labelDiv = radio.closest('.mc-option'); // Get the container div
                    if (!labelDiv) return;
                    labelDiv.classList.remove(correctClass, incorrectClass); // Clear previous first
                    const question = questionsToAsk[currentQuestionIndex]; // Current question object
                    const isThisOptionCorrectAnswer = (radio.value === question.answer);

                    if (isThisOptionCorrectAnswer) {
                        labelDiv.classList.add(correctClass); // Always mark correct one green
                    }
                    if (radio.checked && !isCorrect) {
                        // User selected this, and it was wrong
                        labelDiv.classList.add(incorrectClass); // Mark user's wrong choice red
                    }
                });
                break;
            case 'matching':
                 // Matching styling is handled separately in handleCheckAnswer by adding
                 // 'correct-pair' and 'incorrect-pair' classes to the button elements.
                 break;
        }
    }

    function showError(message, isFatal = true) {
        console.error("Lesson Error:", message);
        if(questionInstruction) questionInstruction.textContent = 'Error';
        if(questionText) questionText.textContent = message;
        if(answerInputArea) answerInputArea.innerHTML = '';
        if(feedbackArea) { feedbackArea.textContent = message; feedbackArea.className = 'feedback incorrect visible'; }

        if (isFatal) { // Disable buttons on fatal errors
            if(checkButton) { checkButton.disabled = true; checkButton.style.display = 'none'; }
            if(continueButton) continueButton.style.display = 'none';
        }
        // Consider adding a "Return to Dashboard" button on error
    }

    // --- API Communication ---
    async function loseHeart() {
        if (currentHearts <= 0) return; // Safeguard

        currentHearts--;
        updateHeartsDisplay();
        console.log(`Lost a heart. Remaining: ${currentHearts}`);

        if (currentHearts <= 0) {
            // Disable interaction immediately if hearts run out
             if(checkButton) checkButton.disabled = true;
             answerInputArea.querySelectorAll('button, input').forEach(el => el.disabled = true); // Disable all inputs/buttons
             showFeedback("Oh no, you're out of hearts! Review your mistakes.", "incorrect");
             // Don't hide continue, allow user to proceed (and potentially fail review if needed)
             // but checking is blocked.
        }

        try {
            const response = await fetch('/lose_heart', { method: 'POST' });
            if (!response.ok) {
                console.error(`Server error losing heart: ${response.status} ${response.statusText}`);
                // Maybe attempt to revert UI heart count? Or show persistent error?
                // currentHearts++; updateHeartsDisplay(); // Example revert
            } else {
                 console.log("Server confirmed heart loss.");
                 // const data = await response.json(); // Process response if needed
            }
        } catch (error) {
            console.error("Network error losing heart:", error);
            // Inform user of network issue? Revert UI heart count?
            // currentHearts++; updateHeartsDisplay(); // Example revert
        }
    }

    async function completeLesson() {
        console.log("Lesson complete!");
        if(progressBar) progressBar.style.width = '100%'; // Ensure progress is full

        showFeedback("Lesson Complete!", "correct");
        if(checkButton) checkButton.style.display = 'none';
        if(continueButton) continueButton.style.display = 'none';

        try {
            const url = `/complete_lesson/${lessonId}?lang=${language}`;
            const response = await fetch(url, { method: 'POST' });

            if (response.ok) {
                const result = await response.json();
                console.log("Lesson completion acknowledged by server:", result);
                showFeedback(`Lesson Complete! +${result.xp_earned || '??'} XP`, "correct");
                setTimeout(() => {
                    window.location.href = `/dashboard?lang=${language}`;
                }, 2000); // Redirect after 2 seconds
            } else {
                console.error(`Server error completing lesson: ${response.status} ${response.statusText}`);
                showError("Could not save lesson completion. Please try again later.", false);
            }
        } catch (error) {
            console.error("Network error completing lesson:", error);
            showError("Network error saving completion. Please check your connection.", false);
        }
    }

    // --- Start the Lesson ---
    initLesson();

}); // End DOMContentLoaded