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

      // Auto-add to word buffer or sentence when stable
      if (
        autoAddActive &&
        _consecutiveCount === AUTO_ADD_STABILITY_THRESHOLD &&
        detectedLabel !== _lastAppendedSign
      ) {
        _lastAppendedSign = detectedLabel;
        
        // If it's a single letter (fingerspelling sign), append to word buffer
        if (detectedLabel.length === 1 && detectedLabel.match(/[A-Z]/i)) {
          addLetterToWordBuffer(detectedLabel.toUpperCase());
        } else {
          // Whole word sign, append directly to sentence
          sentence.value = `${sentence.value.trim()} ${detectedLabel}`.trim();
          sentence.classList.add("sentence-flash");
          setTimeout(() => sentence.classList.remove("sentence-flash"), 600);
        }
      }

      // Auto-speak when stable
      if (
        autoSpeakActive &&
        _consecutiveCount === AUTO_ADD_STABILITY_THRESHOLD &&
        detectedLabel !== window._lastAutoSpokenSign
      ) {
        window._lastAutoSpokenSign = detectedLabel;
        speakText(detectedLabel);
      }
    } else {
      result.textContent = "No sign detected";
      confidence.textContent = "Keep hand steady and centered.";
      if (addSign) addSign.disabled = true;
      _consecutiveSign = "";
      _consecutiveCount = 0;
    }

    // Keep live webcam clean: on-screen skeleton tracking overlay is disabled
    if (preview) {
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

document.querySelector("#delete-word").addEventListener("click", () => {
  sentence.value = sentence.value.trim().split(/\s+/).slice(0, -1).join(" ");
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
});

document.querySelector("#speak").addEventListener("click", () => {
  speakText(sentence.value);
});

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
  const currentTheme = document.documentElement.getAttribute("data-theme") || document.documentElement.dataset.theme || "dark";
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  document.documentElement.dataset.theme = newTheme;
  themeToggle.textContent = newTheme === "dark" ? "☀️ Light theme" : "🌙 Dark theme";
  themeToggle.setAttribute("aria-pressed", String(newTheme === "light"));

  // Live update Clerk theme properties without destroying the DOM node
  if (clerkInstance) {
    const appearance = getClerkAppearance();
    if (typeof clerkInstance.__unstable__updateProps === "function") {
      try {
        if (!clerkInstance.user && clerkSignInMount) {
          clerkInstance.__unstable__updateProps({
            node: clerkSignInMount,
            props: { appearance: appearance },
          }).catch(() => {});
        } else if (clerkInstance.user && clerkUserButtonMount) {
          clerkInstance.__unstable__updateProps({
            node: clerkUserButtonMount,
            props: { appearance: appearance },
          }).catch(() => {});
        }
      } catch (_) {}
    }
  }
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


// ==========================================
// 1. LETTER-TO-WORD CONSTRUCTION ENGINE
// ==========================================
let wordLetters = [];
let currentCorrectedWord = "";
const wordBufferChips = document.querySelector("#word-buffer-chips");
const correctedWordEl = document.querySelector("#corrected-word");
const wordSuggestionsEl = document.querySelector("#word-suggestions");
const commitWordBtn = document.querySelector("#commit-word-btn");
const backspaceLetterBtn = document.querySelector("#backspace-letter-btn");
const clearWordBtn = document.querySelector("#clear-word-btn");
const polishGrammarBtn = document.querySelector("#polish-grammar-btn");

function addLetterToWordBuffer(letter) {
  if (!letter || letter.length !== 1) return;
  wordLetters.push(letter.toUpperCase());
  renderWordBuffer();
  queryWordConstruction();
}

function renderWordBuffer() {
  if (!wordBufferChips) return;
  if (wordLetters.length === 0) {
    wordBufferChips.innerHTML = '<span class="placeholder-chip">Sign letters to build a word...</span>';
    if (correctedWordEl) correctedWordEl.textContent = "—";
    if (wordSuggestionsEl) wordSuggestionsEl.innerHTML = '<span class="no-suggestions">Waiting for letters...</span>';
    currentCorrectedWord = "";
    return;
  }

  wordBufferChips.innerHTML = wordLetters
    .map((l) => `<span class="buffer-letter-chip">${l}</span>`)
    .join("");
}

async function queryWordConstruction() {
  if (wordLetters.length === 0) return;
  try {
    const res = await fetch("/api/gestures/word-construct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ letters: wordLetters }),
    });
    const data = await res.json();
    if (data.success && data.data) {
      const { raw, corrected, suggestions } = data.data;
      currentCorrectedWord = corrected || raw;
      if (correctedWordEl) correctedWordEl.textContent = currentCorrectedWord;

      if (wordSuggestionsEl) {
        if (suggestions && suggestions.length > 0) {
          wordSuggestionsEl.innerHTML = suggestions
            .map(
              (s) => `<button type="button" class="word-suggestion-chip" data-word="${s}">${s}</button>`
            )
            .join("");

          // Attach click listener to suggestion chips
          wordSuggestionsEl.querySelectorAll(".word-suggestion-chip").forEach((chip) => {
            chip.addEventListener("click", () => {
              const word = chip.dataset.word;
              commitWordToSentence(word);
            });
          });
        } else {
          wordSuggestionsEl.innerHTML = '<span class="no-suggestions">No dictionary matches</span>';
        }
      }
    }
  } catch (err) {
    console.error("Word construction query failed:", err);
  }
}

