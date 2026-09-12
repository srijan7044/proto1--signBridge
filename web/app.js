// --- STATE & DOM ELEMENTS ---
const camera = document.querySelector("#camera");
const cameraCanvas = document.querySelector("#camera-canvas");
const preview = document.querySelector("#preview");
const upload = document.querySelector("#upload");
const cameraToggle = document.querySelector("#camera-toggle");
const cameraToggleText = document.querySelector("#camera-toggle-text");
const toggleRealtime = document.querySelector("#toggle-realtime");
const capture = document.querySelector("#capture");
const addSign = document.querySelector("#add-sign");
const toggleAutoAdd = document.querySelector("#toggle-auto-add");
const toggleAutoSpeak = document.querySelector("#toggle-auto-speak");
const result = document.querySelector("#result");
const confidence = document.querySelector("#confidence");
const sentence = document.querySelector("#sentence");
const alertBox = document.querySelector("#alert");
const cameraStatus = document.querySelector("#camera-status");
const themeToggle = document.querySelector("#theme-toggle");

// Mode Tabs
const tabSignToVoice = document.querySelector("#tab-sign-to-voice");
const tabVoiceToSign = document.querySelector("#tab-voice-to-sign");
const modeSignToVoice = document.querySelector("#mode-sign-to-voice");
const modeVoiceToSign = document.querySelector("#mode-voice-to-sign");

// Mode 2 Elements
const ttsInput = document.querySelector("#tts-input");
const micBtn = document.querySelector("#mic-btn");
const generateSignBtn = document.querySelector("#generate-sign-btn");
const signCanvas = document.querySelector("#sign-canvas");
const canvasCaption = document.querySelector("#canvas-overlay-caption");
const playPauseBtn = document.querySelector("#play-pause-btn");
const restartBtn = document.querySelector("#restart-btn");
const speedSelect = document.querySelector("#speed-select");
const glossBadge = document.querySelector("#gloss-badge");
const glossList = document.querySelector("#gloss-list");

let detectedLabel = "";
let cameraStream = null;
let realtimeInterval = null;
let isRealtimeActive = false;
let autoSpeakActive = false;
let autoAddActive = true;
let speechRecognition = null;

// Word Buffer & Smart Suggestion Elements
const wordBufferContainer = document.querySelector("#word-buffer-container");
const wordBufferText = document.querySelector("#word-buffer-text");
const commitWordBtn = document.querySelector("#commit-word-btn");
const clearWordBtn = document.querySelector("#clear-word-btn");
const smartChipsList = document.querySelector("#smart-chips-list");
const grammarBtn = document.querySelector("#grammar-btn");

let wordBuffer = "";
let bufferInactivityTimer = null;
const BUFFER_INACTIVITY_MS = 1400;

// Stability tracking for auto-add and auto-speak
let _consecutiveSign = "";
let _consecutiveCount = 0;
let _lastAppendedSign = "";
const AUTO_ADD_STABILITY_THRESHOLD = 3;

// Animation playback state
let animFrames = [];
let animSpans = [];
let animIndex = 0;
let animPlaying = false;
let animTimer = null;

// MediaPipe Hand Connections indexing
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],       // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8],       // Index
  [5, 9], [9, 10], [10, 11], [11, 12],  // Middle
  [9, 13], [13, 14], [14, 15], [15, 16], // Ring
  [13, 17], [0, 17], [17, 18], [18, 19], [19, 20] // Pinky
];

// --- HELPER FUNCTIONS ---
function showError(message) {
  alertBox.textContent = message;
  alertBox.hidden = false;
}

function clearError() {
  alertBox.hidden = true;
  alertBox.textContent = "";
}

function speakText(text) {
  if (!text || !text.trim()) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text.trim());
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}

// --- WORD BUFFER & SMART SUGGESTIONS HELPERS ---
function updateWordBufferUI() {
  if (!wordBufferContainer || !wordBufferText) return;
  if (wordBuffer.length > 0) {
    wordBufferContainer.hidden = false;
    wordBufferContainer.style.display = "flex";
    wordBufferText.textContent = wordBuffer.split("").join(" - ");
  } else {
    wordBufferContainer.hidden = true;
    wordBufferContainer.style.display = "none";
    wordBufferText.textContent = "";
  }
}

function commitWordBuffer() {
  if (!wordBuffer || !wordBuffer.trim()) return;
  const word = wordBuffer.trim();
  sentence.value = `${sentence.value.trim()} ${word}`.trim();
  flashSentenceBox();
  if (autoSpeakActive) {
    speakText(word);
  }
  wordBuffer = "";
  if (bufferInactivityTimer) clearTimeout(bufferInactivityTimer);
  bufferInactivityTimer = null;
  updateWordBufferUI();
  fetchSmartSuggestions(sentence.value);
}

