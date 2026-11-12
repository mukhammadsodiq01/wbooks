/* ==========================================================================
   WBooks — interaction layer
   Theme switching, mobile navigation, toasts, age filters and reveal effects.
   ========================================================================== */
(function () {
    "use strict";

    var root = document.documentElement;
    var THEME_KEY = "wbooks-theme";

    /* ---------------------------------------------------------------- Theme */
    function applyTheme(theme) {
        root.setAttribute("data-theme", theme);
        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute("content", theme === "dark" ? "#141021" : "#fbf8f2");
        }
        var toggles = document.querySelectorAll("[data-theme-toggle]");
        toggles.forEach(function (button) {
            button.setAttribute(
                "aria-label",
                theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
            );
            button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
        });
    }

    var savedTheme = "light";
    try {
        var stored = localStorage.getItem(THEME_KEY);
        if (stored === "dark" || stored === "light") {
            savedTheme = stored;
        } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
            savedTheme = "dark";
        }
    } catch (error) {
        savedTheme = root.getAttribute("data-theme") || "light";
    }
    applyTheme(savedTheme);

    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
        button.addEventListener("click", function () {
            var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
            applyTheme(next);
            try {
                localStorage.setItem(THEME_KEY, next);
            } catch (error) {
                /* Reading preferences still work for this page view. */
            }
        });
    });

    /* --------------------------------------------------------------- Header */
    var header = document.querySelector("[data-site-header]");
    if (header) {
        var updateHeader = function () {
            header.classList.toggle("is-scrolled", window.scrollY > 8);
        };
        updateHeader();
        window.addEventListener("scroll", updateHeader, { passive: true });
    }

    /* ------------------------------------------------------ Mobile navigation */
    var navToggle = document.querySelector("[data-nav-toggle]");
    var nav = document.querySelector("[data-primary-nav]");

    function closeNav() {
        if (!nav || !navToggle) {
            return;
        }
        nav.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
        var label = navToggle.querySelector(".sr-only");
        if (label) {
            label.textContent = "Open menu";
        }
    }

    if (navToggle && nav) {
        navToggle.addEventListener("click", function () {
            var isOpen = nav.classList.toggle("is-open");
            navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
            var label = navToggle.querySelector(".sr-only");
            if (label) {
                label.textContent = isOpen ? "Close menu" : "Open menu";
            }
        });

        nav.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", closeNav);
        });

        document.addEventListener("click", function (event) {
            if (!nav.classList.contains("is-open")) {
                return;
            }
            if (!nav.contains(event.target) && !navToggle.contains(event.target)) {
                closeNav();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && nav.classList.contains("is-open")) {
                closeNav();
                navToggle.focus();
            }
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > 860) {
                closeNav();
            }
        });
    }

    /* --------------------------------------------------------------- Toasts */
    var toastStack = document.querySelector("[data-toast-stack]");

    function dismissToast(toast) {
        if (!toast || toast.classList.contains("toast-hiding")) {
            return;
        }
        toast.classList.add("toast-hiding");
        window.setTimeout(function () {
            toast.remove();
            if (toastStack && toastStack.children.length === 0) {
                toastStack.remove();
            }
        }, 240);
    }

    if (toastStack) {
        toastStack.querySelectorAll("[data-toast]").forEach(function (toast, index) {
            var close = toast.querySelector("[data-toast-close]");
            if (close) {
                close.addEventListener("click", function () {
                    dismissToast(toast);
                });
            }
            window.setTimeout(function () {
                dismissToast(toast);
            }, 6500 + index * 600);
        });
    }

    /* --------------------------------------------------------- Scroll reveal */
    var revealItems = document.querySelectorAll(".reveal");
    if (revealItems.length) {
        if ("IntersectionObserver" in window) {
            var revealObserver = new IntersectionObserver(
                function (entries, observer) {
                    entries.forEach(function (entry) {
                        if (!entry.isIntersecting) {
                            return;
                        }
                        entry.target.classList.add("is-visible");
                        observer.unobserve(entry.target);
                    });
                },
                { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
            );
            revealItems.forEach(function (item, index) {
                item.style.transitionDelay = Math.min(index * 45, 260) + "ms";
                revealObserver.observe(item);
            });
        } else {
            revealItems.forEach(function (item) {
                item.classList.add("is-visible");
            });
        }
    }

    /* ------------------------------------------------------ Registration role */
    var registerForm = document.querySelector("[data-register-form]");
    if (registerForm) {
        var roleRadios = registerForm.querySelectorAll('input[name="role"]');
        var parentFieldWrap = registerForm.querySelector("[data-parent-email-field]");

        var syncParentField = function () {
            if (!parentFieldWrap) {
                return;
            }
            var selected = registerForm.querySelector('input[name="role"]:checked');
            var isChild = !selected || selected.value === "child";
            parentFieldWrap.hidden = !isChild;
            var emailInput = parentFieldWrap.querySelector("input");
            if (emailInput) {
                emailInput.disabled = !isChild;
                if (!isChild) {
                    emailInput.value = "";
                }
            }
        };

        roleRadios.forEach(function (radio) {
            radio.addEventListener("change", syncParentField);
        });
        syncParentField();

        var passwordOne = registerForm.querySelector("#id_password1");
        var passwordTwo = registerForm.querySelector("#id_password2");
        if (passwordOne && passwordTwo) {
            passwordTwo.addEventListener("input", function () {
                if (!passwordTwo.value) {
                    passwordTwo.setCustomValidity("");
                    return;
                }
                passwordTwo.setCustomValidity(
                    passwordOne.value === passwordTwo.value
                        ? ""
                        : "Passwords do not match yet."
                );
            });
            passwordOne.addEventListener("input", function () {
                passwordTwo.setCustomValidity("");
            });
        }
    }

    /* ------------------------------------------------------------ Age filter */
    var filterButtons = document.querySelectorAll("[data-age-filter]");
    var bookGrid = document.querySelector("[data-book-grid]");
    var filterEmpty = document.querySelector("[data-filter-empty]");

    if (filterButtons.length && bookGrid) {
        filterButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                var age = button.getAttribute("data-age-filter");
                var visibleCount = 0;

                filterButtons.forEach(function (item) {
                    item.classList.toggle("is-active", item === button);
                    item.setAttribute("aria-pressed", item === button ? "true" : "false");
                });

                bookGrid.querySelectorAll("[data-age]").forEach(function (card) {
                    var matches = age === "all" || card.getAttribute("data-age") === age;
                    card.hidden = !matches;
                    if (matches) {
                        visibleCount += 1;
                    }
                });

                if (filterEmpty) {
                    filterEmpty.hidden = visibleCount > 0 || bookGrid.querySelector(".empty-state");
                }
            });
        });
    }

    /* ------------------------------------------- Password visibility (optional) */
    document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
        button.addEventListener("click", function () {
            var input = document.getElementById(button.getAttribute("data-toggle-password"));
            if (!input) {
                return;
            }
            var showing = input.type === "text";
            input.type = showing ? "password" : "text";
            button.setAttribute("aria-pressed", showing ? "false" : "true");
            button.textContent = showing ? "Show" : "Hide";
        });
    });
})();