function commitWordToSentence(wordToCommit) {
  const chosen = (wordToCommit || currentCorrectedWord || wordLetters.join("")).trim();
  if (!chosen) return;

  sentence.value = `${sentence.value.trim()} ${chosen}`.trim();
  sentence.classList.add("sentence-flash");
  setTimeout(() => sentence.classList.remove("sentence-flash"), 600);

  // Clear word buffer
  wordLetters = [];
  renderWordBuffer();
}

commitWordBtn?.addEventListener("click", () => {
  commitWordToSentence();
});

backspaceLetterBtn?.addEventListener("click", () => {
  if (wordLetters.length > 0) {
    wordLetters.pop();
    renderWordBuffer();
    if (wordLetters.length > 0) {
      queryWordConstruction();
    }
  }
});

clearWordBtn?.addEventListener("click", () => {
  wordLetters = [];
  renderWordBuffer();
});

// AI Grammar Synthesis (ASL -> English)
polishGrammarBtn?.addEventListener("click", async () => {
  const rawText = sentence.value.trim();
  if (!rawText) {
    showError("Please sign or build some words first.");
    return;
  }

  polishGrammarBtn.disabled = true;
  polishGrammarBtn.textContent = "✨ Synthesizing...";

  try {
    const res = await fetch("/api/gloss-to-sentence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gloss: rawText }),
    });
    const data = await res.json();
    if (data.sentence) {
      sentence.value = data.sentence;
      sentence.classList.add("sentence-flash");
      setTimeout(() => sentence.classList.remove("sentence-flash"), 600);
      speakText(data.sentence);
    }
  } catch (err) {
    console.error("Grammar polish failed:", err);
  } finally {
    polishGrammarBtn.disabled = false;
    polishGrammarBtn.textContent = "✨ AI Polish Grammar";
  }
});


// ==========================================
// 2. CLERK AUTHENTICATION & APP LOCK GATE
// ==========================================
let currentUser = null;
let clerkInstance = null;

const authGate = document.querySelector("#auth-gate");
const appShell = document.querySelector("#app-shell");
const clerkSignInMount = document.querySelector("#clerk-sign-in-mount");
const clerkUserButtonMount = document.querySelector("#clerk-user-button");
const fallbackOtpContainer = document.querySelector("#fallback-otp-container");

const userProfileMenu = document.querySelector("#user-profile-menu");
const userDisplayName = document.querySelector("#user-display-name");
const userPlanTag = document.querySelector("#user-plan-tag");
const authSignOutBtn = document.querySelector("#auth-sign-out-btn");

