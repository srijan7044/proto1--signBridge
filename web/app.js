// --- STATE & DOM ELEMENTS ---
const camera = document.querySelector("#camera");
const cameraCanvas = document.querySelector("#camera-canvas");
const preview = document.querySelector("#preview");
const upload = document.querySelector("#upload");
const startCamera = document.querySelector("#start-camera");
const toggleRealtime = document.querySelector("#toggle-realtime");
const capture = document.querySelector("#capture");
const addSign = document.querySelector("#add-sign");
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
let speechRecognition = null;

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
      addSign.disabled = false;

      if (autoSpeakActive && detectedLabel !== window._lastAutoSpokenSign) {
        window._lastAutoSpokenSign = detectedLabel;
        speakText(detectedLabel);
        sentence.value = `${sentence.value.trim()} ${detectedLabel}`.trim();
      }
    } else {
      result.textContent = "No sign detected";
      confidence.textContent = "Keep hand steady and centered.";
      addSign.disabled = true;
    }

    if (data.image) {
      preview.src = `data:image/jpeg;base64,${data.image}`;
      preview.hidden = false;
    }
  } catch (error) {
    if (!isRealtimeActive) showError(error.message);
  }
}

startCamera.addEventListener("click", async () => {
  clearError();
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    camera.srcObject = cameraStream;
    capture.disabled = false;
    toggleRealtime.disabled = false;
    cameraStatus.textContent = "Camera Active";
    cameraStatus.className = "status-badge status-online";
    startCamera.textContent = "🎥 Camera Connected";
  } catch (error) {
    showError("Camera access denied or unavailable. You can use image upload instead.");
  }
});

toggleRealtime.addEventListener("click", () => {
  isRealtimeActive = !isRealtimeActive;
  if (isRealtimeActive) {
    toggleRealtime.textContent = "⚡ Live Auto-Recognize: ON";
    toggleRealtime.classList.add("primary-button");
    toggleRealtime.classList.remove("secondary-button");
    realtimeInterval = setInterval(() => {
      if (!camera.videoWidth) return;
      cameraCanvas.width = camera.videoWidth;
      cameraCanvas.height = camera.videoHeight;
      cameraCanvas.getContext("2d").drawImage(camera, 0, 0);
      cameraCanvas.toBlob((blob) => predictFrame(blob), "image/jpeg", 0.85);
    }, 400);
  } else {
    toggleRealtime.textContent = "⚡ Live Auto-Recognize: OFF";
    toggleRealtime.classList.remove("primary-button");
    toggleRealtime.classList.add("secondary-button");
    clearInterval(realtimeInterval);
  }
});

capture.addEventListener("click", () => {
  if (!camera.videoWidth) return;
  cameraCanvas.width = camera.videoWidth;
  cameraCanvas.height = camera.videoHeight;
  cameraCanvas.getContext("2d").drawImage(camera, 0, 0);
  cameraCanvas.toBlob((blob) => predictFrame(blob), "image/jpeg", 0.92);
});

upload.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) predictFrame(file);
});

addSign.addEventListener("click", () => {
  if (detectedLabel) {
    sentence.value = `${sentence.value.trim()} ${detectedLabel}`.trim();
  }
});

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
  addSign.disabled = true;
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
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = false;
  speechRecognition.interimResults = false;
  speechRecognition.lang = "en-US";

  speechRecognition.onstart = () => {
    micBtn.classList.add("listening");
    micBtn.textContent = "🎙️ Listening...";
  };

  speechRecognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    ttsInput.value = transcript;
    generateSignAnimation(transcript);
  };

  speechRecognition.onerror = (event) => {
    showError(`Voice recognition error: ${event.error}`);
    micBtn.classList.remove("listening");
    micBtn.textContent = "🎤 Voice Input";
  };

  speechRecognition.onend = () => {
    micBtn.classList.remove("listening");
    micBtn.textContent = "🎤 Voice Input";
  };

  micBtn.addEventListener("click", () => {
    clearError();
    speechRecognition.start();
  });
} else {
  micBtn.disabled = true;
  micBtn.title = "Speech recognition not supported in this browser";
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

  const offsets = [[w * 0.3, h * 0.5], [w * 0.7, h * 0.5]]; // Left hand (0.3), Right hand (0.7)
  const scale = 160;

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
    ctx.lineWidth = 3;
    HAND_CONNECTIONS.forEach(([a, b]) => {
      ctx.beginPath();
      ctx.moveTo(points[a].x, points[a].y);
      ctx.lineTo(points[b].x, points[b].y);
      ctx.stroke();
    });

    // Draw Joint Circles
    points.forEach((pt) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
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
  animIndex = 0;
  if (!animPlaying) startAnimationPlayback();
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
