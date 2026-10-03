// animation.js — Sign language skeleton animation renderer

import { state, DOM, clearError, showError, HAND_CONNECTIONS } from "./state.js";

export function drawFrame(frameVector) {
  const ctx = DOM["sign-canvas"].getContext("2d");
  const w = DOM["sign-canvas"].width;
  const h = DOM["sign-canvas"].height;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#090d16";
  ctx.fillRect(0, 0, w, h);

  if (!frameVector || frameVector.length < 126) return;

  const hasLeft = frameVector.slice(0, 63).some((v) => Math.abs(v) > 1e-4);
  const hasRight = frameVector.slice(63, 126).some((v) => Math.abs(v) > 1e-4);

  let offsets = [[w * 0.35, h * 0.72], [w * 0.65, h * 0.72]];
  if (!hasLeft && hasRight) {
    offsets[1] = [w * 0.5, h * 0.72];
  } else if (hasLeft && !hasRight) {
    offsets[0] = [w * 0.5, h * 0.72];
  }

  const scale = 110;

  for (let slot = 0; slot < 2; slot++) {
    const start = slot * 63;
    const chunk = frameVector.slice(start, start + 63);
    const hasData = chunk.some((v) => Math.abs(v) > 1e-4);
    if (!hasData) continue;

    const points = [];
    for (let i = 0; i < 21; i++) {
      const x = chunk[i * 3];
      const y = chunk[i * 3 + 1];
      const px = offsets[slot][0] + x * scale;
      const py = offsets[slot][1] + y * scale;
      points.push({ x: px, y: py });
    }

    ctx.strokeStyle = slot === 0 ? "#38bdf8" : "#818cf8";
    ctx.lineWidth = 3.5;
    HAND_CONNECTIONS.forEach(([a, b]) => {
      ctx.beginPath();
      ctx.moveTo(points[a].x, points[a].y);
      ctx.lineTo(points[b].x, points[b].y);
      ctx.stroke();
    });

    points.forEach((pt) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4.5, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
    });
  }

  let currentWord = "";
  for (const span of state.animSpans) {
    if (state.animIndex >= span.start && state.animIndex < span.end) {
      currentWord = span.word;
      break;
    }
  }
  if (DOM["canvas-overlay-caption"]) {
    DOM["canvas-overlay-caption"].textContent = currentWord || "Sign Language";
  }
}

export function startAnimationPlayback() {
  clearTimeout(state.animTimer);
  state.animPlaying = true;
  DOM["play-pause-btn"].textContent = "⏸ Pause";
  stepAnimation();
}

export function stepAnimation() {
  if (!state.animPlaying || state.animFrames.length === 0) return;

  drawFrame(state.animFrames[state.animIndex]);
  state.animIndex = (state.animIndex + 1) % state.animFrames.length;

  const speed = parseFloat(DOM["speed-select"].value) || 1.0;
  const interval = 50 / speed;
  clearTimeout(state.animTimer);
  state.animTimer = setTimeout(stepAnimation, interval);
}

export async function generateSignAnimation(text) {
  if (!text || !text.trim()) return showError("Please enter or speak a sentence first.");
  clearError();
  DOM["generate-sign-btn"].disabled = true;
  DOM["generate-sign-btn"].textContent = "⏳ Generating Animation...";

  try {
    const response = await fetch("/api/text-to-sign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sentence: text }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Generation failed.");

    state.animFrames = data.frames || [];
    state.animSpans = data.spans || [];

    if (DOM["gloss-badge"]) {
      DOM["gloss-badge"].textContent = `Gloss: ${data.gloss ? data.gloss.join(" • ") : "None"}`;
    }

    if (DOM["gloss-list"]) {
      DOM["gloss-list"].innerHTML = "";
      (data.gloss || []).forEach((word) => {
        const pill = document.createElement("span");
        pill.className = "gloss-pill";
        pill.textContent = word;
        DOM["gloss-list"].appendChild(pill);
      });
    }

    if (state.animFrames.length > 0) {
      state.animIndex = 0;
      DOM["play-pause-btn"].disabled = false;
      DOM["restart-btn"].disabled = false;
      startAnimationPlayback();
    } else {
      if (DOM["canvas-overlay-caption"]) {
        DOM["canvas-overlay-caption"].textContent = "No sign animation generated";
      }
    }
  } catch (error) {
    showError(error.message);
  } finally {
    DOM["generate-sign-btn"].disabled = false;
    DOM["generate-sign-btn"].textContent = "✨ Render Sign Language Animation";
  }
}

