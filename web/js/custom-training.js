// custom-training.js — Complete Custom Model Training purchase-to-request flow

import { state, DOM, showError } from "./state.js";
import { apiFetch } from "./api.js";

let isSubmitting = false;

/**
 * Main entry point: Opens the Custom Model Training modal or section.
 * Checks Clerk authentication, verifies $15 purchase status with the backend,
 * and renders either the $15 Purchase Card or the Model Training Request Form.
 */
export async function showCustomTrainingModal() {
  const modal = document.getElementById("custom-training-modal");
  const content = document.getElementById("custom-training-content");
  if (!modal || !content) return;

  modal.hidden = false;

  // 1. Authentication Check
  const token = localStorage.getItem("signbridge_token") || state.token || "";
  if (!token) {
    content.innerHTML = `
      <div class="auth-required-box">
        <span class="auth-icon">🔒</span>
        <h3>Sign In Required</h3>
        <p>Please sign in to your SignBridge account to request Custom Model Training.</p>
        <button id="training-signin-btn" class="primary-button">Sign In / Register</button>
      </div>
    `;
    const signinBtn = document.getElementById("training-signin-btn");
    if (signinBtn) {
      signinBtn.addEventListener("click", () => {
        if (window.Clerk && window.Clerk.openSignIn) {
          window.Clerk.openSignIn();
        } else {
          showError("Authentication service unavailable. Please refresh.");
        }
      });
    }
    return;
  }

  // 2. Show Loading Spinner
  content.innerHTML = `
    <div class="loading-spinner-container">
      <div class="spinner"></div>
      <p>Checking account eligibility...</p>
    </div>
  `;

  try {
    const res = await apiFetch("/api/custom-training/check-eligibility");
    if (res.success && res.data) {
      const { has_purchased, has_pending_request, user_email, requests } = res.data;

      if (!has_purchased) {
        // User has NOT paid -> Render $15 Purchase Card
        renderPurchaseStep(content, user_email);
      } else if (has_pending_request || (requests && requests.length > 0)) {
        // User has submitted requests -> Render Status View with option to submit new
        renderStatusAndHistoryStep(content, requests, user_email);
      } else {
        // User has verified payment but no request yet -> Render Request Form
        renderRequestFormStep(content, user_email);
      }
    } else {
      renderPurchaseStep(content, state.currentUser?.email || "");
    }
  } catch (err) {
    console.error("Failed to check custom training eligibility:", err);
    renderPurchaseStep(content, state.currentUser?.email || "");
  }
}

/**
 * Hides the Custom Model Training Modal.
 */
export function hideCustomTrainingModal() {
  const modal = document.getElementById("custom-training-modal");
  if (modal) modal.hidden = true;
}

/**
 * Renders PART 3: The $15 Custom Model Training Purchase Page/Modal.
 */
