// language.js — Language selector with entitlement checks

import { state, DOM, showError } from "./state.js";

export async function loadUserLanguages() {
  const token = localStorage.getItem("signbridge_token") || "";
  try {
    const res = await fetch("/api/language/list", {
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
      },
    });
    const data = await res.json();
    if (data.success && data.data) {
      renderLanguageSelector(data.data.languages);
      return data.data.languages;
    }
  } catch (err) {
    console.error("Failed to load languages:", err);
  }
  return [];
}

function renderLanguageSelector(languages) {
  if (!DOM["language-selector-btn"] || !DOM["language-list"]) return;

  // Show language selector for authenticated users with premium/lifetime
  if (state.currentUser && (state.currentUser.plan === "premium" || state.currentUser.plan === "lifetime")) {
    DOM["language-selector-btn"].hidden = false;
  } else {
    DOM["language-selector-btn"].hidden = true;
  }

  // Populate language list in modal
  DOM["language-list"].innerHTML = languages.map(lang => {
    const isCurrent = state.currentUser?.preferences?.preferred_language === lang.id;
    const isLocked = lang.required_entitlement !== "free" && 
                     state.currentUser && 
                     state.currentUser.plan === "free";

    return `
      <div class="language-item ${isCurrent ? 'current' : ''} ${isLocked ? 'locked' : ''}" 
           data-lang="${lang.id}" 
           ${isLocked ? 'data-locked="true"' : ''}>
        <span class="language-flag">${getFlag(lang.country)}</span>
        <div class="language-info">
          <span class="language-name">${lang.name}</span>
          <span class="language-native">${lang.native_name}</span>
          <span class="language-variant">${lang.variant}</span>
        </div>
        ${isCurrent ? '<span class="language-check">✓</span>' : ''}
        ${isLocked ? '<span class="language-lock">🔒</span>' : ''}
      </div>
    `;
  }).join('');

  // Add click handlers
  DOM["language-list"].querySelectorAll(".language-item").forEach(item => {
    item.addEventListener("click", () => {
      const langId = item.dataset.lang;
      const isLocked = item.dataset.locked === "true";
      if (isLocked) {
        showLanguageUpgradeMessage(langId);
      } else {
        switchLanguage(langId);
      }
    });
  });
}

function getFlag(countryCode) {
  if (!countryCode) return "🌐";
  const codePoints = countryCode.toUpperCase().split('').map(char => 0x1F1E6 + char.charCodeAt(0) - 65);
  return String.fromCodePoint(...codePoints);
}

async function switchLanguage(languageId) {
  const token = localStorage.getItem("signbridge_token") || "";
  try {
    const res = await fetch("/api/language/switch", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
      },
      body: JSON.stringify({ language_id: languageId }),
    });
    const data = await res.json();
    if (data.success) {
      // Update UI
      if (DOM["current-language-name"]) {
        const lang = data.data.language;
        DOM["current-language-name"].textContent = lang.name;
        DOM["current-language-flag"].textContent = getFlag(lang.country);
      }
      // Update user preferences in state
      if (state.currentUser) {
        state.currentUser.preferences = state.currentUser.preferences || {};
        state.currentUser.preferences.preferred_language = languageId;
        localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
      }
      hideLanguageModal();
      showError(`Language switched to ${data.data.language.name}`);
    } else {
      showError(data.error || "Failed to switch language");
    }
  } catch (err) {
    console.error("Failed to switch language:", err);
    showError("Failed to switch language");
  }
}

function showLanguageUpgradeMessage(languageId) {
  if (!DOM["language-upgrade-message"]) return;
  
  DOM["language-upgrade-message"].hidden = false;
  DOM["language-upgrade-message"].innerHTML = `
    <p>This language requires a Premium or Lifetime subscription.</p>
    <button class="primary-button btn-sm" onclick="initiateStripeCheckout('premium')">Upgrade to Premium</button>
    <button class="secondary-button btn-sm" onclick="initiateStripeCheckout('lifetime')">Get Lifetime Access</button>
  `;
}

export function showLanguageModal() {
  if (DOM["language-modal"]) DOM["language-modal"].hidden = false;
}

export function hideLanguageModal() {
  if (DOM["language-modal"]) DOM["language-modal"].hidden = true;
  if (DOM["language-upgrade-message"]) DOM["language-upgrade-message"].hidden = true;
}

export function initLanguageSelector() {
  // Language selector button
  if (DOM["language-selector-btn"]) {
    DOM["language-selector-btn"].addEventListener("click", showLanguageModal);
  }

  // Close buttons
  if (DOM["language-modal-close"]) {
    DOM["language-modal-close"].addEventListener("click", hideLanguageModal);
  }

  if (DOM["language-modal"]) {
    DOM["language-modal"].addEventListener("click", (e) => {
      if (e.target === DOM["language-modal"]) hideLanguageModal();
    });
  }

  // Load languages on auth
  loadUserLanguages();
}