function clearWordBuffer() {
  wordBuffer = "";
  if (bufferInactivityTimer) clearTimeout(bufferInactivityTimer);
  bufferInactivityTimer = null;
  updateWordBufferUI();
}

async function fetchSmartSuggestions(glossText) {
  if (!glossText || !glossText.trim()) return;
  try {
    const res = await fetch("/api/gloss-to-sentence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gloss: glossText }),
    });
    const data = await res.json();
    if (data.suggestions && data.suggestions.length > 0) {
      renderSmartChips(data.suggestions);
    }
  } catch (err) {
    console.warn("Could not fetch suggestions:", err);
  }
}

function renderSmartChips(suggestions) {
  if (!smartChipsList) return;
  smartChipsList.innerHTML = "";
  suggestions.forEach((text) => {
    const chip = document.createElement("button");
    chip.className = "smart-chip";
    chip.type = "button";
    chip.textContent = text;
    chip.addEventListener("click", () => {
      sentence.value = text;
      flashSentenceBox();
      speakText(text);
    });
    smartChipsList.appendChild(chip);
  });
}

async function autoFixGrammar() {
  const currentText = sentence.value.trim();
  if (!currentText) return showError("Please sign or enter words first before fixing grammar.");
  clearError();
  try {
    const res = await fetch("/api/gloss-to-sentence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gloss: currentText }),
    });
    const data = await res.json();
    if (data.sentence) {
      sentence.value = data.sentence;
      flashSentenceBox();
      if (data.suggestions) renderSmartChips(data.suggestions);
    }
  } catch (err) {
    showError("Grammar fix failed: " + err.message);
  }
}

// --- TAB SWITCHING ---
tabSignToVoice.addEventListener("click", () => {
  tabSignToVoice.classList.add("active");
  tabVoiceToSign.classList.remove("active");
  modeSignToVoice.hidden = false;
  modeVoiceToSign.hidden = true;
});

tabVoiceToSign.addEventListener("click", () => {
  tabVoiceToSign.classList.add("active");
  tabSignToVoice.classList.remove("active");
  modeVoiceToSign.hidden = false;
  modeSignToVoice.hidden = true;
});

// --- MODE 1: SIGN TO SPEECH ---
async function predictFrame(blob) {
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

    detectedLabel = data.label || "";
    if (detectedLabel) {
      result.textContent = detectedLabel;
      confidence.textContent = `Confidence: ${(data.confidence * 100).toFixed(1)}%`;
      if (addSign) addSign.disabled = false;

      // Track consecutive stable predictions
      if (detectedLabel === _consecutiveSign) {
        _consecutiveCount++;
      } else {
        _consecutiveSign = detectedLabel;
        _consecutiveCount = 1;
      }

      // Auto-add logic when stable
      if (
        autoAddActive &&
        _consecutiveCount === AUTO_ADD_STABILITY_THRESHOLD &&
        detectedLabel !== _lastAppendedSign
      ) {
        _lastAppendedSign = detectedLabel;

        const isLetter = detectedLabel.length === 1 && /^[A-Z]$/i.test(detectedLabel);

        if (isLetter) {
          // Accumulate letter into Word Buffer
          wordBuffer += detectedLabel.toUpperCase();
          updateWordBufferUI();
          if (bufferInactivityTimer) clearTimeout(bufferInactivityTimer);
          bufferInactivityTimer = setTimeout(commitWordBuffer, BUFFER_INACTIVITY_MS);
        } else {
          // Full-word gesture (e.g. HELLO, THANKS, HELP, WATER)
          if (wordBuffer) {
            commitWordBuffer();
          }
          sentence.value = `${sentence.value.trim()} ${detectedLabel}`.trim();
          flashSentenceBox();
          if (autoSpeakActive) {
            speakText(detectedLabel);
          }
          fetchSmartSuggestions(sentence.value);
        }
      }
    } else {
      result.textContent = "No sign detected";
      confidence.textContent = "Keep hand steady and centered.";
      if (addSign) addSign.disabled = true;
      _consecutiveSign = "";
      _consecutiveCount = 0;
    }

    if (data.image && data.label) {
      preview.src = `data:image/jpeg;base64,${data.image}`;
      preview.hidden = false;
      preview.style.display = "block";
    } else {
      preview.hidden = true;
      preview.style.display = "none";
    }
  } catch (error) {
    if (!isRealtimeActive) showError(error.message);
  }
}

