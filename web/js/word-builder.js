// word-builder.js — Letter-to-word construction engine

import { state, DOM, showError } from "./state.js";

export function addLetterToWordBuffer(letter) {
  if (!letter || letter.length !== 1) return;
  state.wordLetters.push(letter.toUpperCase());
  renderWordBuffer();
  queryWordConstruction();
}

export function renderWordBuffer() {
  if (!DOM["word-buffer-chips"]) return;
  if (state.wordLetters.length === 0) {
    DOM["word-buffer-chips"].innerHTML = '<span class="placeholder-chip">Sign letters to build a word...</span>';
    if (DOM["corrected-word"]) {
      DOM["corrected-word"].textContent = "—";
      DOM["corrected-word"].style.display = "none";
    }
    if (DOM["word-suggestions"]) {
      DOM["word-suggestions"].innerHTML = '<span class="no-suggestions">Waiting for letters...</span>';
    }
    state.currentCorrectedWord = "";
    return;
  }

  DOM["word-buffer-chips"].innerHTML = state.wordLetters
    .map((l) => `<span class="buffer-letter-chip">${l}</span>`)
    .join("");
  if (DOM["corrected-word"]) DOM["corrected-word"].style.display = "inline";
}

export async function queryWordConstruction() {
  if (state.wordLetters.length === 0) return;
  try {
    const res = await fetch("/api/gestures/word-construct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ letters: state.wordLetters }),
    });
    const data = await res.json();
    if (data.success && data.data) {
      const { raw, corrected, suggestions } = data.data;
      state.currentCorrectedWord = corrected || raw;
       if (DOM["corrected-word"]) {
        DOM["corrected-word"].textContent = state.currentCorrectedWord;
        DOM["corrected-word"].style.display = "inline";
      }

      if (DOM["word-suggestions"]) {
        if (suggestions && suggestions.length > 0) {
          DOM["word-suggestions"].innerHTML = suggestions
            .map(
              (s) => `<button type="button" class="word-suggestion-chip" data-word="${s}">${s}</button>`
            )
            .join("");

          DOM["word-suggestions"].querySelectorAll(".word-suggestion-chip").forEach((chip) => {
            chip.addEventListener("click", () => {
              commitWordToSentence(chip.dataset.word);
            });
          });
        } else {
          DOM["word-suggestions"].innerHTML = '<span class="no-suggestions">No dictionary matches</span>';
        }
      }
    }
  } catch (err) {
    console.error("Word construction query failed:", err);
  }
}

export function commitWordToSentence(wordToCommit) {
  const chosen = (wordToCommit || state.currentCorrectedWord || state.wordLetters.join("")).trim();
  if (!chosen) return;

  DOM.sentence.value = `${DOM.sentence.value.trim()} ${chosen}`.trim();
  DOM.sentence.classList.add("sentence-flash");
  setTimeout(() => DOM.sentence.classList.remove("sentence-flash"), 600);

  state.wordLetters = [];
  renderWordBuffer();
}

export async function polishGrammar() {
  const rawText = DOM.sentence.value.trim();
  if (!rawText) {
    showError("Please sign or build some words first.");
    return;
  }

  DOM["polish-grammar-btn"].disabled = true;
  DOM["polish-grammar-btn"].textContent = "✨ Synthesizing...";

  try {
    const res = await fetch("/api/gloss-to-sentence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gloss: rawText }),
    });
    const data = await res.json();
    if (data.sentence) {
      DOM.sentence.value = data.sentence;
      DOM.sentence.classList.add("sentence-flash");
      setTimeout(() => DOM.sentence.classList.remove("sentence-flash"), 600);

      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(data.sentence);
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  } catch (err) {
    console.error("Grammar polish failed:", err);
  } finally {
    DOM["polish-grammar-btn"].disabled = false;
    DOM["polish-grammar-btn"].textContent = "✨ AI Polish Grammar";
  }
}

export function initWordBuilder() {
  if (DOM["commit-word-btn"]) {
    DOM["commit-word-btn"].addEventListener("click", () => {
      commitWordToSentence();
    });
  }

  if (DOM["backspace-letter-btn"]) {
    DOM["backspace-letter-btn"].addEventListener("click", () => {
      if (state.wordLetters.length > 0) {
        state.wordLetters.pop();
        renderWordBuffer();
        if (state.wordLetters.length > 0) {
          queryWordConstruction();
        }
      }
    });
  }

  if (DOM["clear-word-btn"]) {
    DOM["clear-word-btn"].addEventListener("click", () => {
      state.wordLetters = [];
      renderWordBuffer();
    });
  }

  if (DOM["polish-grammar-btn"]) {
    DOM["polish-grammar-btn"].addEventListener("click", polishGrammar);
  }
}