function renderPurchaseStep(container, userEmail) {
  container.innerHTML = `
    <div class="purchase-card-container">
      <div class="purchase-badge">$15.00 USD — One-Time Payment</div>
      <p class="purchase-subtitle">Request a custom sign language model trained for your specific language or regional dialect.</p>

      <div class="benefits-list">
        <div class="benefit-item">
          <span class="benefit-icon">🚀</span>
          <div>
            <strong>Custom Language Model</strong>
            <p>Request a custom sign language recognition model tailored to your vocabulary needs.</p>
          </div>
        </div>
        <div class="benefit-item">
          <span class="benefit-icon">📋</span>
          <div>
            <strong>Detailed Requirements</strong>
            <p>Submit target language, country/region, regional variations, and specific use case requirements.</p>
          </div>
        </div>
        <div class="benefit-item">
          <span class="benefit-icon">📊</span>
          <div>
            <strong>Real-time Status Tracking</strong>
            <p>Track request review, model training, validation metrics, and release progress in real-time.</p>
          </div>
        </div>
        <div class="benefit-item">
          <span class="benefit-icon">🛡️</span>
          <div>
            <strong>Expert Engineer Review</strong>
            <p>Every request is evaluated and managed directly by SignBridge core engineers.</p>
          </div>
        </div>
      </div>

      <div class="business-disclaimer">
        ℹ️ <strong>Please Note:</strong> The $15.00 payment purchases the right to submit a custom training request for review; it does not guarantee that training will be approved or completed.
      </div>

      <div id="purchase-error-area" class="error-banner" style="display: none; margin-bottom: 1rem;"></div>

      <div class="purchase-actions">
        <button id="continue-to-payment-btn" class="primary-button full-width">
          Continue to Payment ($15.00)
        </button>
        <button id="cancel-purchase-btn" class="secondary-button full-width" type="button">
          Cancel
        </button>
      </div>
    </div>
  `;

  const continueBtn = document.getElementById("continue-to-payment-btn");
  const cancelBtn = document.getElementById("cancel-purchase-btn");

  if (cancelBtn) {
    cancelBtn.addEventListener("click", hideCustomTrainingModal);
  }

  if (continueBtn) {
    continueBtn.addEventListener("click", async () => {
      continueBtn.disabled = true;
      continueBtn.innerHTML = `<span class="spinner-sm"></span> Redirecting to Stripe Checkout...`;

      const errorArea = document.getElementById("purchase-error-area");
      if (errorArea) errorArea.style.display = "none";

      try {
        const data = await apiFetch("/api/payment/create-checkout-session", {
          method: "POST",
          body: {
            plan_id: "custom_training",
            email: userEmail || state.currentUser?.email || "",
          },
        });

        if (data.success && data.data && data.data.checkout_url) {
          window.location.href = data.data.checkout_url;
        } else {
          continueBtn.disabled = false;
          continueBtn.textContent = "Continue to Payment ($15.00)";
          if (errorArea) {
            errorArea.textContent = data.error || "Could not initialize Checkout session. Please try again.";
            errorArea.style.display = "block";
          }
        }
      } catch (err) {
        console.error("Checkout creation failed:", err);
        continueBtn.disabled = false;
        continueBtn.textContent = "Continue to Payment ($15.00)";
        if (errorArea) {
          errorArea.textContent = "Failed to connect to payment server. Check your network connection.";
          errorArea.style.display = "block";
        }
      }
    });
  }
}

/**
 * Renders PART 5: The Custom Model Training Request Form (Unlocked after verified payment).
 */
function renderRequestFormStep(container, userEmail) {
  const prefilledEmail = userEmail || state.currentUser?.email || "";

  container.innerHTML = `
    <div class="request-form-container">
      <div class="verified-payment-banner">
        ✅ <strong>Payment Verified!</strong> Submit your model training details below.
      </div>

      <h3>Submit Your Custom Model Training Request</h3>
      <p class="form-subtext">Tell us about the sign language model you want to request.</p>

      <form id="custom-training-request-form">
        <div class="form-grid">
          <div class="form-group">
            <label for="training-language">Target Language Name <span class="required">*</span></label>
            <input type="text" id="training-language" placeholder="e.g. Hindi, Spanish, Tamil, German" required />
          </div>

          <div class="form-group">
            <label for="training-country">Country or Region <span class="required">*</span></label>
            <input type="text" id="training-country" placeholder="e.g. India, Spain, Mexico, Germany" required />
          </div>
        </div>

        <div class="form-group">
          <label for="training-variant">Preferred Sign Language / Regional Variation <span class="optional">(Optional)</span></label>
          <input type="text" id="training-variant" placeholder="e.g. ISL (Indian Sign Language), LSE, ASL" />
        </div>

        <div class="form-group">
          <label for="training-description">Description of Requested Model <span class="required">*</span></label>
          <textarea id="training-description" rows="3" placeholder="Describe the vocabulary, gestures, or signs you require..." required></textarea>
        </div>

        <div class="form-group">
          <label for="training-usecase">Intended Use Case <span class="required">*</span></label>
          <textarea id="training-usecase" rows="3" placeholder="Describe how this model will be used (e.g. classroom education, healthcare accessibility, public kiosk)..." required></textarea>
        </div>

        <div class="form-group">
          <label for="training-additional">Additional Requirements <span class="optional">(Optional)</span></label>
          <textarea id="training-additional" rows="2" placeholder="Describe any existing dataset details, sample video links, or formatting preferences..."></textarea>
        </div>

        <div class="form-group">
          <label for="training-email">Contact Email</label>
          <input type="email" id="training-email" value="${prefilledEmail}" placeholder="your.email@example.com" />
          <small>We will send model updates and admin review decisions to this email.</small>
        </div>

        <div id="form-error-area" class="error-banner" style="display: none; margin-bottom: 1rem;"></div>

        <div class="form-actions">
          <button type="submit" id="submit-training-request-btn" class="primary-button full-width">
            Submit Training Request
          </button>
          <button type="button" id="cancel-request-btn" class="secondary-button full-width">
            Cancel
          </button>
        </div>
      </form>
    </div>
  `;

  const form = document.getElementById("custom-training-request-form");
  const cancelBtn = document.getElementById("cancel-request-btn");

  if (cancelBtn) {
    cancelBtn.addEventListener("click", hideCustomTrainingModal);
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (isSubmitting) return;

      const submitBtn = document.getElementById("submit-training-request-btn");
      const errorArea = document.getElementById("form-error-area");
      if (errorArea) errorArea.style.display = "none";

      const language = document.getElementById("training-language").value.trim();
      const country = document.getElementById("training-country").value.trim();
      const variant = document.getElementById("training-variant").value.trim();
      const description = document.getElementById("training-description").value.trim();
      const useCase = document.getElementById("training-usecase").value.trim();
      const additionalReqs = document.getElementById("training-additional").value.trim();
      const contactEmail = document.getElementById("training-email").value.trim();

      if (!language || !country || !description || !useCase) {
        if (errorArea) {
          errorArea.textContent = "Please fill in all required fields marked with *.";
          errorArea.style.display = "block";
        }
        return;
      }

      isSubmitting = true;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-sm"></span> Submitting Request...`;
      }

      try {
        const payload = {
          language,
          country,
          variant,
          description,
          use_case: useCase,
          additional_requirements: additionalReqs,
          contact_email: contactEmail,
        };

        const res = await apiFetch("/api/custom-training/request", {
          method: "POST",
          body: payload,
        });

        isSubmitting = false;

        if (res.success && res.data) {
          // Success -> Render Status View
          const userRequests = await loadRequests();
          renderStatusAndHistoryStep(container, userRequests, contactEmail);
        } else {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Submit Training Request";
          }
          if (errorArea) {
            errorArea.textContent = res.error || "Failed to submit training request.";
            errorArea.style.display = "block";
          }
        }
      } catch (err) {
        console.error("Failed to submit request:", err);
        isSubmitting = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Submit Training Request";
        }
        if (errorArea) {
          errorArea.textContent = "An error occurred while submitting your request. Please check your network connection.";
          errorArea.style.display = "block";
        }
      }
    });
  }
}