const cameraOffOverlay = document.querySelector("#camera-off-overlay");
let isCameraOn = false;
let isCameraStarting = false;

function startRealtimeTracking() {
  if (isRealtimeActive) return;
  isRealtimeActive = true;
  toggleRealtime.textContent = "⚡ Live Tracking: ON";
  toggleRealtime.classList.add("primary-button");
  toggleRealtime.classList.remove("secondary-button");
  realtimeInterval = setInterval(() => {
    if (!camera || !camera.videoWidth) return;
    const w = camera.videoWidth || 640;
    const h = camera.videoHeight || 480;
    cameraCanvas.width = w;
    cameraCanvas.height = h;
    const ctx = cameraCanvas.getContext("2d");
    ctx.drawImage(camera, 0, 0, w, h);
    cameraCanvas.toBlob((blob) => {
      if (blob && isRealtimeActive) predictFrame(blob);
    }, "image/jpeg", 0.85);
  }, 350);
}

function stopRealtimeTracking() {
  isRealtimeActive = false;
  if (realtimeInterval) clearInterval(realtimeInterval);
  realtimeInterval = null;
  toggleRealtime.textContent = "⚡ Live Tracking: OFF";
  toggleRealtime.classList.remove("primary-button");
  toggleRealtime.classList.add("secondary-button");
  if (preview) {
    preview.hidden = true;
    preview.style.display = "none";
  }
}

async function turnCameraOn() {
  if (isCameraStarting || isCameraOn) return;
  isCameraStarting = true;
  clearError();
  try {
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop());
      cameraStream = null;
    }
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    camera.srcObject = cameraStream;
    camera.hidden = false;
    camera.style.display = "block";
    await camera.play();

    if (cameraOffOverlay) {
      cameraOffOverlay.hidden = true;
      cameraOffOverlay.style.display = "none";
    }

    camera.onloadedmetadata = () => {
      cameraStatus.textContent = `Camera Active (${camera.videoWidth}x${camera.videoHeight})`;
      cameraStatus.className = "status-badge status-online";
    };

    isCameraOn = true;
    capture.disabled = false;
    toggleRealtime.disabled = false;
    cameraStatus.textContent = "Camera Active";
    cameraStatus.className = "status-badge status-online";

    if (cameraToggle) cameraToggle.checked = true;
    if (cameraToggleText) cameraToggleText.textContent = "Camera: ON";

    // Automatically activate live tracking so hand mapping dots appear immediately!
    startRealtimeTracking();
  } catch (error) {
    showError("Camera access denied or unavailable: " + error.message);
    turnCameraOff();
  } finally {
    isCameraStarting = false;
  }
}

function turnCameraOff() {
  stopRealtimeTracking();

  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }

  camera.srcObject = null;
  camera.hidden = true;
  camera.style.display = "none";
  if (preview) {
    preview.hidden = true;
    preview.style.display = "none";
    preview.src = "";
  }
  if (cameraOffOverlay) {
    cameraOffOverlay.hidden = false;
    cameraOffOverlay.style.display = "flex";
  }

  isCameraOn = false;
  capture.disabled = true;
  toggleRealtime.disabled = true;
  cameraStatus.textContent = "Camera OFF";
  cameraStatus.className = "status-badge status-offline";

  if (cameraToggle) cameraToggle.checked = false;
  if (cameraToggleText) cameraToggleText.textContent = "Camera: OFF";
}

if (cameraToggle) {
  cameraToggle.addEventListener("change", () => {
    if (cameraToggle.checked) {
      turnCameraOn();
    } else {
      turnCameraOff();
    }
  });
}

toggleRealtime.addEventListener("click", () => {
  if (isRealtimeActive) {
    stopRealtimeTracking();
  } else {
    startRealtimeTracking();
  }
});

capture.addEventListener("click", () => {
  clearError();
  if (!cameraStream || !camera.srcObject) {
    return showError("Please start the camera first by clicking 'Start Camera'.");
  }

  const w = camera.videoWidth || 640;
  const h = camera.videoHeight || 480;
  cameraCanvas.width = w;
  cameraCanvas.height = h;
  const ctx = cameraCanvas.getContext("2d");
  ctx.drawImage(camera, 0, 0, w, h);

  result.textContent = "Capturing & Analyzing...";
  confidence.textContent = "Processing frame...";

  cameraCanvas.toBlob(
    (blob) => {
      if (!blob) return showError("Failed to capture image frame from camera.");
      predictFrame(blob);
    },
    "image/jpeg",
    0.95
  );
});

