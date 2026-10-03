// state.js — Shared global state and DOM references for SignBridge

export const state = {
  detectedLabel: "",
  cameraStream: null,
  realtimeInterval: null,
  isRealtimeActive: false,
  autoSpeakActive: false,
  autoAddActive: true,
  isCameraOn: false,
  isCameraStarting: false,

  consecutiveSign: "",
  consecutiveCount: 0,
  lastAppendedSign: "",

  wordLetters: [],
  currentCorrectedWord: "",

  animFrames: [],
  animSpans: [],
  animIndex: 0,
  animPlaying: false,
  animTimer: null,

  currentUser: null,
  clerkInstance: null,
  currentAuthEmail: "",

  AUTO_ADD_STABILITY_THRESHOLD: 3,
};

export const DOM = {};

export function initDOMElements() {
  const selectors = [
    "camera", "camera-canvas", "preview", "upload", "camera-toggle",
    "camera-toggle-text", "toggle-realtime", "capture", "toggle-auto-add",
    "toggle-auto-speak", "result", "confidence", "sentence", "alert",
    "camera-status", "theme-toggle", "tab-sign-to-voice", "tab-voice-to-sign",
    "mode-sign-to-voice", "mode-voice-to-sign", "tts-input", "mic-btn",
    "generate-sign-btn", "sign-canvas", "canvas-overlay-caption",
    "play-pause-btn", "restart-btn", "speed-select", "gloss-badge", "gloss-list",
    "auth-gate", "app-shell", "clerk-sign-in-mount", "clerk-user-button",
    "user-profile-menu", "user-display-name", "user-plan-tag", "auth-sign-out-btn",
    "upgrade-btn", "pricing-modal", "pricing-modal-close", "checkout-pro-btn",
    "checkout-enterprise-btn", "camera-off-overlay",
    "word-buffer-chips", "word-suggestions", "commit-word-btn",
    "backspace-letter-btn", "clear-word-btn", "polish-grammar-btn",
    "corrected-word",
    "delete-word", "clear", "speak", "fallback-otp-container",
    "email-step", "otp-step", "auth-email", "auth-otp",
    "send-otp-btn", "verify-otp-btn", "back-to-email-btn", "auth-status-msg",
    "label-count",
  ];

  selectors.forEach((id) => {
    DOM[id] = document.getElementById(id);
  });
}

export const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [0, 17], [17, 18], [18, 19], [19, 20],
];

export function showError(message) {
  if (DOM.alert) {
    DOM.alert.textContent = message;
    DOM.alert.hidden = false;
  }
}

export function clearError() {
  if (DOM.alert) {
    DOM.alert.hidden = true;
    DOM.alert.textContent = "";
  }
}

export function speakText(text) {
  if (!text || !text.trim()) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text.trim());
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}