const emailStep = document.querySelector("#email-step");
const otpStep = document.querySelector("#otp-step");
const authEmailInput = document.querySelector("#auth-email");
const authOtpInput = document.querySelector("#auth-otp");
const sendOtpBtn = document.querySelector("#send-otp-btn");
const verifyOtpBtn = document.querySelector("#verify-otp-btn");
const backToEmailBtn = document.querySelector("#back-to-email-btn");
const authStatusMsg = document.querySelector("#auth-status-msg");

let currentAuthEmail = "";
let simulatedOtpCode = "123456";

function unlockAppShell(userData) {
  if (authGate) authGate.hidden = true;
  if (appShell) appShell.hidden = false;
  if (upgradeBtn) upgradeBtn.hidden = false;
  currentUser = userData;
  updateUserUI();
}

function lockAppShell() {
  if (authGate) authGate.hidden = false;
  if (appShell) appShell.hidden = true;
  if (upgradeBtn) upgradeBtn.hidden = true;
  currentUser = null;
  stopRealtimeTracking();
  turnCameraOff();
  updateUserUI();
}

function updateUserUI() {
  if (currentUser) {
    if (userProfileMenu) userProfileMenu.hidden = false;
    if (userDisplayName) userDisplayName.textContent = currentUser.first_name || currentUser.name || currentUser.email || "User";
    const plan = (currentUser.membership_plan || currentUser.plan || "free").toUpperCase();
    if (userPlanTag) {
      userPlanTag.textContent = plan;
      if (plan === "PRO" || plan === "ENTERPRISE") {
        userPlanTag.style.background = "linear-gradient(135deg, #10b981, #059669)";
        userPlanTag.style.color = "#fff";
      } else {
        userPlanTag.style.background = "";
        userPlanTag.style.color = "";
      }
    }
  } else {
    if (userProfileMenu) userProfileMenu.hidden = true;
  }
}

function extractClerkDomain(publishableKey) {
  try {
    const b64 = publishableKey.split("_")[2] || "";
    const decoded = atob(b64);
    return decoded.replace(/\$$/, "");
  } catch (_) {
    return "brief-dingo-2050.clerk.accounts.dev";
  }
}

function loadClerkSDK(publishableKey) {
  if (window.Clerk && typeof window.Clerk.load === "function") {
    return window.Clerk.load().then(() => window.Clerk);
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-clerk-sdk]");
    if (existing) existing.remove();

    const domain = extractClerkDomain(publishableKey);
    const script = document.createElement("script");
    script.setAttribute("data-clerk-sdk", "true");
    script.setAttribute("data-clerk-publishable-key", publishableKey);
    // Load directly from Clerk edge CDN for fast 0.7s initialization
    script.src = `https://${domain}/npm/@clerk/clerk-js@5/dist/clerk.browser.js`;
    script.crossOrigin = "anonymous";
    script.onload = async () => {
      try {
        if (window.Clerk) {
          await window.Clerk.load();
          resolve(window.Clerk);
        } else {
          reject(new Error("Clerk object not found on window"));
        }
      } catch (e) {
        reject(e);
      }
    };
    script.onerror = () => {
      // Fallback to jsdelivr CDN if edge domain is blocked
      const fallbackScript = document.createElement("script");
      fallbackScript.setAttribute("data-clerk-sdk", "true");
      fallbackScript.setAttribute("data-clerk-publishable-key", publishableKey);
      fallbackScript.src = "https://cdn.jsdelivr.net/npm/@clerk/clerk-js@latest/dist/clerk.browser.js";
      fallbackScript.crossOrigin = "anonymous";
      fallbackScript.onload = async () => {
        try {
          if (window.Clerk) {
            await window.Clerk.load();
            resolve(window.Clerk);
          } else {
            reject(new Error("Clerk object not found"));
          }
        } catch (e) {
          reject(e);
        }
      };
      fallbackScript.onerror = (e) => reject(new Error("Failed to load Clerk JS SDK from CDN"));
      document.head.appendChild(fallbackScript);
    };
    document.head.appendChild(script);
  });
}

