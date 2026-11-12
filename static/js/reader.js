/* ==========================================================================
   WBooks — Interactive reader
   Page turning, live themes, particle atmospheres and auto-saving progress.
   ========================================================================== */
(function () {
    "use strict";

    var shell = document.querySelector("[data-reader]");
    if (!shell) {
        return;
    }

    var pages = Array.prototype.slice.call(
        shell.querySelectorAll("[data-page]")
    );
    if (!pages.length) {
        return;
    }

    var currentEl = shell.querySelector("[data-reader-current]");
    var totalEl = shell.querySelector("[data-reader-total]");
    var meter = shell.querySelector("[data-reader-meter]");
    var saveEl = shell.querySelector("[data-reader-save]");
    var saveText = shell.querySelector("[data-reader-save-text]");
    var announcement = shell.querySelector("[data-reader-announcement]");
    var particleHost = shell.querySelector("[data-reader-particles]");
    var endnote = shell.querySelector("[data-reader-endnote]");
    var prevButton = shell.querySelector("[data-reader-prev]");
    var nextButton = shell.querySelector("[data-reader-next]");
    var restartButton = shell.querySelector("[data-reader-restart]");
    var dots = Array.prototype.slice.call(
        shell.querySelectorAll("[data-reader-dot]")
    );
    var themeButtons = Array.prototype.slice.call(
        shell.querySelectorAll("[data-reader-theme-option]")
    );

    var THEME_KEYS = ["forest", "ice", "holo", "classic"];
    var THEME_COLORS = {
        forest: "#0c2118",
        ice: "#061725",
        holo: "#03060d",
        classic: "#e6d8bf"
    };
    var PARTICLE_COUNT = {
        forest: 18,
        ice: 16,
        holo: 14,
        classic: 12
    };

    var bookSlug = shell.getAttribute("data-book-slug") || "";
    var bookTitle = shell.getAttribute("data-book-title") || "this story";
    var saveUrl = shell.getAttribute("data-save-url") || "/api/progress/";
    var csrfToken = shell.getAttribute("data-csrf") || "";
    var defaultTheme = shell.getAttribute("data-reader-theme") || "classic";
    var storageKey = "wbooks-reader-theme:" + bookSlug;
    var initialPage = parseInt(shell.getAttribute("data-initial-page"), 10);

    var total = pages.length;
    var currentIndex = 0;
    var isFlipping = false;
    var pendingPage = null;
    var pendingSeconds = 0;
    var saveInFlight = false;
    var lastSavedPage = null;
    var retryAttempts = 0;
    var retryTimer = null;
    var flushTimer = null;

    var reduceMotion =
        window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* ------------------------------------------------------------ utilities */
    function clamp(value, minimum, maximum) {
        return Math.min(maximum, Math.max(minimum, value));
    }

    function randomBetween(minimum, maximum) {
        return minimum + Math.random() * (maximum - minimum);
    }

    function pageNumberAt(index) {
        var value = parseInt(pages[index].getAttribute("data-page"), 10);
        return Number.isFinite(value) ? value : index + 1;
    }

    function setSaveState(state, text) {
        if (!saveEl) {
            return;
        }
        saveEl.setAttribute("data-state", state);
        if (saveText) {
            saveText.textContent = text;
        }
    }

    function announce(text) {
        if (!announcement) {
            return;
        }
        announcement.textContent = "";
        window.setTimeout(function () {
            announcement.textContent = text;
        }, 40);
    }

    /* ------------------------------------------------------ initial position */
    var foundInitial = -1;
    pages.forEach(function (page, index) {
        var number = parseInt(page.getAttribute("data-page"), 10);
        if (number === initialPage) {
            foundInitial = index;
        }
    });
    currentIndex = foundInitial >= 0 ? foundInitial : 0;

    pages.forEach(function (page, index) {
        var isCurrent = index === currentIndex;
        page.classList.toggle("is-active", isCurrent);
        page.setAttribute("aria-hidden", isCurrent ? "false" : "true");
        if (isCurrent) {
            page.setAttribute("tabindex", "0");
        } else {
            page.removeAttribute("tabindex");
        }
    });

    lastSavedPage = pageNumberAt(currentIndex);

    /* --------------------------------------------------------------- chrome */
    function updateChrome() {
        var pageNumber = pageNumberAt(currentIndex);
        var percentage = Math.round(((currentIndex + 1) / total) * 100);

        if (currentEl) {
            currentEl.textContent = String(pageNumber);
        }
        if (totalEl) {
            totalEl.textContent = String(total);
        }
        if (meter) {
            meter.style.width = percentage + "%";
            var track = meter.parentElement;
            if (track) {
                track.setAttribute("aria-valuenow", String(percentage));
            }
        }
        if (prevButton) {
            prevButton.disabled = currentIndex === 0;
        }
        if (nextButton) {
            nextButton.disabled = currentIndex === total - 1;
        }
        if (endnote) {
            endnote.hidden = currentIndex !== total - 1;
        }

        dots.forEach(function (dot, index) {
            var isCurrent = index === currentIndex;
            dot.classList.toggle("is-current", isCurrent);
            dot.setAttribute("aria-current", isCurrent ? "page" : "false");
        });

        shell.classList.toggle("is-last-page", currentIndex === total - 1);
    }

    /* ----------------------------------------------------------- page turns */
    function preloadNeighbours(index) {
        [index - 1, index + 1].forEach(function (neighbour) {
            if (neighbour < 0 || neighbour >= total) {
                return;
            }
            var image = pages[neighbour].querySelector("img");
            if (!image) {
                return;
            }
            var source = image.getAttribute("src");
            if (source) {
                var preload = new Image();
                preload.src = source;
            }
        });
    }

    function showPage(index, options) {
        var settings = options || {};
        var target = clamp(index, 0, total - 1);

        if (target === currentIndex || isFlipping) {
            return;
        }

        var direction =
            settings.direction || (target > currentIndex ? "next" : "prev");
        var flipClass = direction === "next" ? "is-flipping-next" : "is-flipping-prev";
        var outgoing = pages[currentIndex];
        var incoming = pages[target];

        isFlipping = true;

        outgoing.classList.remove("is-active");
        outgoing.classList.add("is-leaving", flipClass);
        outgoing.setAttribute("aria-hidden", "true");
        outgoing.removeAttribute("tabindex");

        incoming.classList.add("is-active", flipClass);
        incoming.setAttribute("aria-hidden", "false");
        incoming.setAttribute("tabindex", "0");

        currentIndex = target;
        updateChrome();
        preloadNeighbours(currentIndex);

        if (settings.save !== false) {
            queueSave(pageNumberAt(currentIndex));
        }

        announce(
            "Page " + pageNumberAt(currentIndex) + " of " + total + "."
        );

        var settle = function () {
            outgoing.classList.remove("is-leaving", "is-flipping-next", "is-flipping-prev");
            incoming.classList.remove("is-flipping-next", "is-flipping-prev");
            isFlipping = false;
        };

        window.setTimeout(settle, reduceMotion ? 0 : 680);
    }

    function goNext() {
        showPage(currentIndex + 1, { direction: "next" });
    }

    function goPrevious() {
        showPage(currentIndex - 1, { direction: "prev" });
    }

    if (prevButton) {
        prevButton.addEventListener("click", goPrevious);
    }
    if (nextButton) {
        nextButton.addEventListener("click", goNext);
    }
    if (restartButton) {
        restartButton.addEventListener("click", function () {
            showPage(0, { direction: "prev", save: true });
        });
    }

    dots.forEach(function (dot, index) {
        dot.addEventListener("click", function () {
            showPage(index, {
                direction: index >= currentIndex ? "next" : "prev"
            });
        });
    });

    /* ------------------------------------------------------------- keyboard */
    document.addEventListener("keydown", function (event) {
        if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) {
            return;
        }
        var tag = event.target && event.target.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
            return;
        }

        if (event.key === "ArrowRight" || event.key === "PageDown") {
            event.preventDefault();
            goNext();
        } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
            event.preventDefault();
            goPrevious();
        } else if (event.key === "Home") {
            event.preventDefault();
            showPage(0, { direction: "prev" });
        } else if (event.key === "End") {
            event.preventDefault();
            showPage(total - 1, { direction: "next" });
        }
    });

    /* ---------------------------------------------------------------- swipe */
    var touchStartX = 0;
    var touchStartY = 0;
    var touchTracking = false;
    var book = shell.querySelector("[data-reader-book]");

    if (book) {
        book.addEventListener(
            "touchstart",
            function (event) {
                if (event.touches.length !== 1) {
                    touchTracking = false;
                    return;
                }
                touchTracking = true;
                touchStartX = event.touches[0].clientX;
                touchStartY = event.touches[0].clientY;
            },
            { passive: true }
        );

        book.addEventListener(
            "touchend",
            function (event) {
                if (!touchTracking || !event.changedTouches.length) {
                    return;
                }
                touchTracking = false;
                var deltaX = event.changedTouches[0].clientX - touchStartX;
                var deltaY = event.changedTouches[0].clientY - touchStartY;

                if (Math.abs(deltaX) < 48) {
                    return;
                }
                if (Math.abs(deltaX) < Math.abs(deltaY) * 1.2) {
                    return;
                }
                if (deltaX < 0) {
                    goNext();
                } else {
                    goPrevious();
                }
            },
            { passive: true }
        );
    }

    /* --------------------------------------------------------------- themes */
    function readStoredTheme() {
        try {
            return window.localStorage.getItem(storageKey);
        } catch (error) {
            return null;
        }
    }

    function buildParticles(theme) {
        if (!particleHost) {
            return;
        }
        particleHost.textContent = "";
        if (reduceMotion) {
            return;
        }

        var count = PARTICLE_COUNT[theme] || 12;
        var fragment = document.createDocumentFragment();

        for (var index = 0; index < count; index += 1) {
            var particle = document.createElement("span");
            particle.className = "reader-particle";
            particle.style.setProperty("--x", randomBetween(2, 98).toFixed(2) + "%");
            particle.style.setProperty("--y", randomBetween(0, 96).toFixed(2) + "%");
            particle.style.setProperty("--size", randomBetween(5, 11).toFixed(1) + "px");
            particle.style.setProperty("--dur", randomBetween(7, 15).toFixed(1) + "s");
            particle.style.setProperty("--delay", (-randomBetween(0, 10)).toFixed(1) + "s");
            particle.style.setProperty("--sway", randomBetween(-70, 70).toFixed(1) + "px");
            fragment.appendChild(particle);
        }

        particleHost.appendChild(fragment);
    }

    function applyTheme(theme, options) {
        var settings = options || {};
        var key = THEME_KEYS.indexOf(theme) >= 0 ? theme : "classic";

        shell.setAttribute("data-reader-theme", key);
        themeButtons.forEach(function (button) {
            var isActive = button.getAttribute("data-reader-theme-option") === key;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });

        buildParticles(key);

        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta && THEME_COLORS[key]) {
            meta.setAttribute("content", THEME_COLORS[key]);
        }

        if (settings.persist !== false) {
            try {
                window.localStorage.setItem(storageKey, key);
            } catch (error) {
                /* Theme still applies for this visit. */
            }
        }
    }

    themeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            applyTheme(button.getAttribute("data-reader-theme-option"));
        });
    });

    var storedTheme = readStoredTheme();
    applyTheme(
        THEME_KEYS.indexOf(storedTheme) >= 0 ? storedTheme : defaultTheme,
        { persist: false }
    );

    /* --------------------------------------------------------- auto-saving */
    function beaconSave() {
        var hasPage = pendingPage !== null && pendingPage !== lastSavedPage;
        var hasTime = pendingSeconds > 0;
        if ((!hasPage && !hasTime) || !navigator.sendBeacon) {
            return;
        }

        var body = new URLSearchParams();
        body.set("book", bookSlug);
        body.set(
            "current_page",
            String(pendingPage !== null ? pendingPage : lastSavedPage)
        );
        body.set("seconds", String(pendingSeconds));
        body.set("csrfmiddlewaretoken", csrfToken);
        navigator.sendBeacon(saveUrl, body);

        pendingPage = null;
        pendingSeconds = 0;
    }

    function flushSave() {
        if (saveInFlight) {
            return;
        }

        var hasPage = pendingPage !== null && pendingPage !== lastSavedPage;
        var hasTime = pendingSeconds > 0;
        if (!hasPage && !hasTime) {
            return;
        }

        var pageToSave = pendingPage !== null ? pendingPage : lastSavedPage;
        var secondsToSave = pendingSeconds;
        pendingPage = null;
        pendingSeconds = 0;
        saveInFlight = true;

        setSaveState("saving", "Saving…");

        fetch(saveUrl, {
            method: "POST",
            credentials: "same-origin",
            keepalive: true,
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify({
                book: bookSlug,
                current_page: pageToSave,
                seconds: secondsToSave
            })
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Progress save failed with " + response.status);
                }
                return response.json();
            })
            .then(function (data) {
                retryAttempts = 0;
                lastSavedPage = Number(data.current_page);
                if (data.is_completed) {
                    setSaveState("saved", "Story complete");
                } else {
                    setSaveState("saved", "Saved · page " + data.current_page);
                }
            })
            .catch(function () {
                if (pendingPage === null) {
                    pendingPage = pageToSave;
                }
                pendingSeconds += secondsToSave;
                setSaveState("error", "Will retry");

                if (retryAttempts < 3 && retryTimer === null) {
                    retryAttempts += 1;
                    retryTimer = window.setTimeout(function () {
                        retryTimer = null;
                        flushSave();
                    }, 5000);
                }
            })
            .finally(function () {
                saveInFlight = false;
                if (
                    (pendingPage !== null && pendingPage !== lastSavedPage) ||
                    pendingSeconds > 0
                ) {
                    if (retryTimer === null) {
                        flushSave();
                    }
                }
            });
    }

    function queueSave(pageNumber) {
        if (!Number.isFinite(pageNumber)) {
            return;
        }
        pendingPage = pageNumber;
        if (!saveInFlight) {
            flushSave();
        }
    }

    window.addEventListener("online", function () {
        retryAttempts = 0;
        if (retryTimer !== null) {
            window.clearTimeout(retryTimer);
            retryTimer = null;
        }
        flushSave();
    });

    /* ------------------------------------------------------- reading time */
    function tickReadingTime() {
        if (document.visibilityState !== "visible") {
            return;
        }
        pendingSeconds += 1;

        if (pendingSeconds >= 60) {
            flushSave();
        }
    }

    flushTimer = window.setInterval(tickReadingTime, 1000);

    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") {
            beaconSave();
        }
    });

    window.addEventListener("pagehide", beaconSave);

    /* --------------------------------------------------------------- initial */
    updateChrome();
    preloadNeighbours(currentIndex);
    announce("Page " + pageNumberAt(currentIndex) + " of " + total + ".");
})();
