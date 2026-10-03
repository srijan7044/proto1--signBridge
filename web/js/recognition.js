// recognition.js — Sign-to-speech prediction and API calls

import { state, DOM, showError, clearError } from "./state.js";
import { addLetterToWordBuffer } from "./word-builder.js";

export async function predictFrame(blob) {
  clearError();
  const formData = new FormData();
  formData.append("image", blob, "frame.jpg");

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Prediction failed.");

    state.detectedLabel = data.label || "";
    if (state.detectedLabel) {
      DOM.result.textContent = state.detectedLabel;
      DOM.confidence.textContent = `Confidence: ${(data.confidence * 100).toFixed(1)}%`;

      if (state.detectedLabel === state.consecutiveSign) {
        state.consecutiveCount++;
      } else {
        state.consecutiveSign = state.detectedLabel;
        state.consecutiveCount = 1;
      }

      if (
        state.autoAddActive &&
        state.consecutiveCount === state.AUTO_ADD_STABILITY_THRESHOLD &&
        state.detectedLabel !== state.lastAppendedSign
      ) {
        state.lastAppendedSign = state.detectedLabel;

        if (state.detectedLabel.length === 1 && state.detectedLabel.match(/[A-Z]/i)) {
          addLetterToWordBuffer(state.detectedLabel.toUpperCase());
        } else {
          DOM.sentence.value = `${DOM.sentence.value.trim()} ${state.detectedLabel}`.trim();
          DOM.sentence.classList.add("sentence-flash");
          setTimeout(() => DOM.sentence.classList.remove("sentence-flash"), 600);
        }
      }

      if (
        state.autoSpeakActive &&
        state.consecutiveCount === state.AUTO_ADD_STABILITY_THRESHOLD &&
        state.detectedLabel !== window._lastAutoSpokenSign
      ) {
        window._lastAutoSpokenSign = state.detectedLabel;
        const utterance = new SpeechSynthesisUtterance(state.detectedLabel);
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);
      }
    } else {
      DOM.result.textContent = "No sign detected";
      DOM.confidence.textContent = "Keep hand steady and centered.";
      state.consecutiveSign = "";
      state.consecutiveCount = 0;
    }

    if (DOM.preview) {
      DOM.preview.hidden = true;
      DOM.preview.style.display = "none";
    }
  } catch (error) {
    if (!state.isRealtimeActive) showError(error.message);
  }
}

export function initRecognitionControls() {
  if (DOM["toggle-auto-add"]) {
    DOM["toggle-auto-add"].addEventListener("click", () => {
      state.autoAddActive = !state.autoAddActive;
      DOM["toggle-auto-add"].textContent = `✨ Auto-Add Signs to Sentence: ${state.autoAddActive ? "ON" : "OFF"}`;
      DOM["toggle-auto-add"].classList.toggle("primary-button", state.autoAddActive);
      DOM["toggle-auto-add"].classList.toggle("secondary-button", !state.autoAddActive);
      state.consecutiveSign = "";
      state.consecutiveCount = 0;
    });
  }

  if (DOM["toggle-auto-speak"]) {
    DOM["toggle-auto-speak"].addEventListener("click", () => {
      state.autoSpeakActive = !state.autoSpeakActive;
      DOM["toggle-auto-speak"].textContent = `🔊 Auto-Speak Confirmed Signs: ${state.autoSpeakActive ? "ON" : "OFF"}`;
      DOM["toggle-auto-speak"].classList.toggle("primary-button", state.autoSpeakActive);
      DOM["toggle-auto-speak"].classList.toggle("secondary-button", !state.autoSpeakActive);
    });
  }

  if (DOM["delete-word"]) {
    DOM["delete-word"].addEventListener("click", () => {
      DOM.sentence.value = DOM.sentence.value.trim().split(/\s+/).slice(0, -1).join(" ");
    });
  }

  if (DOM.clear) {
    DOM.clear.addEventListener("click", () => {
      DOM.sentence.value = "";
      DOM.result.textContent = "No sign yet";
      DOM.confidence.textContent = "Start camera or upload an image.";
      state.consecutiveSign = "";
      state.consecutiveCount = 0;
      state.lastAppendedSign = "";
      window._lastAutoSpokenSign = "";
    });
  }

  if (DOM.speak) {
    DOM.speak.addEventListener("click", () => {
      const text = DOM.sentence.value;
      if (!text || !text.trim()) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text.trim());
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    });
  }
}

export function loadLabelCount() {
  fetch("/api/labels")
    .then((res) => res.json())
    .then((data) => {
      if (data.labels && DOM["label-count"]) {
        DOM["label-count"].textContent = `${data.labels.length} Signs Trained`;
      }
    })
    .catch(() => {
      if (DOM["label-count"]) DOM["label-count"].textContent = "Model Active";
    });
}
