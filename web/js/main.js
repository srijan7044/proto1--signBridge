// main.js — SignBridge main entry point and module orchestrator

import { initDOMElements, DOM, state } from "./state.js";
import { initCameraControls } from "./camera.js";
import { predictFrame, initRecognitionControls, loadLabelCount } from "./recognition.js";
import { initWordBuilder } from "./word-builder.js";
import { initAnimationControls, initSpeechRecognition } from "./animation.js";
import { initClerkAuth, initAuthControls } from "./auth.js";
import { initThemeToggle } from "./theme.js";
import { initPaymentControls } from "./payments.js";
import { initUsageTracking } from "./usage.js";
import { initLanguageSelector, loadUserLanguages } from "./language.js";
import { initCustomTraining } from "./custom-training.js";
import { initAdmin } from "./admin.js";

initDOMElements();
window.predictFrame = predictFrame;

initThemeToggle();

// ── Tab navigation ────────────────────────────────────────────────
const tabSignToVoice = document.getElementById("tab-sign-to-voice");
const tabVoiceToSign = document.getElementById("tab-voice-to-sign");
const modeSignToVoice = document.getElementById("mode-sign-to-voice");
const modeVoiceToSign = document.getElementById("mode-voice-to-sign");

if (tabSignToVoice) {
  tabSignToVoice.addEventListener("click", () => {
    tabSignToVoice.classList.add("active");
    tabVoiceToSign.classList.remove("active");
    modeSignToVoice.hidden = false;
    modeVoiceToSign.hidden = true;
  });
}

if (tabVoiceToSign) {
  tabVoiceToSign.addEventListener("click", () => {
    tabVoiceToSign.classList.add("active");
    tabSignToVoice.classList.remove("active");
    modeVoiceToSign.hidden = false;
    modeSignToVoice.hidden = true;
  });
}

// ── Module initialization ─────────────────────────────────────────
initCameraControls();
initRecognitionControls();
initWordBuilder();
initAnimationControls();
initSpeechRecognition();
initAuthControls();
initClerkAuth();
initPaymentControls();
initUsageTracking();
initLanguageSelector();
initCustomTraining();
initAdmin();

loadLabelCount();

// ── React to successful login via event ───────────────────────────
window.addEventListener("signbridge:user-unlocked", (e) => {
  const userData = e.detail || {};
  // Load available languages for this user
  loadUserLanguages();

  const email = (userData.email || "").toLowerCase();
  const role = userData.role || "";
  const isMasterAdmin = email === "offsray7044@gmail.com";
  const isAdmin = isMasterAdmin || role === "admin";

  // Show admin button only for authorized admins
  const adminBtn = document.getElementById("admin-btn");
  if (adminBtn) {
    adminBtn.hidden = !isAdmin;
  }

  // Ensure billing & training buttons remain accessible to all authenticated users
  const billingBtn = document.getElementById("billing-btn");
  if (billingBtn) {
    billingBtn.hidden = false;
  }
  const trainingBtn = document.getElementById("custom-training-btn");
  if (trainingBtn) {
    trainingBtn.hidden = false;
  }
});

// ── Robust User Profile Menu Dropdown Controller ──────────────────
let userMenuDropdownInitialized = false;

export function initUserMenuDropdown() {
  if (userMenuDropdownInitialized) {
    return;
  }
  userMenuDropdownInitialized = true;

  function getToggle() {
    return document.getElementById("user-menu-toggle");
  }

  function getMenu() {
    return document.getElementById("user-dropdown-menu");
  }

  function isMenuOpen() {
    const menu = getMenu();
    return !!(menu && !menu.hidden);
  }

  function openMenu() {
    const menu = getMenu();
    const toggle = getToggle();
    if (!menu || !toggle) return;

    menu.hidden = false;
    toggle.setAttribute("aria-expanded", "true");

    // Focus the first visible dropdown item for keyboard navigation
    const firstItem = menu.querySelector(".dropdown-item:not([hidden])");
    if (firstItem) {
      firstItem.focus();
    }
  }

  function closeMenu(restoreFocus = false) {
    const menu = getMenu();
    const toggle = getToggle();
    if (!menu) return;

    menu.hidden = true;
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      if (restoreFocus) {
        toggle.focus();
      }
    }
  }

  function toggleMenu() {
    if (isMenuOpen()) {
      closeMenu(false);
    } else {
      openMenu();
    }
  }

  // Delegated click handling so dynamic re-renders never detach listeners
  document.addEventListener("click", (e) => {
    const toggle = getToggle();
    const menu = getMenu();

    // 1. Click on the user menu toggle button
    if (toggle && (toggle === e.target || toggle.contains(e.target))) {
      e.preventDefault();
      e.stopPropagation();
      toggleMenu();
      return;
    }

    // 2. Click on a dropdown item
    const clickedItem = e.target.closest(".dropdown-item");
    if (clickedItem && menu && menu.contains(clickedItem)) {
      // Allow the item action handler to receive and process the click event, then close cleanly
      setTimeout(() => {
        closeMenu(false);
      }, 50);
      return;
    }

    // 3. Click outside the dropdown and toggle
    if (isMenuOpen()) {
      if (menu && !menu.contains(e.target)) {
        closeMenu(false);
      }
    }
  });

  // Comprehensive keyboard accessibility (Escape, Arrows, Home, End, Tab)
  document.addEventListener("keydown", (e) => {
    const toggle = getToggle();
    const menu = getMenu();

    // Opening via keyboard while focused on toggle
    if (!isMenuOpen()) {
      if (toggle && document.activeElement === toggle) {
        if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openMenu();
        }
      }
      return;
    }

    // When dropdown is open:
    if (e.key === "Escape") {
      e.preventDefault();
      closeMenu(true);
      return;
    }

    const visibleItems = Array.from(
      menu ? menu.querySelectorAll(".dropdown-item:not([hidden]):not(:disabled)") : []
    );
    if (!visibleItems.length) return;

    const currentIndex = visibleItems.indexOf(document.activeElement);

    if (e.key === "ArrowDown") {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % visibleItems.length;
      visibleItems[nextIndex].focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prevIndex = (currentIndex - 1 + visibleItems.length) % visibleItems.length;
      visibleItems[prevIndex].focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      visibleItems[0].focus();
    } else if (e.key === "End") {
      e.preventDefault();
      visibleItems[visibleItems.length - 1].focus();
    } else if (e.key === "Tab") {
      // Tab moves focus out of dropdown -> close menu
      closeMenu(false);
    }
  });

  // Close menu on logout / locking
  window.addEventListener("signbridge:user-locked", () => {
    closeMenu(false);
  });

  // Close menu if open on unlock / state change
  window.addEventListener("signbridge:user-unlocked", () => {
    closeMenu(false);
  });
}

// Initialize dropdown immediately or upon DOM readiness
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initUserMenuDropdown);
} else {
  initUserMenuDropdown();
}
