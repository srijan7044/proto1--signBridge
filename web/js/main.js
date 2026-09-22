// main.js — SignBridge main entry point and module orchestrator

import { initDOMElements, DOM, state } from "./state.js";
import { initCameraControls } from "./camera.js";
import { predictFrame, initRecognitionControls, loadLabelCount } from "./recognition.js";
import { initWordBuilder } from "./word-builder.js";
import { initAnimationControls, initSpeechRecognition } from "./animation.js";
import { initClerkAuth, initAuthControls } from "./auth.js";
import { initThemeToggle } from "./theme.js";
import { initPaymentControls } from "./payments.js";

initDOMElements();
window.predictFrame = predictFrame;

initThemeToggle();

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

initCameraControls();
initRecognitionControls();
initWordBuilder();
initAnimationControls();
initSpeechRecognition();
initAuthControls();
initClerkAuth();
initPaymentControls();

loadLabelCount();
