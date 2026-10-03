// theme.js — Theme toggle functionality

export function initThemeToggle() {
  const themeToggle = document.getElementById("theme-toggle");
  if (!themeToggle) return;

  const currentTheme =
    document.documentElement.getAttribute("data-theme") ||
    document.documentElement.dataset.theme ||
    "light";
  themeToggle.textContent =
    currentTheme === "dark" ? "☀️ Light theme" : "🌙 Dark theme";
  themeToggle.setAttribute("aria-pressed", String(currentTheme === "light"));

  themeToggle.addEventListener("click", () => {
    const currentTheme =
      document.documentElement.getAttribute("data-theme") ||
      document.documentElement.dataset.theme ||
      "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    document.documentElement.dataset.theme = newTheme;
    themeToggle.textContent =
      newTheme === "dark" ? "☀️ Light theme" : "🌙 Dark theme";
    themeToggle.setAttribute("aria-pressed", String(newTheme === "light"));

    window.dispatchEvent(
      new CustomEvent("signbridge:theme-changed", {
        detail: { theme: newTheme },
      }),
    );
  });
}

initThemeToggle();
