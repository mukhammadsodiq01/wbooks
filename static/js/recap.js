/* ==========================================================================
   WBooks — recap storyboard player
   A lightweight slideshow with autoplay, scene dots, swipe and video sync.
   ========================================================================== */
(function () {
    "use strict";

    var player = document.querySelector("[data-recap]");
    if (!player) {
        return;
    }

    var scenes = Array.prototype.slice.call(
        player.querySelectorAll("[data-recap-scene]")
    );
    if (!scenes.length) {
        return;
    }

    var playButton = player.querySelector("[data-recap-play]");
    var playText = player.querySelector("[data-recap-play-text]");
    var prevButton = player.querySelector("[data-recap-prev]");
    var nextButton = player.querySelector("[data-recap-next]");
    var currentEl = player.querySelector("[data-recap-current]");
    var totalEl = player.querySelector("[data-recap-total]");
    var track = player.querySelector("[data-recap-track]");
    var dots = Array.prototype.slice.call(
        player.querySelectorAll("[data-recap-dot]")
    );
    var video = player.querySelector(".recap-video-player");
    var stage = player.querySelector("[data-recap-stage]");

    var total = scenes.length;
    var index = 0;
    var playing = false;
    var timer = null;

    var reduceMotion =
        window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var SCENE_MS = reduceMotion ? 8000 : 5600;

    function setPlayLabel(label, pressed) {
        if (!playButton) {
            return;
        }
        playButton.setAttribute("aria-pressed", pressed ? "true" : "false");
        if (playText) {
            playText.textContent = label;
        }
    }

    function clearTimer() {
        if (timer !== null) {
            window.clearTimeout(timer);
            timer = null;
        }
    }

    function updateChrome() {
        if (currentEl) {
            currentEl.textContent = String(index + 1);
        }
        if (totalEl) {
            totalEl.textContent = String(total);
        }
        if (track) {
            track.style.width = Math.round(((index + 1) / total) * 100) + "%";
        }

        dots.forEach(function (dot, dotIndex) {
            var current = dotIndex === index;
            dot.classList.toggle("is-current", current);
            dot.setAttribute("aria-current", current ? "step" : "false");
        });

        if (prevButton) {
            prevButton.disabled = false;
        }
        if (nextButton) {
            nextButton.disabled = false;
        }
    }

    function showScene(target) {
        var next = Math.min(total - 1, Math.max(0, target));
        if (next === index) {
            return;
        }

        scenes[index].classList.remove("is-active");
        scenes[index].setAttribute("aria-hidden", "true");
        scenes[next].classList.add("is-active");
        scenes[next].setAttribute("aria-hidden", "false");
        index = next;
        updateChrome();
    }

    function scheduleNext() {
        clearTimer();
        if (!playing) {
            return;
        }
        if (index >= total - 1) {
            playing = false;
            setPlayLabel("Play again", false);
            return;
        }
        timer = window.setTimeout(function () {
            timer = null;
            showScene(index + 1);
            if (index >= total - 1) {
                playing = false;
                setPlayLabel("Play again", false);
            } else {
                scheduleNext();
            }
        }, SCENE_MS);
    }

    function play() {
        if (playing) {
            return;
        }
        if (index >= total - 1) {
            playing = true;
            showScene(0);
            setPlayLabel("Pause storyboard", true);
            scheduleNext();
            return;
        }
        playing = true;
        setPlayLabel("Pause storyboard", true);
        scheduleNext();
    }

    function pause() {
        playing = false;
        clearTimer();
        setPlayLabel(
            index >= total - 1 ? "Play again" : "Play the storyboard",
            false
        );
    }

    if (playButton) {
        playButton.addEventListener("click", function () {
            if (playing) {
                pause();
            } else {
                play();
            }
        });
    }

    if (prevButton) {
        prevButton.addEventListener("click", function () {
            var wasPlaying = playing;
            showScene(index - 1);
            if (wasPlaying) {
                scheduleNext();
            }
        });
    }

    if (nextButton) {
        nextButton.addEventListener("click", function () {
            var wasPlaying = playing;
            showScene(index + 1);
            if (wasPlaying) {
                scheduleNext();
            }
        });
    }

    dots.forEach(function (dot) {
        dot.addEventListener("click", function () {
            pause();
            showScene(parseInt(dot.getAttribute("data-recap-dot"), 10) || 0);
        });
    });

    /* ---------------------------------------------------------------- swipe */
    var touchStartX = 0;
    var touchStartY = 0;
    var tracking = false;

    if (stage) {
        stage.addEventListener(
            "touchstart",
            function (event) {
                if (event.touches.length !== 1) {
                    tracking = false;
                    return;
                }
                tracking = true;
                touchStartX = event.touches[0].clientX;
                touchStartY = event.touches[0].clientY;
            },
            { passive: true }
        );

        stage.addEventListener(
            "touchend",
            function (event) {
                if (!tracking || !event.changedTouches.length) {
                    return;
                }
                tracking = false;
                var deltaX = event.changedTouches[0].clientX - touchStartX;
                var deltaY = event.changedTouches[0].clientY - touchStartY;
                if (Math.abs(deltaX) < 46) {
                    return;
                }
                if (Math.abs(deltaX) < Math.abs(deltaY) * 1.2) {
                    return;
                }
                pause();
                showScene(deltaX < 0 ? index + 1 : index - 1);
            },
            { passive: true }
        );
    }

    /* ------------------------------------------------------- keyboard + tab */
    player.addEventListener("keydown", function (event) {
        if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) {
            return;
        }
        var tag = event.target && event.target.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
            return;
        }
        if (event.key === "ArrowRight") {
            event.preventDefault();
            pause();
            showScene(index + 1);
        } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            pause();
            showScene(index - 1);
        } else if (event.key === " " || event.key === "Enter") {
            if (event.target === player) {
                event.preventDefault();
                playButton && playButton.click();
            }
        }
    });

    /* ------------------------------------------------------------ video sync */
    if (video) {
        video.addEventListener("play", pause);
    }

    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden" && playing) {
            pause();
        }
    });

    updateChrome();
})();