export function initAnimationControls() {
  document.querySelectorAll(".phrase-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      DOM["tts-input"].value = chip.textContent;
      generateSignAnimation(chip.textContent);
    });
  });

  if (DOM["generate-sign-btn"]) {
    DOM["generate-sign-btn"].addEventListener("click", () => {
      generateSignAnimation(DOM["tts-input"].value);
    });
  }

  if (DOM["play-pause-btn"]) {
    DOM["play-pause-btn"].addEventListener("click", () => {
      state.animPlaying = !state.animPlaying;
      if (state.animPlaying) {
        DOM["play-pause-btn"].textContent = "⏸ Pause";
        stepAnimation();
      } else {
        DOM["play-pause-btn"].textContent = "▶ Play";
        clearTimeout(state.animTimer);
      }
    });
  }

  if (DOM["restart-btn"]) {
    DOM["restart-btn"].addEventListener("click", () => {
      clearTimeout(state.animTimer);
      state.animIndex = 0;
      startAnimationPlayback();
    });
  }
}

export function initSpeechRecognition() {
  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    if (DOM["mic-btn"]) {
      DOM["mic-btn"].addEventListener("click", () => {
        showError("Speech recognition is not supported in this browser. Please type your message into the text box below.");
        DOM["tts-input"].focus();
      });
    }
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  state.speechRecognition = new SpeechRecognition();
  state.speechRecognition.continuous = false;
  state.speechRecognition.interimResults = true;
  state.speechRecognition.lang = "en-US";
  let isListening = false;

  state.speechRecognition.onstart = () => {
    isListening = true;
    DOM["mic-btn"].classList.add("listening");
    DOM["mic-btn"].textContent = "🎙️ Listening... Speak now!";
    clearError();
  };

  state.speechRecognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript;
    }
    DOM["tts-input"].value = transcript;
    if (event.results[0].isFinal && transcript.trim()) {
      generateSignAnimation(transcript);
    }
  };

  state.speechRecognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    isListening = false;
    DOM["mic-btn"].classList.remove("listening");
    DOM["mic-btn"].textContent = "🎤 Voice Input";

    if (event.error === "network") {
      showError(
        "Voice Input Network Error: Chrome's voice recognition requires an active internet connection. " +
        "Please check your connection/VPN, or type your message directly into the text box below!"
      );
      DOM["tts-input"].focus();
    } else if (event.error === "not-allowed" || event.error === "permission-denied") {
      showError("Microphone permission was denied. Please allow microphone access in your browser location bar.");
    } else if (event.error === "no-speech") {
      showError("No speech detected. Please try clicking 'Voice Input' again and speak clearly.");
    } else if (event.error === "aborted") {
      // Silently ignore abort
    } else {
      showError(`Voice input error (${event.error}). Please type your sentence in the box.`);
    }
  };

  state.speechRecognition.onend = () => {
    isListening = false;
    DOM["mic-btn"].classList.remove("listening");
    DOM["mic-btn"].textContent = "🎤 Voice Input";
  };

  if (DOM["mic-btn"]) {
    DOM["mic-btn"].addEventListener("click", () => {
      clearError();
      if (isListening) {
        state.speechRecognition.stop();
      } else {
        try {
          state.speechRecognition.start();
        } catch (err) {
          console.warn("Speech recognition start issue:", err);
        }
      }
    });
  }
}