upload.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) predictFrame(file);
});

if (addSign) {
  addSign.addEventListener("click", () => {
    if (detectedLabel) {
      sentence.value = `${sentence.value.trim()} ${detectedLabel}`.trim();
    }
  });
}

if (toggleAutoAdd) {
  toggleAutoAdd.addEventListener("click", () => {
    autoAddActive = !autoAddActive;
    toggleAutoAdd.textContent = `✨ Auto-Add Signs to Sentence: ${autoAddActive ? "ON" : "OFF"}`;
    toggleAutoAdd.classList.toggle("primary-button", autoAddActive);
    toggleAutoAdd.classList.toggle("secondary-button", !autoAddActive);
    _consecutiveSign = "";
    _consecutiveCount = 0;
  });
}

toggleAutoSpeak.addEventListener("click", () => {
  autoSpeakActive = !autoSpeakActive;
  toggleAutoSpeak.textContent = `🔊 Auto-Speak Confirmed Signs: ${autoSpeakActive ? "ON" : "OFF"}`;
  toggleAutoSpeak.classList.toggle("primary-button", autoSpeakActive);
  toggleAutoSpeak.classList.toggle("secondary-button", !autoSpeakActive);
});

if (commitWordBtn) {
  commitWordBtn.addEventListener("click", commitWordBuffer);
}

if (clearWordBtn) {
  clearWordBtn.addEventListener("click", clearWordBuffer);
}

if (grammarBtn) {
  grammarBtn.addEventListener("click", autoFixGrammar);
}

document.querySelector("#delete-word").addEventListener("click", () => {
  sentence.value = sentence.value.trim().split(/\s+/).slice(0, -1).join(" ");
  fetchSmartSuggestions(sentence.value);
});

document.querySelector("#clear").addEventListener("click", () => {
  sentence.value = "";
  result.textContent = "No sign yet";
  confidence.textContent = "Start camera or upload an image.";
  if (addSign) addSign.disabled = true;
  _consecutiveSign = "";
  _consecutiveCount = 0;
  _lastAppendedSign = "";
  window._lastAutoSpokenSign = "";
  clearWordBuffer();
  fetchSmartSuggestions("");
});

document.querySelector("#speak").addEventListener("click", () => {
  speakText(sentence.value);
});

// Initialize default smart suggestion chips
fetchSmartSuggestions("");

// --- MODE 2: VOICE & TEXT TO SIGN ---
// Quick Phrase Chips
document.querySelectorAll(".phrase-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    ttsInput.value = chip.textContent;
    generateSignAnimation(chip.textContent);
  });
});

// Web Speech API Voice Input
let isListening = false;

if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = false;
  speechRecognition.interimResults = true;
  speechRecognition.lang = "en-US";

  speechRecognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    micBtn.textContent = "🎙️ Listening... Speak now!";
    clearError();
  };

  speechRecognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript;
    }
    ttsInput.value = transcript;
    if (event.results[0].isFinal && transcript.trim()) {
      generateSignAnimation(transcript);
    }
  };

  speechRecognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    isListening = false;
    micBtn.classList.remove("listening");
    micBtn.textContent = "🎤 Voice Input";

    if (event.error === "network") {
      showError(
        "Voice Input Network Error: Chrome's voice recognition requires an active internet connection. " +
        "Please check your connection/VPN, or type your message directly into the text box below!"
      );
      ttsInput.focus();
    } else if (event.error === "not-allowed" || event.error === "permission-denied") {
      showError("Microphone permission was denied. Please allow microphone access in your browser location bar.");
    } else if (event.error === "no-speech") {
      showError("No speech detected. Please try clicking 'Voice Input' again and speak clearly.");
    } else if (event.error === "aborted") {
      // User or system stopped listening silently
    } else {
      showError(`Voice input error (${event.error}). Please type your sentence in the box.`);
    }
  };

  speechRecognition.onend = () => {
    isListening = false;
    micBtn.classList.remove("listening");
    micBtn.textContent = "🎤 Voice Input";
  };

  micBtn.addEventListener("click", () => {
    clearError();
    if (isListening) {
      speechRecognition.stop();
    } else {
      try {
        speechRecognition.start();
      } catch (err) {
        console.warn("Speech recognition start issue:", err);
      }
    }
  });
} else {
  micBtn.addEventListener("click", () => {
    showError("Speech recognition is not supported in this browser. Please type your message into the text box below.");
    ttsInput.focus();
  });
}



