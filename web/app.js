const camera = document.querySelector("#camera");
const canvas = document.querySelector("#canvas");
const preview = document.querySelector("#preview");
const upload = document.querySelector("#upload");
const startCamera = document.querySelector("#start-camera");
const capture = document.querySelector("#capture");
const addSign = document.querySelector("#add-sign");
const result = document.querySelector("#result");
const confidence = document.querySelector("#confidence");
const sentence = document.querySelector("#sentence");
const alertBox = document.querySelector("#alert");
const cameraStatus = document.querySelector("#camera-status");
const themeToggle = document.querySelector("#theme-toggle");
let detectedLabel = "";
let cameraStream = null;

function showError(message) {
  alertBox.textContent = message;
  alertBox.hidden = false;
}

function clearError() {
  alertBox.hidden = true;
  alertBox.textContent = "";
}

async function predict(file) {
  clearError();
  const formData = new FormData();
  formData.append("image", file, file.name || "camera.jpg");
  result.textContent = "Analyzing...";
  confidence.textContent = "Please wait.";
  addSign.disabled = true;
  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Prediction failed.");
    detectedLabel = data.label || "";
    result.textContent = detectedLabel || "No hand detected";
    confidence.textContent = detectedLabel
      ? `Confidence: ${(data.confidence * 100).toFixed(1)}%`
      : "Try a brighter image with the full hand visible.";
    addSign.disabled = !detectedLabel;
    if (data.image) {
      preview.src = `data:image/jpeg;base64,${data.image}`;
      preview.hidden = false;
    }
  } catch (error) {
    result.textContent = "Unable to recognize";
    confidence.textContent = "Try another image.";
    showError(error.message);
  }
}

startCamera.addEventListener("click", async () => {
  clearError();
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    });
    camera.srcObject = cameraStream;
    capture.disabled = false;
    cameraStatus.textContent = "Camera ready";
    startCamera.textContent = "Camera active";
  } catch (error) {
    showError(
      "Camera permission was not granted. Use the upload option instead.",
    );
  }
});

capture.addEventListener("click", () => {
  if (!camera.videoWidth) return;
  canvas.width = camera.videoWidth;
  canvas.height = camera.videoHeight;
  canvas.getContext("2d").drawImage(camera, 0, 0);
  canvas.toBlob(
    (blob) => predict(new File([blob], "camera.jpg", { type: "image/jpeg" })),
    "image/jpeg",
    0.92,
  );
});

upload.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) predict(file);
});

addSign.addEventListener("click", () => {
  sentence.value = `${sentence.value.trim()} ${detectedLabel}`.trim();
  sentence.focus();
});

document.querySelector("#delete-word").addEventListener("click", () => {
  sentence.value = sentence.value.trim().split(/\s+/).slice(0, -1).join(" ");
});
document.querySelector("#clear").addEventListener("click", () => {
  sentence.value = "";
});
document.querySelector("#speak").addEventListener("click", () => {
  if (!sentence.value.trim())
    return showError("Enter or recognize a sentence first.");
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(
    new SpeechSynthesisUtterance(sentence.value.trim()),
  );
});

themeToggle.addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme !== "dark";
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  localStorage.setItem("signbridge-theme", dark ? "dark" : "light");
  themeToggle.textContent = dark ? "Light theme" : "Dark theme";
  themeToggle.setAttribute("aria-pressed", String(dark));
});
const savedTheme = localStorage.getItem("signbridge-theme");
if (savedTheme === "dark") themeToggle.click();

fetch("/api/labels")
  .then((response) => response.json())
  .then((data) => {
    document.querySelector("#label-count").textContent = data.labels
      ? `${data.labels.length} signs available`
      : "Labels unavailable";
  })
  .catch(() => {
    document.querySelector("#label-count").textContent = "Labels unavailable";
  });

window.addEventListener("beforeunload", () => {
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
});