/**
 * Renders Request Status & Request History Step.
 */
function renderStatusAndHistoryStep(container, requests, userEmail) {
  const requestList = requests || [];

  container.innerHTML = `
    <div class="status-step-container">
      <div class="status-header">
        <h3>My Custom Model Training Requests</h3>
        <button id="new-request-btn" class="secondary-button btn-sm">Submit New Request</button>
      </div>

      <div class="requests-timeline-list">
        ${requestList.length === 0 ? '<p class="empty-text">No requests submitted yet.</p>' : requestList.map(req => `
          <div class="training-request-card">
            <div class="request-card-header">
              <h4>${escapeHtml(req.language)} ${req.variant ? `(${escapeHtml(req.variant)})` : ''}</h4>
              <span class="status-badge status-${req.status.toLowerCase()}">${formatStatusLabel(req.status)}</span>
            </div>
            <p class="request-country">📍 <strong>Region:</strong> ${escapeHtml(req.country || 'Not specified')}</p>
            <p class="request-desc">${escapeHtml(req.description)}</p>

            <div class="status-timeline">
              <div class="timeline-step completed">
                <span class="step-dot"></span>
                <span>Submitted</span>
                <span class="step-date">${new Date(req.created_at).toLocaleDateString()}</span>
              </div>
              <div class="timeline-step ${['PAID_PENDING_REVIEW', 'UNDER_REVIEW', 'TRAINING', 'VALIDATING', 'APPROVED'].includes(req.status) ? 'completed' : ''}">
                <span class="step-dot"></span>
                <span>Payment Verified</span>
              </div>
              <div class="timeline-step ${['UNDER_REVIEW', 'TRAINING', 'VALIDATING', 'APPROVED'].includes(req.status) ? 'completed' : ''}">
                <span class="step-dot"></span>
                <span>Under Review</span>
              </div>
              <div class="timeline-step ${['TRAINING', 'VALIDATING', 'APPROVED'].includes(req.status) ? 'completed' : ''}">
                <span class="step-dot"></span>
                <span>Training</span>
              </div>
              <div class="timeline-step ${req.status === 'APPROVED' ? 'completed' : ''}">
                <span class="step-dot"></span>
                <span>Approved</span>
              </div>
            </div>

            ${req.admin_notes ? `<div class="admin-notes-card"><strong>Admin Feedback:</strong> ${escapeHtml(req.admin_notes)}</div>` : ''}

            ${req.status === 'APPROVED' ? `
              <div style="margin-top: 1rem;">
                <button class="primary-button full-width open-workspace-btn" data-request-id="${req.request_id}">
                  🛠️ Open My Model Workspace
                </button>
              </div>
            ` : ''}
          </div>
        `).join('')}
      </div>

      <div class="status-actions">
        <button id="close-training-modal-btn" class="primary-button full-width">Done</button>
      </div>
    </div>
  `;

  const doneBtn = document.getElementById("close-training-modal-btn");
  const newReqBtn = document.getElementById("new-request-btn");

  if (doneBtn) doneBtn.addEventListener("click", hideCustomTrainingModal);
  if (newReqBtn) {
    newReqBtn.addEventListener("click", () => {
      renderRequestFormStep(container, userEmail);
    });
  }

  container.querySelectorAll(".open-workspace-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const requestId = btn.dataset.requestId;
      await openWorkspaceForRequest(container, requestId);
    });
  });
}