generateSignBtn.addEventListener("click", () => {
  generateSignAnimation(ttsInput.value);
});

async function generateSignAnimation(text) {
  if (!text || !text.trim()) return showError("Please enter or speak a sentence first.");
  clearError();
  generateSignBtn.disabled = true;
  generateSignBtn.textContent = "⏳ Generating Animation...";

  try {
    const response = await fetch("/api/text-to-sign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sentence: text }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Generation failed.");

    animFrames = data.frames || [];
    animSpans = data.spans || [];
    glossBadge.textContent = `Gloss: ${data.gloss ? data.gloss.join(" • ") : "None"}`;

    // Render Gloss Pills
    glossList.innerHTML = "";
    (data.gloss || []).forEach((word) => {
      const pill = document.createElement("span");
      pill.className = "gloss-pill";
      pill.textContent = word;
      glossList.appendChild(pill);
    });

    if (animFrames.length > 0) {
      animIndex = 0;
      playPauseBtn.disabled = false;
      restartBtn.disabled = false;
      startAnimationPlayback();
    } else {
      canvasCaption.textContent = "No sign animation generated";
    }
  } catch (error) {
    showError(error.message);
  } finally {
    generateSignBtn.disabled = false;
    generateSignBtn.textContent = "✨ Render Sign Language Animation";
  }
}

// --- SKELETON CANVAS RENDERER ---
function drawFrame(frameVector) {
  const ctx = signCanvas.getContext("2d");
  const w = signCanvas.width;
  const h = signCanvas.height;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#090d16";
  ctx.fillRect(0, 0, w, h);

  if (!frameVector || frameVector.length < 126) return;

  const hasLeft = frameVector.slice(0, 63).some((v) => Math.abs(v) > 1e-4);
  const hasRight = frameVector.slice(63, 126).some((v) => Math.abs(v) > 1e-4);

  // Position wrist anchor at h * 0.72 so fingers extending upward (negative Y) center nicely
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

    // Draw Skeleton Connections
    ctx.strokeStyle = slot === 0 ? "#38bdf8" : "#818cf8";
    ctx.lineWidth = 3.5;
    HAND_CONNECTIONS.forEach(([a, b]) => {
      ctx.beginPath();
      ctx.moveTo(points[a].x, points[a].y);
      ctx.lineTo(points[b].x, points[b].y);
      ctx.stroke();
    });

    // Draw Joint Circles
    points.forEach((pt) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4.5, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
    });
  }

  // Find caption word for current frame
  let currentWord = "";
  for (const span of animSpans) {
    if (animIndex >= span.start && animIndex < span.end) {
      currentWord = span.word;
      break;
    }
  }
  canvasCaption.textContent = currentWord || "Sign Language";
}


function startAnimationPlayback() {
  clearTimeout(animTimer);
  animPlaying = true;
  playPauseBtn.textContent = "⏸ Pause";
  stepAnimation();
}

function stepAnimation() {
  if (!animPlaying || animFrames.length === 0) return;

  drawFrame(animFrames[animIndex]);
  animIndex = (animIndex + 1) % animFrames.length;

  const speed = parseFloat(speedSelect.value) || 1.0;
  const interval = 50 / speed; // Base 20 FPS (50ms per frame)
  clearTimeout(animTimer);
  animTimer = setTimeout(stepAnimation, interval);
}

playPauseBtn.addEventListener("click", () => {
  animPlaying = !animPlaying;
  if (animPlaying) {
    playPauseBtn.textContent = "⏸ Pause";
    stepAnimation();
  } else {
    playPauseBtn.textContent = "▶ Play";
    clearTimeout(animTimer);
  }
});

restartBtn.addEventListener("click", () => {
  clearTimeout(animTimer);
  animIndex = 0;
  startAnimationPlayback();
});

// Theme Toggle
themeToggle.addEventListener("click", () => {
  const isDark = document.documentElement.dataset.theme === "dark";
  const newTheme = isDark ? "light" : "dark";
  document.documentElement.dataset.theme = newTheme;
  themeToggle.textContent = isDark ? "🌙 Dark theme" : "☀️ Light theme";
  themeToggle.setAttribute("aria-pressed", String(!isDark));
});

// Load Model Labels
fetch("/api/labels")
  .then((res) => res.json())
  .then((data) => {
    if (data.labels) {
      document.querySelector("#label-count").textContent = `${data.labels.length} Signs Trained`;
    }
  })
  .catch(() => {
    document.querySelector("#label-count").textContent = "Model Active";
  });
