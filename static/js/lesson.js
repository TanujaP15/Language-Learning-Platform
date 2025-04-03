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
    let currentQuestionIndex = 0;
    let questions = [];
    let currentHearts = 0;
    let lessonId = null;
    let language = '';
    let mistakeMadeOnCurrent = false;

    // --- State for Matching Questions ---
    let matchCol1Selected = null; // Reference to the selected DOM element in column 1
    let matchCol2Selected = null; // Reference to the selected DOM element in column 2
    let userMatchedPairs = {};    // Stores user's confirmed matches {col1Value: col2Value}
    let itemsToMatch = 0;         // Total number of pairs for the current question

    // --- Initialization ---
    function initLesson() {
        // ... (keep existing init logic for loading data, language, hearts) ...
        if (typeof lessonData !== 'undefined' && lessonData && lessonData.questions) {
            questions = lessonData.questions;
            lessonId = lessonData.lesson;
            lessonTitleDisplay.textContent = lessonData.title; // Set title
        } else {
            console.error("Lesson data not found or invalid.");
            showError("Could not load lesson questions.");
            checkButton.disabled = true;
            return;
        }

        if (typeof currentLanguage !== 'undefined') {
            language = currentLanguage;
        } else {
            console.warn("Language not defined.");
            language = 'Spanish'; // Default fallback
        }

        if (typeof initialHearts !== 'undefined') {
            currentHearts = initialHearts;
        } else {
            console.warn("Initial hearts not defined.");
            currentHearts = 0; // Default fallback
        }

        updateHeartsDisplay();
        if (currentHearts <= 0) {
             showError("You have no hearts left to continue!", false);
             checkButton.disabled = true;
        }

        if (questions.length > 0) {
            displayQuestion();
        } else {
            console.error("No questions found for this lesson.");
            showError("No questions available in this lesson.");
            checkButton.disabled = true;
        }

        // Event Listeners (keep existing)
        checkButton.addEventListener('click', handleCheckAnswer);
        continueButton.addEventListener('click', handleContinue);
        answerInputArea.addEventListener('keypress', function(e) {
           if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'text' && !checkButton.disabled) {
                handleCheckAnswer();
           }
        });
    }

    // --- Display Logic ---
    function displayQuestion() {
        if (currentQuestionIndex >= questions.length) return;

        const question = questions[currentQuestionIndex];
        mistakeMadeOnCurrent = false;

        // Reset matching state
        matchCol1Selected = null;
        matchCol2Selected = null;
        userMatchedPairs = {};
        itemsToMatch = 0;

        // Clear previous state
        answerInputArea.innerHTML = '';
        feedbackArea.innerHTML = '';
        feedbackArea.className = 'feedback';
        feedbackArea.classList.remove('visible');
        checkButton.disabled = true; // Disable check initially for most types
        continueButton.style.display = 'none';

        // Set question text and instruction
        questionInstruction.textContent = question.instruction || getInstruction(question.type); // Use provided instruction or default
        questionText.textContent = question.question || '';

        switch (question.type) {
            case 'translation':
            case 'sentence_transformation':
                createTextInput();
                checkButton.disabled = false; // Enable check for text input
                break;
            case 'multiple_choice':
                createMultipleChoice(question.options);
                // Enable check button only when an option is selected
                answerInputArea.addEventListener('change', () => {
                     checkButton.disabled = !document.querySelector('input[name="mc-answer"]:checked');
                }, { once: true }); // Optimization: check only once needed per question
                break;
            case 'fill_in_blank':
                createFillInBlank(question.question);
                // Enable check button - user needs to type something
                const fibInput = questionText.querySelector('input');
                if(fibInput) {
                    fibInput.addEventListener('input', () => {
                        checkButton.disabled = fibInput.value.trim() === '';
                    });
                    checkButton.disabled = true; // Initially disabled
                } else {
                     checkButton.disabled = true; // Should not happen
                }
                break;
            case 'matching':
                itemsToMatch = Object.keys(question.pairs).length;
                createMatchingUI(question.pairs);
                // Check button remains disabled until all pairs are selected by the user
                break;
            default:
                questionInstruction.textContent = 'Question:'
                questionText.textContent = `Unsupported question type: ${question.type}`;
                checkButton.disabled = true;
        }

        const firstInput = answerInputArea.querySelector('input:not([type=radio])');
        if (firstInput) {
            firstInput.focus();
        }

        updateProgress();
    }

    // --- Get Default Instruction Text ---
    function getInstruction(type) {
         switch (type) {
            case 'translation': return 'Translate this word/phrase:';
            case 'multiple_choice': return 'Select the correct option:';
            case 'fill_in_blank': return 'Fill in the blank:';
            case 'matching': return 'Match the pairs:';
            case 'sentence_transformation': return 'Translate this sentence:';
            default: return 'Question:';
         }
    }


    // --- Input Creation Functions ---
    // createTextInput, createFillInBlank, createMultipleChoice remain mostly the same...
    // Ensure createFillInBlank correctly places input within questionText

    function createTextInput(placeholder = "Type your answer here") {
        const input = document.createElement('input');
        input.type = 'text';
        input.id = 'text-answer';
        input.placeholder = placeholder;
        input.autocomplete = 'off';
        input.autocapitalize = 'none';
        input.classList.add('form-control', 'form-control-lg'); // Add bootstrap classes if desired
        answerInputArea.appendChild(input);
        // Enable check button when user types something
        input.addEventListener('input', () => {
            checkButton.disabled = input.value.trim() === '';
        });
        checkButton.disabled = true; // Initially disabled
    }

    function createFillInBlank(questionString) {
        const parts = questionString.split('____');
        questionText.innerHTML = ''; // Clear text area
        let inputField; // Reference to the input

        parts.forEach((part, index) => {
            questionText.appendChild(document.createTextNode(part));
            if (index < parts.length - 1) {
                inputField = document.createElement('input');
                inputField.type = 'text';
                inputField.id = 'text-answer'; // Single input ID
                inputField.classList.add('fill-blank-input');
                inputField.maxLength = 25;
                inputField.autocomplete = 'off';
                inputField.autocapitalize = 'none';
                questionText.appendChild(inputField);
            }
        });

        answerInputArea.innerHTML = ''; // No separate input needed

        if (inputField) {
            inputField.focus();
             // Enable check button when user types something
             inputField.addEventListener('input', () => {
                 checkButton.disabled = inputField.value.trim() === '';
             });
             checkButton.disabled = true; // Initially disabled
        } else {
             checkButton.disabled = true; // Disable if no input somehow
        }
    }

    function createMultipleChoice(options) {
        options.forEach((option, index) => {
            const div = document.createElement('div'); // Use div as container for better styling control
            div.classList.add('mc-option');

            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'mc-answer';
            radio.value = option;
            radio.id = `option-${index}`;
            radio.classList.add('form-check-input'); // Optional bootstrap styling

            const label = document.createElement('label');
            label.htmlFor = `option-${index}`;
            label.appendChild(document.createTextNode(option)); // Text goes inside label
            label.classList.add('form-check-label'); // Optional bootstrap styling

            div.appendChild(radio);
            div.appendChild(label);

            // Click anywhere on the div selects the radio
            div.addEventListener('click', () => {
                if (!radio.checked) { // Only trigger if not already checked
                    radio.checked = true;
                    // Manually trigger change event for listener
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                }
                document.querySelectorAll('.mc-option').forEach(el => el.classList.remove('selected'));
                div.classList.add('selected');
            });

            answerInputArea.appendChild(div);
        });
         // Listen for changes to enable check button
         answerInputArea.addEventListener('change', (event) => {
              if (event.target.type === 'radio') {
                   checkButton.disabled = false;
              }
         });
         checkButton.disabled = true; // Initially disabled
    }

    // --- NEW: Matching UI Creation ---
    function createMatchingUI(pairs) {
        const keys = Object.keys(pairs);
        const values = Object.values(pairs);

        // Shuffle function (Fisher-Yates)
        function shuffle(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        }

        // Shuffle one or both columns - shuffling values is usually sufficient
        const shuffledValues = shuffle([...values]); // Create shuffled copy

        const container = document.createElement('div');
        container.className = 'matching-container';

        const col1Div = document.createElement('div');
        col1Div.className = 'match-column';
        col1Div.id = 'match-col-1';

        const col2Div = document.createElement('div');
        col2Div.className = 'match-column';
        col2Div.id = 'match-col-2';

        // Create items for column 1 (keys)
        keys.forEach(key => {
            const item = document.createElement('button'); // Use buttons for better accessibility
            item.className = 'match-item';
            item.textContent = key;
            item.dataset.value = key; // Store original key
            item.dataset.column = '1';
            item.addEventListener('click', handleMatchItemClick);
            col1Div.appendChild(item);
        });

        // Create items for column 2 (shuffled values)
        shuffledValues.forEach(value => {
            const item = document.createElement('button');
            item.className = 'match-item';
            item.textContent = value;
            item.dataset.value = value; // Store original value
            item.dataset.column = '2';
            item.addEventListener('click', handleMatchItemClick);
            col2Div.appendChild(item);
        });

        container.appendChild(col1Div);
        container.appendChild(col2Div);
        answerInputArea.appendChild(container);

        checkButton.disabled = true; // Disabled until all pairs are attempted
    }

    // --- NEW: Matching Click Handler ---
    function handleMatchItemClick(event) {
        const clickedItem = event.target;
        const column = clickedItem.dataset.column;

        if (clickedItem.classList.contains('paired')) {
            // --- Logic to UNMATCH a pair ---
            const valueToRemove = clickedItem.dataset.value;
            let keyToRemove = null;
            let pairedElementCol1 = null;
            let pairedElementCol2 = null;

            // Find the pair in userMatchedPairs
            for (const key in userMatchedPairs) {
                if (key === valueToRemove || userMatchedPairs[key] === valueToRemove) {
                    keyToRemove = key;
                    break;
                }
            }

            if (keyToRemove) {
                const valuePaired = userMatchedPairs[keyToRemove];
                delete userMatchedPairs[keyToRemove]; // Remove from tracked pairs

                // Find the DOM elements for this pair
                pairedElementCol1 = answerInputArea.querySelector(`#match-col-1 .match-item[data-value="${keyToRemove}"]`);
                pairedElementCol2 = answerInputArea.querySelector(`#match-col-2 .match-item[data-value="${valuePaired}"]`);

                // Remove visual pairing styles and re-enable buttons
                if (pairedElementCol1) {
                    pairedElementCol1.classList.remove('paired', 'selected');
                    pairedElementCol1.disabled = false;
                }
                if (pairedElementCol2) {
                    pairedElementCol2.classList.remove('paired', 'selected');
                    pairedElementCol2.disabled = false;
                }
                 console.log("Unmatched:", keyToRemove, valuePaired);
            }
            // Reset selections
            matchCol1Selected = null;
            matchCol2Selected = null;
            // Always disable check button when unpairing
            checkButton.disabled = true;

        } else if (column === '1') {
             // If selecting a new item in col 1, deselect any previous one
            if (matchCol1Selected && matchCol1Selected !== clickedItem) {
                matchCol1Selected.classList.remove('selected');
            }
             // Toggle selection for the clicked item
             clickedItem.classList.toggle('selected');
             matchCol1Selected = clickedItem.classList.contains('selected') ? clickedItem : null;
             matchCol2Selected = null; // Deselect column 2 when selecting column 1

        } else if (column === '2') {
            // Only allow selecting from column 2 if something is selected in column 1
            if (matchCol1Selected) {
                 // This selection completes a pair attempt
                const col1Value = matchCol1Selected.dataset.value;
                const col2Value = clickedItem.dataset.value;

                // Store the attempted pair
                userMatchedPairs[col1Value] = col2Value;
                console.log("Matched Attempt:", userMatchedPairs);


                // Visually mark as paired and disable
                matchCol1Selected.classList.add('paired');
                matchCol1Selected.classList.remove('selected'); // Remove selection highlight
                matchCol1Selected.disabled = true;

                clickedItem.classList.add('paired');
                clickedItem.disabled = true;

                // Reset selection
                matchCol1Selected = null;

                // Check if all items are now paired
                if (Object.keys(userMatchedPairs).length === itemsToMatch) {
                    checkButton.disabled = false; // Enable check button
                }
            } else {
                 // No active selection in column 1, do nothing or provide feedback
                 console.log("Select an item from the left column first.");
            }
        }
    }


    // --- Event Handlers (handleCheckAnswer needs update) ---
    function handleCheckAnswer() {
        if (currentHearts <= 0) {
            showFeedback("You are out of hearts!", "incorrect");
            return;
        }

        const question = questions[currentQuestionIndex];
        let isCorrect = false; // Overall correctness for the question

        if (question.type === 'matching') {
            // --- Matching Check Logic ---
            const correctPairs = question.pairs;
            let correctMatches = 0;
            isCorrect = true; // Assume correct initially

            // Disable all match items during check
            answerInputArea.querySelectorAll('.match-item').forEach(item => item.disabled = true);

            // Check each attempted pair
            for (const key in userMatchedPairs) {
                const userValue = userMatchedPairs[key];
                const correctValue = correctPairs[key];

                const item1 = answerInputArea.querySelector(`#match-col-1 .match-item[data-value="${key}"]`);
                const item2 = answerInputArea.querySelector(`#match-col-2 .match-item[data-value="${userValue}"]`);

                if (userValue === correctValue) {
                    correctMatches++;
                    // Style the correct pair
                    if(item1) item1.classList.add('correct-pair');
                    if(item2) item2.classList.add('correct-pair');
                } else {
                    isCorrect = false; // One wrong pair makes the whole question wrong for scoring
                    // Style the incorrect pair
                     if(item1) item1.classList.add('incorrect-pair');
                     if(item2) {
                          item2.classList.add('incorrect-pair');
                          // Optionally highlight the one they *selected* specifically
                          item2.classList.add('selected'); // Reuse 'selected' style with incorrect context
                     }
                    console.log(`Incorrect Match: ${key} -> ${userValue} (Should be: ${correctValue})`);
                }
            }

             // Provide specific feedback for matching
             if (isCorrect) {
                 showFeedback("All pairs matched correctly!", "correct");
             } else {
                  showFeedback(`Some pairs were incorrect. (${correctMatches}/${itemsToMatch} correct)`, "incorrect");
                 // Here you could optionally show the correct pairings more explicitly if needed
             }

        } else {
            // --- Check Logic for other types (Translation, MC, FIB) ---
            let userAnswer = getUserAnswer(question.type);
            const correctAnswer = question.answer;

            if (typeof userAnswer === 'string') {
                userAnswer = userAnswer.trim().toLowerCase();
            }
            if (typeof correctAnswer === 'string') {
                isCorrect = userAnswer === correctAnswer.toLowerCase();
            } else {
                isCorrect = userAnswer === correctAnswer;
            }
        } // End of check logic branching

        // --- Common Feedback/Action Logic ---
        if (isCorrect) {
            if(question.type !== 'matching') showFeedback("Correct!", "correct"); // Avoid duplicate message for matching
            styleInputFeedback(question.type, true); // Style non-matching inputs
            checkButton.disabled = true;
            continueButton.style.display = 'block';
            continueButton.focus();
        } else {
            if(question.type !== 'matching') {
                 showFeedback(`Incorrect. Correct: ${question.answer}`, "incorrect");
            }
            styleInputFeedback(question.type, false); // Style non-matching inputs

            if (!mistakeMadeOnCurrent) {
                loseHeart();
                mistakeMadeOnCurrent = true;
            }
            checkButton.disabled = true;
            continueButton.style.display = 'block'; // Allow moving on
        }
    } // End handleCheckAnswer

    function handleContinue() {
        currentQuestionIndex++;
        if (currentQuestionIndex < questions.length) {
            displayQuestion();
        } else {
            completeLesson();
        }
    }

    // --- Answer Retrieval (needs update for matching) ---
    function getUserAnswer(type) {
        switch (type) {
            case 'translation':
            case 'sentence_transformation':
                return document.getElementById('text-answer')?.value || '';
            case 'fill_in_blank':
                 const fibInput = questionText.querySelector('input#text-answer');
                 return fibInput?.value || '';
            case 'multiple_choice':
                const selectedRadio = document.querySelector('input[name="mc-answer"]:checked');
                return selectedRadio ? selectedRadio.value : null;
            case 'matching':
                 return userMatchedPairs; // Return the object of attempted pairs
            default:
                return null;
        }
    }

    // --- UI Update Functions (needs update for matching) ---
    function updateProgress() {
        // Progress increases only when moving to the *next* question
        const progressPercent = (currentQuestionIndex / questions.length) * 100;
        progressBar.style.width = `${progressPercent}%`;
    }

    function updateHeartsDisplay() {
        // ... (keep existing logic) ...
         heartsCountSpan.textContent = `x${currentHearts}`;
         const heartIcon = heartsCountSpan.previousElementSibling;
         if (heartIcon) {
              heartIcon.style.color = currentHearts > 0 ? '#ff4b4b' : '#adb5bd';
         }
    }

    function showFeedback(message, type) {
        feedbackArea.textContent = message;
        feedbackArea.className = `feedback ${type}`;
        feedbackArea.classList.add('visible');
    }

    // --- Updated to handle matching feedback ---
    function styleInputFeedback(questionType, isCorrect) {
        const correctClass = 'correct';
        const incorrectClass = 'incorrect';

        // Clear previous non-matching feedback styles first
        const textInput = answerInputArea.querySelector('#text-answer') || questionText.querySelector('#text-answer');
        if (textInput) textInput.classList.remove(correctClass, incorrectClass);
        answerInputArea.querySelectorAll('.mc-option').forEach(label => {
             label.classList.remove(correctClass, incorrectClass);
        });

        // Apply styles based on type
        switch (questionType) {
            case 'translation':
            case 'sentence_transformation':
            case 'fill_in_blank':
                if (textInput) {
                    textInput.classList.add(isCorrect ? correctClass : incorrectClass);
                }
                break;
            case 'multiple_choice':
                const radios = answerInputArea.querySelectorAll('input[name="mc-answer"]');
                radios.forEach(radio => {
                    const label = radio.closest('.mc-option');
                    if (!label) return;
                    const question = questions[currentQuestionIndex];
                    if (radio.value === question.answer) {
                        label.classList.add(correctClass); // Mark the correct option green
                    } else if (radio.checked && !isCorrect) {
                        label.classList.add(incorrectClass); // Mark the selected wrong option red
                    }
                });
                break;
            case 'matching':
                 // Styling for matching is handled directly within handleCheckAnswer
                 // by adding 'correct-pair' or 'incorrect-pair' classes.
                 // No further action needed here for matching type.
                 break;
        }
    }

    function showError(message, isFatal = true) {
        // ... (keep existing logic) ...
         console.error("Lesson Error:", message);
        questionInstruction.textContent = 'Error';
        questionText.textContent = message;
        answerInputArea.innerHTML = '';
        feedbackArea.innerHTML = '';
        if (isFatal) {
            checkButton.disabled = true;
            continueButton.style.display = 'none';
        }
    }

    // --- API Communication (loseHeart, completeLesson remain the same) ---
    async function loseHeart() {
         // ... (keep existing logic) ...
          if (currentHearts <= 0) return;

        currentHearts--;
        updateHeartsDisplay();
        console.log(`Lost a heart. Remaining: ${currentHearts}`);

        if (currentHearts <= 0) {
            checkButton.disabled = true;
             // Ensure matching items are also disabled
             answerInputArea.querySelectorAll('.match-item').forEach(item => item.disabled = true);
            showFeedback("Oh no, you're out of hearts!", "incorrect");
        }

        try {
            const response = await fetch('/lose_heart', { method: 'POST' });
            if (!response.ok) {
                console.error("Failed to update heart count on server.");
            } else {
                 console.log("Server confirmed heart loss.");
                 // const data = await response.json(); // If you need updated count/time
            }
        } catch (error) {
            console.error("Network error losing heart:", error);
        }
    }

    async function completeLesson() {
         // ... (keep existing logic) ...
         console.log("Lesson complete!");
        showFeedback("Lesson Complete!", "correct");
        checkButton.style.display = 'none';
        continueButton.style.display = 'none';

        try {
            const url = `/complete_lesson/${lessonId}?lang=${language}`;
            const response = await fetch(url, { method: 'POST' });

            if (response.ok) {
                const result = await response.json();
                console.log("Lesson completion acknowledged by server:", result);
                showFeedback(`Lesson Complete! +${result.xp_earned || '??'} XP`, "correct");
                setTimeout(() => {
                    window.location.href = `/dashboard?lang=${language}`;
                }, 1500);
            } else {
                console.error("Failed to mark lesson as complete on server.");
                showError("Could not save lesson completion. Please try again later.", false);
            }
        } catch (error) {
            console.error("Network error completing lesson:", error);
            showError("Network error saving completion. Please check your connection.", false);
        }
    }

    // --- Start the Lesson ---
    initLesson();
});