async function openWorkspaceForRequest(container, requestId) {
  try {
    const res = await apiFetch("/api/custom-training/workspaces");
    let workspaces = (res.success && res.data) ? res.data.workspaces : [];
    let ws = workspaces.find(w => w.request_id === requestId);
    if (!ws) {
      // Fetch or initialize
      const allRes = await apiFetch("/api/custom-training/workspaces");
      workspaces = (allRes.success && allRes.data) ? allRes.data.workspaces : [];
      ws = workspaces[0];
    }
    if (ws) {
      renderWorkspaceView(container, ws.model_id);
    } else {
      showError("Could not load custom model workspace.");
    }
  } catch (err) {
    console.error("Failed to open workspace:", err);
    showError("Workspace unavailable.");
  }
}

async function renderWorkspaceView(container, modelId) {
  container.innerHTML = `
    <div class="loading-spinner-container">
      <div class="spinner"></div>
      <p>Loading your model workspace...</p>
    </div>
  `;

  let workspace = null;
  try {
    const res = await apiFetch(`/api/custom-training/workspace/${modelId}`);
    if (res.success && res.data) {
      workspace = res.data.workspace;
    }
  } catch (e) {
    console.error("Workspace load error:", e);
  }

  if (!workspace) {
    container.innerHTML = `<p class="error-banner">Workspace not found.</p>`;
    return;
  }

  const labels = workspace.labels || ["A", "B", "C", "D", "E"];
  const sampleCounts = workspace.sample_counts || {};

  container.innerHTML = `
    <div class="workspace-container">
      <div class="workspace-header">
        <div>
          <h3>${escapeHtml(workspace.name)}</h3>
          <span class="status-badge status-${(workspace.status || 'awaiting').toLowerCase()}">
            Status: ${workspace.status || 'Awaiting Setup'}
          </span>
          <span class="status-badge status-online">Version ${workspace.version || 1}</span>
        </div>
        <button id="back-to-requests-btn" class="secondary-button btn-sm">← Back to Requests</button>
      </div>

      <!-- STEP 1: LABEL CONFIGURATION -->
      <div class="workspace-card">
        <h4>1. Select Target Letters / Gestures</h4>
        <p class="form-subtext">Specify the letters or sign labels you want this custom model to recognize.</p>
        <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
          <input type="text" id="workspace-labels-input" value="${labels.join(', ')}" placeholder="e.g. A, B, C, D, E" style="flex: 1;" />
          <button id="save-labels-btn" class="secondary-button">Save Labels</button>
        </div>
        <div class="labels-pills">
          ${labels.map(l => `<span class="label-pill">${escapeHtml(l)} (${sampleCounts[l] || 0}/30)</span>`).join('')}
        </div>
      </div>

      <!-- STEP 2: CAMERA SAMPLE COLLECTION -->
      <div class="workspace-card">
        <h4>2. Camera Sample Collection</h4>
        <p class="form-subtext">Collect gesture samples using your camera for each label.</p>
        <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 0.75rem;">
          <label><strong>Target Label:</strong></label>
          <select id="collect-label-select" class="form-select">
            ${labels.map(l => `<option value="${l}">${l} (Current count: ${sampleCounts[l] || 0})</option>`).join('')}
          </select>
          <button id="start-workspace-cam-btn" class="primary-button btn-sm">📷 Start Camera</button>
        </div>

        <div id="workspace-cam-preview-box" style="display: none; position: relative; max-width: 480px; margin: 0 auto;">
          <video id="ws-video" autoplay playsinline style="width: 100%; border-radius: 8px; background: #000;"></video>
          <canvas id="ws-canvas" style="display: none;"></canvas>
          <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem;">
            <button id="capture-sample-btn" class="primary-button full-width">Capture Sample Frame</button>
          </div>
        </div>
        <div id="sample-status-area" style="margin-top: 0.5rem;"></div>
      </div>

      <!-- STEP 3: MODEL TRAINING -->
      <div class="workspace-card">
        <h4>3. Train Your Custom Model</h4>
        <p class="form-subtext">Train a Random Forest classifier exclusively on your collected dataset.</p>
        <div id="train-metrics-area" style="margin-bottom: 0.75rem;">
          ${workspace.metrics && workspace.metrics.accuracy ? `
            <div class="verified-payment-banner">
              🎯 <strong>Trained Accuracy:</strong> ${workspace.metrics.accuracy}% | Samples: ${workspace.metrics.num_samples} | Classes: ${workspace.metrics.num_classes}
            </div>
          ` : ''}
        </div>
        <button id="train-custom-model-btn" class="primary-button full-width">
          🚀 Train My Model
        </button>
      </div>

      <!-- STEP 4: LIVE MODEL TESTING -->
      <div class="workspace-card">
        <h4>4. Test Your Trained Model</h4>
        <p class="form-subtext">Test sign recognition live with your custom model.</p>
        <button id="test-custom-model-btn" class="secondary-button full-width" ${workspace.status !== 'trained' ? 'disabled' : ''}>
          🧪 Test Custom Recognition
        </button>
        <div id="workspace-test-results" style="margin-top: 0.5rem; text-align: center; font-weight: bold; font-size: 1.2rem;"></div>
      </div>
    </div>
  `;

  // Bind Back Button
  const backBtn = document.getElementById("back-to-requests-btn");
  if (backBtn) {
    backBtn.addEventListener("click", async () => {
      const userRequests = await loadRequests();
      renderStatusAndHistoryStep(container, userRequests, "");
    });
  }

  // Bind Label Save
  const saveLabelsBtn = document.getElementById("save-labels-btn");
  if (saveLabelsBtn) {
    saveLabelsBtn.addEventListener("click", async () => {
      const val = document.getElementById("workspace-labels-input").value;
      const newLabels = val.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
      if (newLabels.length < 2) return alert("Please specify at least 2 labels.");
      saveLabelsBtn.disabled = true;
      const res = await apiFetch(`/api/custom-training/workspace/${modelId}/labels`, {
        method: "POST",
        body: { labels: newLabels }
      });
      saveLabelsBtn.disabled = false;
      if (res.success) {
        renderWorkspaceView(container, modelId);
      } else {
        alert(res.error || "Failed to update labels");
      }
    });
  }

  // Camera stream state
  let wsStream = null;
  const startCamBtn = document.getElementById("start-workspace-cam-btn");
  const camBox = document.getElementById("workspace-cam-preview-box");
  const videoElem = document.getElementById("ws-video");
  const captureBtn = document.getElementById("capture-sample-btn");
  const statusArea = document.getElementById("sample-status-area");

  if (startCamBtn) {
    startCamBtn.addEventListener("click", async () => {
      try {
        wsStream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoElem.srcObject = wsStream;
        camBox.style.display = "block";
        startCamBtn.disabled = true;
      } catch (err) {
        alert("Camera error: " + err.message);
      }
    });
  }

  // Sample capture
  if (captureBtn) {
    captureBtn.addEventListener("click", async () => {
      if (!wsStream) return alert("Please start the camera first.");
      const labelSelect = document.getElementById("collect-label-select");
      const label = labelSelect.value;
      captureBtn.disabled = true;
      statusArea.innerHTML = `<span class="spinner-sm"></span> Processing frame & extracting landmarks...`;

      const canvas = document.getElementById("ws-canvas");
      canvas.width = videoElem.videoWidth || 640;
      canvas.height = videoElem.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(videoElem, 0, 0);

      canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append("image", blob, "sample.jpg");
        formData.append("label", label);

        try {
          const token = localStorage.getItem("signbridge_token") || state.token || "";
          const response = await fetch(`/api/custom-training/workspace/${modelId}/collect-sample`, {
            method: "POST",
            headers: token ? { "Authorization": `Bearer ${token}` } : {},
            body: formData
          });
          const res = await response.json();
          captureBtn.disabled = false;
          if (res.success) {
            statusArea.innerHTML = `<span style="color: var(--color-success, green);">✅ Sample added for '${label}'!</span>`;
            setTimeout(() => renderWorkspaceView(container, modelId), 800);
          } else {
            statusArea.innerHTML = `<span style="color: var(--color-danger, red);">❌ ${res.error || "Capture failed"}</span>`;
          }
        } catch (e) {
          captureBtn.disabled = false;
          statusArea.innerHTML = `<span style="color: var(--color-danger, red);">❌ Network error capturing sample</span>`;
        }
      }, "image/jpeg", 0.9);
    });
  }

  // Model Train Button
  const trainBtn = document.getElementById("train-custom-model-btn");
  if (trainBtn) {
    trainBtn.addEventListener("click", async () => {
      trainBtn.disabled = true;
      trainBtn.innerHTML = `<span class="spinner-sm"></span> Training Random Forest Classifier...`;
      try {
        const res = await apiFetch(`/api/custom-training/workspace/${modelId}/train`, { method: "POST" });
        if (res.success) {
          alert(res.message || "Model trained successfully!");
          renderWorkspaceView(container, modelId);
        } else {
          trainBtn.disabled = false;
          trainBtn.textContent = "🚀 Train My Model";
          alert(res.error || "Training failed.");
        }
      } catch (e) {
        trainBtn.disabled = false;
        trainBtn.textContent = "🚀 Train My Model";
        alert("Error during model training.");
      }
    });
  }

  // Model Test Button
  const testBtn = document.getElementById("test-custom-model-btn");
  const testResultsArea = document.getElementById("workspace-test-results");
  if (testBtn) {
    testBtn.addEventListener("click", async () => {
      if (!wsStream) return alert("Please start the camera above to test!");
      const canvas = document.getElementById("ws-canvas");
      canvas.width = videoElem.videoWidth || 640;
      canvas.height = videoElem.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(videoElem, 0, 0);

      canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append("image", blob, "frame.jpg");
        try {
          const token = localStorage.getItem("signbridge_token") || state.token || "";
          const response = await fetch(`/api/custom-training/workspace/${modelId}/predict`, {
            method: "POST",
            headers: token ? { "Authorization": `Bearer ${token}` } : {},
            body: formData
          });
          const res = await response.json();
          if (res.success && res.data) {
            testResultsArea.innerHTML = `Predicted Sign: <span style="color: #6366f1;">${res.data.label || 'No Sign'}</span> (${(res.data.confidence * 100).toFixed(1)}%)`;
          } else {
            testResultsArea.innerHTML = `<span style="color: red;">Prediction error: ${res.error || 'Unknown'}</span>`;
          }
        } catch (e) {
          testResultsArea.innerHTML = `<span style="color: red;">Prediction network error</span>`;
        }
      }, "image/jpeg", 0.9);
    });
  }
}

