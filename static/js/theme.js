/* Light / dark switch for every page. Loaded in <head> so the saved choice is applied before the page is painted.
   - the choice is saved in the browser (localStorage "theme": "light" or "dark"); dark is the default
   - any element with data-theme-toggle switches it (its <i> shows an eye: open = light mode on, slashed = off)
   - elements with data-theme-label show "On" / "Off"
   - a page with data-always-dark on <html> (the live interview) is never switched */
(function () {
    var KEY = "theme";
    var root = document.documentElement;
    var always = root.hasAttribute("data-always-dark");
    var here = document.currentScript ? document.currentScript.src : "";

    function saved() {
        try { return localStorage.getItem(KEY) === "light" ? "light" : "dark"; } catch (e) { return "dark"; }
    }

    function loadInlineMap(done) {
        if (window.__LIGHT_INLINE) { done(); return; }
        var s = document.createElement("script");
        s.src = here ? here.replace(/theme\.js(\?.*)?$/, "light-inline-map.js") : "/static/js/light-inline-map.js";
        s.onload = done;
        document.head.appendChild(s);
    }

    function swapInline(light) {
        // inline styles marked !important cannot be overridden by a stylesheet, so they are swapped here
        var nodes = document.querySelectorAll("[style]");
        for (var i = 0; i < nodes.length; i++) {
            var el = nodes[i];
            var original = el.hasAttribute("data-dark-style") ? el.getAttribute("data-dark-style") : el.getAttribute("style");
            if (light) {
                var map = window.__LIGHT_INLINE || {};
                if (map[original]) {
                    if (!el.hasAttribute("data-dark-style")) el.setAttribute("data-dark-style", original);
                    el.setAttribute("style", map[original]);
                }
            } else if (el.hasAttribute("data-dark-style")) {
                el.setAttribute("style", original);
                el.removeAttribute("data-dark-style");
            }
        }
    }

    function buttons(light) {
        var list = document.querySelectorAll("[data-theme-toggle]");
        for (var i = 0; i < list.length; i++) {
            var b = list[i];
            b.setAttribute("aria-pressed", light ? "true" : "false");
            b.setAttribute("title", light ? "Light mode is on. Click to switch it off" : "Light mode is off. Click to switch it on");
            var icon = b.querySelector("i");
            if (icon) icon.className = "bi " + (light ? "bi-eye-fill" : "bi-eye-slash");
        }
        var labels = document.querySelectorAll("[data-theme-label]");
        for (var j = 0; j < labels.length; j++) labels[j].textContent = light ? "On" : "Off";
    }

    function apply(theme) {
        if (always) theme = "dark";
        var light = theme === "light";
        root.classList.toggle("light-theme", light);
        root.classList.toggle("dark-theme", !light);
        root.setAttribute("data-theme", light ? "light" : "dark");
        if (document.body) document.body.classList.toggle("dark-theme", !light);
        if (document.readyState !== "loading") { buttons(light); if (light) loadInlineMap(function () { swapInline(true); }); else swapInline(false); }
    }

    // 1. before the first paint
    apply(saved());

    // 2. once the page exists: buttons, inline styles, and the click handler
    document.addEventListener("DOMContentLoaded", function () {
        var light = !always && saved() === "light";
        if (document.body) document.body.classList.toggle("dark-theme", !light);
        buttons(light);
        if (light) loadInlineMap(function () { swapInline(true); });
    });

    document.addEventListener("click", function (e) {
        var btn = e.target.closest ? e.target.closest("[data-theme-toggle]") : null;
        if (!btn || always) return;
        e.preventDefault();
        var next = saved() === "light" ? "dark" : "light";
        try { localStorage.setItem(KEY, next); } catch (err) { /* private window: still switches for this page */ }
        apply(next);
        if (next === "light") buttons(true);
    });

    // another open tab changed it
    window.addEventListener("storage", function (e) { if (e.key === KEY) apply(saved()); });

    window.AppTheme = { apply: apply, current: saved };
})();
