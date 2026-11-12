/* ==========================================================================
   WBooks — quiz interaction
   One question at a time, instant feedback and server-graded submission.
   ========================================================================== */
(function () {
    "use strict";

    var form = document.querySelector("[data-quiz-form]");
    if (!form) {
        return;
    }

    var steps = Array.prototype.slice.call(
        form.querySelectorAll("[data-quiz-step]")
    );
    if (!steps.length) {
        return;
    }

    var nextButton = form.querySelector("[data-quiz-next]");
    var submitButton = form.querySelector("[data-quiz-submit]");
    var root = form.closest(".quiz-card") || document;
    var currentEl = root.querySelector("[data-quiz-current]");
    var totalEl = root.querySelector("[data-quiz-total]");
    var meter = root.querySelector("[data-quiz-meter]");
    var live = root.querySelector("[data-quiz-live]");
    var note = form.querySelector("[data-quiz-note]");

    var current = 0;
    var total = steps.length;
    var answered = 0;

    function setLive(text) {
        if (live) {
            live.textContent = text;
        }
    }

    function setNote(text) {
        if (note) {
            note.textContent = text;
        }
    }

    function updateHeader() {
        if (currentEl) {
            currentEl.textContent = String(current + 1);
        }
        if (totalEl) {
            totalEl.textContent = String(total);
        }
        if (meter) {
            var percentage = Math.round(((current + 1) / total) * 100);
            meter.style.width = percentage + "%";
            var track = meter.parentElement;
            if (track) {
                track.setAttribute("aria-valuenow", String(percentage));
            }
        }
    }

    function focusStep(step) {
        var first = step.querySelector(".quiz-radio");
        if (first) {
            first.focus({ preventScroll: true });
            step.scrollIntoView({
                behavior:
                    window.matchMedia &&
                    window.matchMedia("(prefers-reduced-motion: reduce)").matches
                        ? "auto"
                        : "smooth",
                block: "nearest"
            });
        }
    }

    function markAnswer(step, label, feedback) {
        var selected = label.querySelector(".quiz-radio");
        if (!selected) {
            return;
        }

        var options = Array.prototype.slice.call(
            step.querySelectorAll("[data-quiz-option]")
        );
        var correct = parseInt(step.getAttribute("data-correct"), 10);
        var chosen = parseInt(selected.value, 10);
        var isCorrect = chosen === correct;

        options.forEach(function (option) {
            var value = parseInt(option.getAttribute("data-value"), 10);
            option.classList.toggle("is-correct", value === correct);
            option.classList.toggle("is-wrong", value === chosen && !isCorrect);
            option.classList.toggle(
                "is-dimmed",
                value !== correct && value !== chosen
            );
        });

        var feedbackIcon = feedback.querySelector("[data-quiz-feedback-icon]");
        var verdict = feedback.querySelector("[data-quiz-verdict]");
        var explanation = feedback.querySelector("[data-quiz-explanation]");

        feedback.hidden = false;
        feedback.classList.toggle("is-wrong", !isCorrect);
        if (feedbackIcon) {
            feedbackIcon.textContent = isCorrect ? "✓" : "✦";
        }
        if (verdict) {
            verdict.textContent = isCorrect
                ? "That's right!"
                : "Not quite — here's the clue.";
        }
        if (explanation) {
            explanation.textContent =
                step.getAttribute("data-explanation") ||
                (isCorrect
                    ? "You remembered this moment beautifully."
                    : "Every story has a detail worth revisiting. You'll get it next time.");
        }

        step.setAttribute("data-answered", "true");
        step.setAttribute("data-chosen", String(chosen));
        answered += 1;
        setLive(
            answered === total
                ? "All questions answered"
                : "Answered " + answered + " of " + total
        );

        if (current >= total - 1) {
            if (nextButton) {
                nextButton.hidden = true;
            }
            if (submitButton) {
                submitButton.hidden = false;
                submitButton.disabled = false;
            }
            setNote("All done — finish the quiz to see your score.");
        } else if (nextButton) {
            nextButton.hidden = false;
            nextButton.disabled = false;
        }
    }

    steps.forEach(function (step) {
        var options = Array.prototype.slice.call(
            step.querySelectorAll("[data-quiz-option]")
        );

        options.forEach(function (option) {
            option.addEventListener("click", function (event) {
                if (step.getAttribute("data-answered") === "true") {
                    event.preventDefault();
                    return;
                }
                var input = option.querySelector(".quiz-radio");
                if (input && !input.checked) {
                    input.checked = true;
                    input.dispatchEvent(new Event("change", { bubbles: true }));
                }
            });

            var radio = option.querySelector(".quiz-radio");
            if (radio) {
                radio.addEventListener("click", function (event) {
                    if (step.getAttribute("data-answered") === "true") {
                        event.preventDefault();
                    }
                });
                radio.addEventListener("keydown", function (event) {
                    if (
                        step.getAttribute("data-answered") === "true" &&
                        (event.key === " " ||
                            event.key === "Enter" ||
                            event.key === "ArrowUp" ||
                            event.key === "ArrowDown" ||
                            event.key === "ArrowLeft" ||
                            event.key === "ArrowRight")
                    ) {
                        event.preventDefault();
                    }
                });
                radio.addEventListener("change", function () {
                    if (step.getAttribute("data-answered") === "true") {
                        var chosen = step.getAttribute("data-chosen");
                        Array.prototype.forEach.call(
                            step.querySelectorAll(".quiz-radio"),
                            function (input) {
                                input.checked = input.value === chosen;
                            }
                        );
                        return;
                    }
                    var feedback = step.querySelector("[data-quiz-feedback]");
                    if (feedback) {
                        markAnswer(step, option, feedback);
                    }
                });
            }
        });
    });

    if (nextButton) {
        nextButton.disabled = true;
        nextButton.addEventListener("click", function () {
            if (current >= total - 1) {
                return;
            }
            steps[current].classList.remove("is-active");
            current += 1;
            steps[current].classList.add("is-active");
            updateHeader();
            nextButton.disabled = true;
            nextButton.hidden = true;
            if (note) {
                setNote("Choose the answer that feels right.");
            }
            if (current >= total - 1) {
                nextButton.hidden = true;
            }
            focusStep(steps[current]);
        });
    }

    if (total > 1 && submitButton) {
        submitButton.hidden = true;
    }

    if (total === 1) {
        if (nextButton) {
            nextButton.hidden = true;
        }
        if (submitButton) {
            submitButton.disabled = true;
        }
    }

    form.addEventListener("submit", function (event) {
        var unanswered = steps.filter(function (step) {
            return step.getAttribute("data-answered") !== "true";
        });

        if (unanswered.length) {
            event.preventDefault();
            var first = unanswered[0];
            var target = steps.indexOf(first);
            if (target >= 0) {
                steps[current].classList.remove("is-active");
                current = target;
                first.classList.add("is-active");
                updateHeader();
                focusStep(first);
            }
            setLive("Answer every question first");
            setNote("There's still one question waiting for your answer.");
            return;
        }

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Checking your answers…";
        }
        setLive("Checking your answers…");
    });

    updateHeader();
    setLive("Ready when you are");
})();