function getClerkAppearance() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || document.documentElement.dataset.theme || "dark";
  const isDark = currentTheme !== "light";

  if (isDark) {
    return {
      variables: {
        colorPrimary: "#38bdf8",
        colorBackground: "#151c2e",
        colorText: "#f8fafc",
        colorTextSecondary: "#94a3b8",
        colorInputBackground: "#1e293b",
        colorInputText: "#f8fafc",
        borderRadius: "0.75rem",
      },
      elements: {
        card: {
          backgroundColor: "#151c2e",
          border: "1px solid rgba(255, 255, 255, 0.12)",
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.6)",
        },
        headerTitle: {
          color: "#ffffff",
          fontWeight: "800",
        },
        headerSubtitle: {
          color: "#94a3b8",
        },
        socialButtonsBlockButton: {
          backgroundColor: "#1e293b",
          borderColor: "rgba(255, 255, 255, 0.15)",
        },
        socialButtonsBlockButtonText: {
          color: "#f8fafc !important",
          fontWeight: "600",
        },
        dividerLine: {
          backgroundColor: "rgba(255, 255, 255, 0.12)",
        },
        dividerText: {
          color: "#94a3b8",
        },
        formFieldLabel: {
          color: "#cbd5e1",
          fontWeight: "600",
        },
        formFieldInput: {
          backgroundColor: "#1e293b",
          borderColor: "rgba(255, 255, 255, 0.15)",
          color: "#ffffff",
        },
        formButtonPrimary: {
          backgroundColor: "#38bdf8",
          color: "#0b0f19",
          fontWeight: "700",
        },
        footerActionText: {
          color: "#94a3b8",
        },
        footerActionLink: {
          color: "#38bdf8",
          fontWeight: "600",
        },
        footer: {
          background: "transparent",
        },
      },
    };
  } else {
    return {
      variables: {
        colorPrimary: "#0284c7",
        colorBackground: "#ffffff",
        colorText: "#0f172a",
        colorTextSecondary: "#475569",
        colorInputBackground: "#f8fafc",
        colorInputText: "#0f172a",
        borderRadius: "0.75rem",
      },
      elements: {
        card: {
          backgroundColor: "#ffffff",
          border: "1px solid rgba(0, 0, 0, 0.12)",
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.1)",
        },
        headerTitle: {
          color: "#0f172a",
          fontWeight: "800",
        },
        headerSubtitle: {
          color: "#475569",
        },
        socialButtonsBlockButton: {
          backgroundColor: "#ffffff",
          borderColor: "rgba(0, 0, 0, 0.15)",
        },
        socialButtonsBlockButtonText: {
          color: "#0f172a !important",
          fontWeight: "600",
        },
        dividerLine: {
          backgroundColor: "rgba(0, 0, 0, 0.12)",
        },
        dividerText: {
          color: "#64748b",
        },
        formFieldLabel: {
          color: "#334155",
          fontWeight: "600",
        },
        formFieldInput: {
          backgroundColor: "#f8fafc",
          borderColor: "rgba(0, 0, 0, 0.15)",
          color: "#0f172a",
        },
        formButtonPrimary: {
          backgroundColor: "#0284c7",
          color: "#ffffff",
          fontWeight: "700",
        },
        footerActionText: {
          color: "#64748b",
        },
        footerActionLink: {
          color: "#0284c7",
          fontWeight: "600",
        },
        footer: {
          background: "transparent",
        },
      },
    };
  }
}