async function loadRequests() {
  try {
    const res = await apiFetch("/api/custom-training/requests");
    if (res.success && res.data) {
      return res.data.requests;
    }
  } catch (e) {
    console.error("Failed to load requests:", e);
  }
  return [];
}

function formatStatusLabel(status) {
  const labels = {
    "DRAFT": "Draft",
    "PAYMENT_PENDING": "Payment Pending",
    "PAID_PENDING_REVIEW": "Paid - Pending Review",
    "UNDER_REVIEW": "Under Review",
    "NEEDS_INFORMATION": "Needs Info",
    "TRAINING": "Training in Progress",
    "VALIDATING": "Validating",
    "APPROVED": "Approved & Active",
    "REJECTED": "Rejected",
    "REFUNDED": "Refunded",
  };
  return labels[status] || status;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Initializes listeners for Custom Model Training controls.
 */
export function initCustomTraining() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("#custom-training-btn, .custom-training-trigger");
    if (btn) {
      e.preventDefault();
      showCustomTrainingModal();
    }
  });

  const closeBtn = document.getElementById("custom-training-modal-close");
  if (closeBtn) closeBtn.addEventListener("click", hideCustomTrainingModal);

  const modal = document.getElementById("custom-training-modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) hideCustomTrainingModal();
    });
  }
}