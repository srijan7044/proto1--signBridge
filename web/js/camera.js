// camera.js — Webcam capture, frame capture, and live tracking management

import { state, DOM, showError, clearError } from "./state.js";

export function startRealtimeTracking() {
  if (state.isRealtimeActive) return;
  state.isRealtimeActive = true;
  if (DOM["toggle-realtime"]) {
    DOM["toggle-realtime"].textContent = "⚡ Live Tracking: ON";
    DOM["toggle-realtime"].classList.add("primary-button");
    DOM["toggle-realtime"].classList.remove("secondary-button");
  }
  state.realtimeInterval = setInterval(() => {
    if (!DOM.camera || !DOM.camera.videoWidth) return;
    const w = DOM.camera.videoWidth || 640;
    const h = DOM.camera.videoHeight || 480;
    DOM["camera-canvas"].width = w;
    DOM["camera-canvas"].height = h;
    const ctx = DOM["camera-canvas"].getContext("2d");
    ctx.drawImage(DOM.camera, 0, 0, w, h);
    DOM["camera-canvas"].toBlob((blob) => {
      if (blob && state.isRealtimeActive) window.predictFrame(blob);
    }, "image/jpeg", 0.85);
  }, 350);
}

export function stopRealtimeTracking() {
  state.isRealtimeActive = false;
  if (state.realtimeInterval) clearInterval(state.realtimeInterval);
  state.realtimeInterval = null;
  if (DOM["toggle-realtime"]) {
    DOM["toggle-realtime"].textContent = "⚡ Live Tracking: OFF";
    DOM["toggle-realtime"].classList.remove("primary-button");
    DOM["toggle-realtime"].classList.add("secondary-button");
  }
  if (DOM.preview) {
    DOM.preview.hidden = true;
    DOM.preview.style.display = "none";
  }
}

export async function turnCameraOn() {
  if (state.isCameraStarting || state.isCameraOn) return;
  state.isCameraStarting = true;
  clearError();
  try {
    if (state.cameraStream) {
      state.cameraStream.getTracks().forEach((track) => track.stop());
      state.cameraStream = null;
    }
    state.cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    DOM.camera.srcObject = state.cameraStream;
    DOM.camera.hidden = false;
    DOM.camera.style.display = "block";
    await DOM.camera.play();

    if (DOM["camera-off-overlay"]) {
      DOM["camera-off-overlay"].hidden = true;
      DOM["camera-off-overlay"].style.display = "none";
    }

    DOM.camera.onloadedmetadata = () => {
      if (DOM["camera-status"]) {
        DOM["camera-status"].textContent = `Camera Active (${DOM.camera.videoWidth}x${DOM.camera.videoHeight})`;
        DOM["camera-status"].className = "status-badge status-online";
      }
    };

    state.isCameraOn = true;
    DOM.capture.disabled = false;
    DOM["toggle-realtime"].disabled = false;
    if (DOM["camera-status"]) {
      DOM["camera-status"].textContent = "Camera Active";
      DOM["camera-status"].className = "status-badge status-online";
    }
    if (DOM["camera-toggle"]) DOM["camera-toggle"].checked = true;
    if (DOM["camera-toggle-text"]) DOM["camera-toggle-text"].textContent = "Camera: ON";

    startRealtimeTracking();
  } catch (error) {
    showError("Camera access denied or unavailable: " + error.message);
    turnCameraOff();
  } finally {
    state.isCameraStarting = false;
  }
}

export function turnCameraOff() {
  stopRealtimeTracking();

  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach((track) => track.stop());
    state.cameraStream = null;
  }

  DOM.camera.srcObject = null;
  DOM.camera.hidden = true;
  DOM.camera.style.display = "none";
  if (DOM.preview) {
    DOM.preview.hidden = true;
    DOM.preview.style.display = "none";
    DOM.preview.src = "";
  }
  if (DOM["camera-off-overlay"]) {
    DOM["camera-off-overlay"].hidden = false;
    DOM["camera-off-overlay"].style.display = "flex";
  }

  state.isCameraOn = false;
  DOM.capture.disabled = true;
  DOM["toggle-realtime"].disabled = true;
  if (DOM["camera-status"]) {
    DOM["camera-status"].textContent = "Camera OFF";
    DOM["camera-status"].className = "status-badge status-offline";
  }
  if (DOM["camera-toggle"]) DOM["camera-toggle"].checked = false;
  if (DOM["camera-toggle-text"]) DOM["camera-toggle-text"].textContent = "Camera: OFF";
}

export function initCameraControls() {
  if (DOM["camera-toggle"]) {
    DOM["camera-toggle"].addEventListener("change", () => {
      if (DOM["camera-toggle"].checked) {
        turnCameraOn();
      } else {
        turnCameraOff();
      }
    });
  }

  if (DOM["toggle-realtime"]) {
    DOM["toggle-realtime"].addEventListener("click", () => {
      if (state.isRealtimeActive) {
        stopRealtimeTracking();
      } else {
        startRealtimeTracking();
      }
    });
  }

  if (DOM.capture) {
    DOM.capture.addEventListener("click", () => {
      clearError();
      if (!state.cameraStream || !DOM.camera.srcObject) {
        return showError("Please start the camera first by clicking 'Start Camera'.");
      }

      const w = DOM.camera.videoWidth || 640;
      const h = DOM.camera.videoHeight || 480;
      DOM["camera-canvas"].width = w;
      DOM["camera-canvas"].height = h;
      const ctx = DOM["camera-canvas"].getContext("2d");
      ctx.drawImage(DOM.camera, 0, 0, w, h);

      DOM.result.textContent = "Capturing & Analyzing...";
      DOM.confidence.textContent = "Processing frame...";

      DOM["camera-canvas"].toBlob(
        (blob) => {
          if (!blob) return showError("Failed to capture image frame from camera.");
          window.predictFrame(blob);
        },
        "image/jpeg",
        0.95
      );
    });
  }

  if (DOM.upload) {
    DOM.upload.addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (file) window.predictFrame(file);
    });
  }
}