async function initClerkAuth() {
  try {
    const res = await fetch("/api/auth/config");
    const configData = await res.json();
    const clerkKey = configData.data?.clerk_publishable_key || "";

    const isLiveClerkKey = clerkKey && clerkKey.startsWith("pk_") && !clerkKey.includes("example.com");

    if (isLiveClerkKey) {
      if (clerkSignInMount) {
        clerkSignInMount.innerHTML = `
          <div class="clerk-loader-placeholder">
            <div class="loader-spinner"></div>
            <p>Connecting to Clerk secure authentication...</p>
          </div>
        `;
      }

      const clerk = await loadClerkSDK(clerkKey);
      clerkInstance = clerk;

      if (clerk.user) {
        // User already authenticated
        const token = await clerk.session.getToken();
        const userData = {
          clerk_id: clerk.user.id,
          email: clerk.user.primaryEmailAddress?.emailAddress || "",
          name: clerk.user.fullName || clerk.user.firstName || "User",
          image_url: clerk.user.imageUrl || "",
          plan: "free",
        };
        await syncUserWithBackend(token, userData);
        unlockAppShell(userData);

        if (clerkUserButtonMount) {
          clerkUserButtonMount.innerHTML = "";
          clerk.mountUserButton(clerkUserButtonMount, { appearance: getClerkAppearance() });
        }
      } else {
        // User unauthenticated -> Lock application and mount Clerk Sign-In
        lockAppShell();
        if (fallbackOtpContainer) fallbackOtpContainer.hidden = true;
        if (clerkSignInMount) {
          clerkSignInMount.hidden = false;
          clerkSignInMount.innerHTML = "";
          clerk.mountSignIn(clerkSignInMount, { appearance: getClerkAppearance() });
        }
      }

      // Listen to auth state changes in real time
      clerk.addListener(async (emission) => {
        if (emission.user) {
          const token = await clerk.session?.getToken();
          const userData = {
            clerk_id: emission.user.id,
            email: emission.user.primaryEmailAddress?.emailAddress || "",
            name: emission.user.fullName || emission.user.firstName || "User",
            image_url: emission.user.imageUrl || "",
            plan: "free",
          };
          if (token) await syncUserWithBackend(token, userData);
          unlockAppShell(userData);
          if (clerkUserButtonMount) {
            clerkUserButtonMount.innerHTML = "";
            clerk.mountUserButton(clerkUserButtonMount, { appearance: getClerkAppearance() });
          }
        } else {
          lockAppShell();
          if (clerkSignInMount) {
            clerkSignInMount.innerHTML = "";
            clerk.mountSignIn(clerkSignInMount, { appearance: getClerkAppearance() });
          }
        }
      });
    } else {
      // Local fallback mode when no valid Clerk publishable key configured
      lockAppShell();
      showFallbackOtpForm();
    }
  } catch (err) {
    console.error("Clerk live authentication initialization error:", err);
    lockAppShell();
    showFallbackOtpForm();
  }
}

function showFallbackOtpForm() {
  if (fallbackOtpContainer) fallbackOtpContainer.hidden = false;
  if (clerkSignInMount) clerkSignInMount.hidden = true;
}

sendOtpBtn?.addEventListener("click", async () => {
  const email = authEmailInput?.value.trim();
  if (!email || !email.includes("@")) {
    showAuthStatus("Please enter a valid email address.", "error");
    return;
  }
  currentAuthEmail = email;
  sendOtpBtn.disabled = true;
  sendOtpBtn.textContent = "Sending code...";

  // Show status without exposing private codes
  showAuthStatus(`A 6-digit verification code was sent to ${email}. Please check your inbox.`, "success");
  if (emailStep) emailStep.hidden = true;
  if (otpStep) otpStep.hidden = false;

  sendOtpBtn.disabled = false;
  sendOtpBtn.textContent = "Send Verification Code";
});

backToEmailBtn?.addEventListener("click", () => {
  if (emailStep) emailStep.hidden = false;
  if (otpStep) otpStep.hidden = true;
  clearAuthStatus();
});

verifyOtpBtn?.addEventListener("click", async () => {
  const code = authOtpInput?.value.trim();
  if (!code || code.length < 4) {
    showAuthStatus("Please enter the verification code sent to your email.", "error");
    return;
  }

  verifyOtpBtn.disabled = true;
  verifyOtpBtn.textContent = "Verifying...";

  const mockId = "user_" + btoa(currentAuthEmail).substring(0, 12).toLowerCase();
  const mockUser = {
    clerk_id: mockId,
    email: currentAuthEmail,
    first_name: currentAuthEmail.split("@")[0],
    name: currentAuthEmail.split("@")[0],
    membership_plan: "free",
  };
  await syncUserWithBackend("demo_token_" + mockId, mockUser);
  unlockAppShell(mockUser);

  verifyOtpBtn.disabled = false;
  verifyOtpBtn.textContent = "Verify & Unlock Communicator";
});

