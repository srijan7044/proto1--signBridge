// theme.js — Centralized theme management and persistence for SignBridge

export const THEME_STORAGE_KEY = "signbridge_theme";

/**
 * Retrieves the saved theme from localStorage.
 * Priority:
 * 1. Saved preference in localStorage ("signbridge_theme" or fallback "theme")
 * 2. Light Theme (default for new / unset users)
 * Operating-system preferences do NOT override the explicit saved choice or the default.
 */
export function getSavedTheme() {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY) || localStorage.getItem("theme");
    if (saved === "dark" || saved === "light") {
      return saved;
    }
  } catch (_) {}
  return "light";
}

/**
 * Applies the given theme to the document and optionally persists it.
 * @param {"light"|"dark"} theme 
 * @param {boolean} save Whether to persist to localStorage (default true)
 */
export function applyTheme(theme, save = true) {
  const resolved = theme === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", resolved);
  document.documentElement.dataset.theme = resolved;

  if (save) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, resolved);
    } catch (_) {}
  }

  // Update theme meta tag if present
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  if (metaTheme) {
    metaTheme.setAttribute("content", resolved === "dark" ? "#0b0f19" : "#f8fafc");
  }

  // Update all theme toggle buttons across the page
  const toggles = document.querySelectorAll("#theme-toggle, .theme-toggle-btn");
  toggles.forEach((btn) => {
    btn.textContent = resolved === "dark" ? "☀️ Light theme" : "🌙 Dark theme";
    btn.setAttribute("aria-pressed", String(resolved === "dark"));
  });

  // Notify components and integrations (e.g. Clerk, Canvas, Charts)
  window.dispatchEvent(
    new CustomEvent("signbridge:theme-changed", {
      detail: { theme: resolved },
    }),
  );

  return resolved;
}

let lastToggleTime = 0;

/**
 * Toggles between light and dark themes and persists the selection.
 * Protected by a debounce guard so rapid or duplicate triggers cannot cancel each other out.
 */
export function toggleTheme() {
  const now = Date.now();
  if (now - lastToggleTime < 200) {
    return document.documentElement.getAttribute("data-theme") || getSavedTheme();
  }
  lastToggleTime = now;

  const current = document.documentElement.getAttribute("data-theme") || getSavedTheme();
  const next = current === "dark" ? "light" : "dark";
  return applyTheme(next, true);
}

/**
 * Sets up the theme toggle button and initializes the theme state.
 */
export function initThemeToggle() {
  // Ensure the correct theme is applied immediately on initialization
  const initialTheme = getSavedTheme();
  applyTheme(initialTheme, false);

  // Prevent multiple click listeners across different module instances or loads
  if (!window.__SIGNBRIDGE_THEME_LISTENER_ATTACHED__) {
    window.__SIGNBRIDGE_THEME_LISTENER_ATTACHED__ = true;

    document.addEventListener("click", (e) => {
      const toggleBtn = e.target.closest("#theme-toggle, .theme-toggle-btn");
      if (toggleBtn) {
        e.preventDefault();
        toggleTheme();
      }
    });
  }

  // Expose on window for inline handlers, test suites, and console verification
  window.applyTheme = applyTheme;
  window.getSavedTheme = getSavedTheme;
  window.toggleTheme = toggleTheme;
}

// Initialize theme immediately upon module loading
initThemeToggle();