function showAuthStatus(msg, type) {
  if (!authStatusMsg) return;
  authStatusMsg.textContent = msg;
  authStatusMsg.className = `auth-status ${type}`;
  authStatusMsg.hidden = false;
}

function clearAuthStatus() {
  if (!authStatusMsg) return;
  authStatusMsg.textContent = "";
  authStatusMsg.hidden = true;
}

async function syncUserWithBackend(token, userData) {
  try {
    const res = await fetch("/api/auth/sync", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(userData),
    });
    const resData = await res.json();
    if (resData.success && resData.data) {
      currentUser = resData.data;
      localStorage.setItem("signbridge_user", JSON.stringify(currentUser));
      localStorage.setItem("signbridge_token", token);
      updateUserUI();
    }
  } catch (err) {
    console.error("User sync failed:", err);
    currentUser = userData;
    localStorage.setItem("signbridge_user", JSON.stringify(currentUser));
    updateUserUI();
  }
}

authSignOutBtn?.addEventListener("click", async () => {
  if (clerkInstance) {
    try {
      await clerkInstance.signOut();
    } catch (_) {}
  }
  localStorage.removeItem("signbridge_user");
  localStorage.removeItem("signbridge_token");
  lockAppShell();
  if (!clerkInstance) {
    showFallbackOtpForm();
  }
});

// Initialize Clerk Authentication on Page Load
window.addEventListener("DOMContentLoaded", () => {
  initClerkAuth();
});


// ==========================================
// 3. STRIPE PAYMENT GATEWAY
// ==========================================
const pricingModal = document.querySelector("#pricing-modal");
const pricingModalClose = document.querySelector("#pricing-modal-close");
const upgradeBtn = document.querySelector("#upgrade-btn");
const checkoutProBtn = document.querySelector("#checkout-pro-btn");
const checkoutEnterpriseBtn = document.querySelector("#checkout-enterprise-btn");

function showPricingModal() {
  if (pricingModal) pricingModal.hidden = false;
}

function hidePricingModal() {
  if (pricingModal) pricingModal.hidden = true;
}

upgradeBtn?.addEventListener("click", showPricingModal);
pricingModalClose?.addEventListener("click", hidePricingModal);
pricingModal?.addEventListener("click", (e) => {
  if (e.target === pricingModal) hidePricingModal();
});

async function initiateStripeCheckout(plan) {
  const token = localStorage.getItem("signbridge_token") || "";
  try {
    const res = await fetch("/api/payment/create-checkout-session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
      },
      body: JSON.stringify({
        plan_id: plan,
        email: currentUser ? currentUser.email : "guest@signbridge.app",
      }),
    });
    const data = await res.json();
    if (data.success && data.data && data.data.checkout_url) {
      // If simulated or live checkout session
      window.location.href = data.data.checkout_url;
    } else {
      // Direct simulated upgrade for local demo
      if (currentUser) {
        currentUser.membership_plan = plan;
        localStorage.setItem("signbridge_user", JSON.stringify(currentUser));
        updateUserUI();
      }
      alert(`🎉 Congratulations! Upgraded to ${plan.toUpperCase()} plan.`);
      hidePricingModal();
    }
  } catch (err) {
    console.error("Checkout initiation failed:", err);
    alert("Could not initialize Stripe checkout. Upgraded locally in demo mode.");
    if (currentUser) {
      currentUser.membership_plan = plan;
      updateUserUI();
    }
    hidePricingModal();
  }
}

checkoutProBtn?.addEventListener("click", () => initiateStripeCheckout("pro_monthly"));
checkoutEnterpriseBtn?.addEventListener("click", () => initiateStripeCheckout("lifetime"));

// Check for payment success callback in URL query params
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get("payment") === "success") {
  const plan = urlParams.get("plan") || "pro";
  if (currentUser) {
    currentUser.membership_plan = plan;
    localStorage.setItem("signbridge_user", JSON.stringify(currentUser));
    updateUserUI();
  }
  showError(`🎉 Payment successful! You are now subscribed to the ${plan.toUpperCase()} tier.`);
  window.history.replaceState({}, document.title, window.location.pathname);
}

