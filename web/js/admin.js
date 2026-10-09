// admin.js — Admin dashboard functionality

import { state, DOM, showError } from "./state.js";
import { apiFetch } from "./api.js";

export async function loadAdminDashboard() {
  const token = localStorage.getItem("signbridge_token") || "";
  if (!token) return null;

  try {
    const data = await apiFetch("/api/admin/dashboard");
    if (data.success && data.data) {
      renderAdminDashboard(data.data);
      return data.data;
    } else if (!data.success && data.error) {
      showError(data.error);
    }
  } catch (err) {
    console.error("Failed to load admin dashboard:", err);
    showError("Failed to load admin dashboard");
  }
  return null;
}

function renderAdminDashboard(stats) {
  const contentEl = document.getElementById("admin-dashboard-content");
  if (!contentEl) return;

  contentEl.innerHTML = `
    <div class="admin-stats-grid">
      <div class="stat-card">
        <h3>Users</h3>
        <div class="stat-value">${stats.users.total}</div>
        <div class="stat-breakdown">
          <span class="stat-item free">Free: ${stats.users.free}</span>
          <span class="stat-item premium">Premium: ${stats.users.premium}</span>
          <span class="stat-item lifetime">Lifetime: ${stats.users.lifetime}</span>
        </div>
      </div>
      <div class="stat-card">
        <h3>Custom Training</h3>
        <div class="stat-value">${stats.custom_training.total_requests}</div>
        <div class="stat-breakdown">
          <span class="stat-item pending">Pending: ${stats.custom_training.pending_review}</span>
          <span class="stat-item training">Training: ${stats.custom_training.training}</span>
          <span class="stat-item validating">Validating: ${stats.custom_training.validating}</span>
          <span class="stat-item approved">Approved: ${stats.custom_training.approved}</span>
          <span class="stat-item rejected">Rejected: ${stats.custom_training.rejected}</span>
        </div>
      </div>
      <div class="stat-card">
        <h3>Monthly Revenue</h3>
        <div class="stat-value">$${stats.revenue.monthly_total_usd.toFixed(2)}</div>
        <div class="stat-breakdown">
          <span class="stat-item">Subscriptions: $${stats.revenue.monthly_subscription_usd.toFixed(2)}</span>
          <span class="stat-item">Training: $${stats.revenue.monthly_training_usd.toFixed(2)}</span>
        </div>
      </div>
    </div>

    <div class="admin-sections">
      <section class="admin-section">
        <div class="section-header">
          <h3>Custom Training Requests</h3>
          <select id="training-status-filter" class="filter-select">
            <option value="">All Statuses</option>
            <option value="PAID_PENDING_REVIEW">Pending Review</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="NEEDS_INFORMATION">Needs Info</option>
            <option value="TRAINING">Training</option>
            <option value="VALIDATING">Validating</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
        <div id="admin-training-requests"></div>
      </section>

      <section class="admin-section">
        <div class="section-header">
          <h3>Recent Payments</h3>
        </div>
        <div id="admin-payments"></div>
      </section>

      <section class="admin-section">
        <div class="section-header">
          <h3>Language Registry</h3>
        </div>
        <div id="admin-languages"></div>
      </section>

      <section class="admin-section">
        <div class="section-header">
          <h3>User Management & Sub-Admins</h3>
        </div>
        <div class="admin-controls" style="margin-bottom: 1rem; display: flex; gap: 10px;">
          <input type="text" id="admin-user-search" placeholder="Search user by email..." class="form-input" style="max-width: 300px;">
          <button id="admin-user-search-btn" class="primary-button btn-sm">Search</button>
        </div>
        <div id="admin-users-list"></div>
      </section>
    </div>
  `;

  loadAdminTrainingRequests();
  loadAdminPayments();
  loadAdminLanguages();
  loadAdminUsers();

  const filterEl = document.getElementById("training-status-filter");
  if (filterEl) {
    filterEl.addEventListener("change", (e) => {
      loadAdminTrainingRequests(e.target.value);
    });
  }

  if (document.getElementById("admin-user-search-btn")) {
    document.getElementById("admin-user-search-btn").addEventListener("click", () => {
       const query = document.getElementById("admin-user-search").value;
       loadAdminUsers(1, query);
    });
  }
}

async function loadAdminUsers(page = 1, search = "") {
  try {
    const url = `/api/admin/users?page=${page}&search=${encodeURIComponent(search)}`;
    const data = await apiFetch(url);
    if (data.success && data.data) {
      renderAdminUsers(data.data);
    }
  } catch (err) {
    console.error("Failed to load users:", err);
  }
}

function renderAdminUsers(data) {
  const container = document.getElementById("admin-users-list");
  if (!container) return;

  const users = data.users || [];
  if (users.length === 0) {
    container.innerHTML = '<p class="no-requests">No users found.</p>';
    return;
  }

  container.innerHTML = `
    <table class="admin-table">
      <thead>
        <tr><th>Email</th><th>Name</th><th>Role</th><th>Actions</th></tr>
      </thead>
      <tbody>
        ${users.map(u => `
          <tr>
            <td>${u.email || u.clerk_id}</td>
            <td>${u.name || 'N/A'}</td>
            <td><span class="status-${u.role}">${u.role || 'user'}</span></td>
            <td>
              ${u.role === 'admin' 
                 ? `<button class="secondary-button btn-sm revoke-admin-btn" data-user="${u.clerk_id}">Revoke Admin</button>`
                 : `<button class="primary-button btn-sm grant-admin-btn" data-user="${u.clerk_id}">Make Admin</button>`
              }
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;

  container.querySelectorAll(".grant-admin-btn").forEach(btn => {
    btn.addEventListener("click", () => toggleAdminRole(btn.dataset.user, "grant"));
  });

  container.querySelectorAll(".revoke-admin-btn").forEach(btn => {
    btn.addEventListener("click", () => toggleAdminRole(btn.dataset.user, "revoke"));
  });
}

async function toggleAdminRole(userId, action) {
  if (!confirm(`Are you sure you want to ${action} admin role for this user?`)) return;
  
  try {
    const data = await apiFetch(`/api/admin/users/${userId}/admin`, {
      method: "POST",
      body: { action },
    });
    if (data.success) {
      showError(data.message || `Successfully updated admin role`);
      loadAdminUsers();
    } else {
      showError(data.error || "Failed to update admin role");
    }
  } catch (err) {
    console.error("Failed to update role:", err);
  }
}

async function loadAdminTrainingRequests(statusFilter = "") {
  try {
    const url = `/api/admin/training-requests${statusFilter ? `?status=${statusFilter}` : ''}`;
    const data = await apiFetch(url);
    if (data.success && data.data) {
      renderAdminTrainingRequests(data.data.requests);
    }
  } catch (err) {
    console.error("Failed to load training requests:", err);
  }
}

function renderAdminTrainingRequests(requests) {
  const container = document.getElementById("admin-training-requests");
  if (!container) return;

  if (requests.length === 0) {
    container.innerHTML = '<p class="no-requests">No training requests found.</p>';
    return;
  }

  container.innerHTML = requests.map(req => `
    <div class="admin-request-card" data-request-id="${req.request_id}" data-status="${req.status}">
      <div class="request-header">
        <div>
          <h4>${req.language} (${req.language_id})</h4>
          <span class="request-user">${req.user?.email || req.user_id}</span>
        </div>
        <span class="request-status status-${req.status.toLowerCase()}">${formatStatus(req.status)}</span>
      </div>
      <p class="request-description">${req.description}</p>
      <div class="request-meta">
        <span>Submitted: ${new Date(req.created_at).toLocaleString()}</span>
        <span>Payment: ${req.payment?.status || req.payment_status}</span>
      </div>
      <div class="request-actions">
        <button class="secondary-button btn-sm view-request-btn" data-request-id="${req.request_id}">View Details</button>
        ${req.status === 'PAID_PENDING_REVIEW' ? `
          <button class="primary-button btn-sm review-request-btn" data-request-id="${req.request_id}">Begin Review</button>
          <button class="secondary-button btn-sm reject-request-btn" data-request-id="${req.request_id}">Reject</button>
        ` : ''}
        ${['UNDER_REVIEW', 'NEEDS_INFORMATION'].includes(req.status) ? `
          <button class="primary-button btn-sm approve-request-btn" data-request-id="${req.request_id}">Approve</button>
          <button class="secondary-button btn-sm reject-request-btn" data-request-id="${req.request_id}">Reject</button>
        ` : ''}
        ${req.status === 'UNDER_REVIEW' ? `
          <button class="secondary-button btn-sm start-training-btn" data-request-id="${req.request_id}">Start Training</button>
        ` : ''}
        ${req.status === 'TRAINING' ? `
          <button class="primary-button btn-sm validate-request-btn" data-request-id="${req.request_id}">Mark Validating</button>
          <button class="secondary-button btn-sm reject-request-btn" data-request-id="${req.request_id}">Reject</button>
        ` : ''}
        ${req.status === 'VALIDATING' ? `
          <button class="primary-button btn-sm final-approve-btn" data-request-id="${req.request_id}">Final Approve</button>
          <button class="secondary-button btn-sm reject-request-btn" data-request-id="${req.request_id}">Reject</button>
        ` : ''}
      </div>
    </div>
  `).join('');

  container.querySelectorAll(".view-request-btn").forEach(btn => {
    btn.addEventListener("click", () => showAdminRequestDetail(btn.dataset.requestId));
  });
  // PAID_PENDING_REVIEW -> begin admin review
  container.querySelectorAll(".review-request-btn").forEach(btn => {
    btn.addEventListener("click", () => updateRequestStatus(btn.dataset.requestId, "UNDER_REVIEW"));
  });
  // UNDER_REVIEW or NEEDS_INFORMATION -> final approval
  container.querySelectorAll(".approve-request-btn").forEach(btn => {
    btn.addEventListener("click", () => updateRequestStatus(btn.dataset.requestId, "APPROVED"));
  });
  // UNDER_REVIEW -> hand off to model training pipeline
  container.querySelectorAll(".start-training-btn").forEach(btn => {
    btn.addEventListener("click", () => updateRequestStatus(btn.dataset.requestId, "TRAINING"));
  });
  // TRAINING -> mark ready for validation
  container.querySelectorAll(".validate-request-btn").forEach(btn => {
    btn.addEventListener("click", () => updateRequestStatus(btn.dataset.requestId, "VALIDATING"));
  });
  container.querySelectorAll(".reject-request-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const reason = prompt("Reason for rejection:");
      if (reason) updateRequestStatus(btn.dataset.requestId, "REJECTED", reason);
    });
  });
  // VALIDATING -> provide model path and approve
  container.querySelectorAll(".final-approve-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const modelPath = prompt("Model path/identifier:");
      if (modelPath) finalApproveRequest(btn.dataset.requestId, modelPath);
    });
  });
}

async function showAdminRequestDetail(requestId) {
  try {
    const data = await apiFetch(`/api/admin/training-request/${requestId}`);
    if (data.success && data.data) {
      renderRequestDetailModal(data.data.request);
    }
  } catch (err) {
    console.error("Failed to load request detail:", err);
  }
}

function renderRequestDetailModal(request) {
  const modal = document.createElement("div");
  modal.className = "modal-backdrop";
  modal.innerHTML = `
    <div class="modal-card modal-card-wide">
      <button class="modal-close" type="button">&times;</button>
      <div class="modal-header">
        <h2>Training Request: ${request.language} (${request.language_id})</h2>
      </div>
      <div class="request-detail">
        <div class="detail-section">
          <h4>User</h4>
          <p>Email: ${request.user?.email || 'N/A'}</p>
          <p>Name: ${request.user?.name || 'N/A'}</p>
          <p>Plan: ${request.user?.plan || 'N/A'}</p>
        </div>
        <div class="detail-section">
          <h4>Request</h4>
          <p>Language: ${request.language}</p>
          <p>Language ID: ${request.language_id}</p>
          <p>Country: ${request.country || 'N/A'}</p>
          <p>Variant: ${request.variant || 'N/A'}</p>
          <p>Description: ${request.description}</p>
          <p>Dataset Info: ${JSON.stringify(request.dataset_info || {})}</p>
        </div>
        <div class="detail-section">
          <h4>Status & Payment</h4>
          <p>Status: <span class="status-${request.status.toLowerCase()}">${formatStatus(request.status)}</span></p>
          <p>Payment: ${request.payment?.status || 'N/A'}</p>
          <p>Stripe Session: ${request.payment?.session_id || 'N/A'}</p>
        </div>
        <div class="detail-section">
          <h4>Admin Actions</h4>
          <div class="admin-actions">
            ${request.status === 'PAID_PENDING_REVIEW' ? `
              <button class="primary-button begin-review-detail-btn">Begin Review</button>
              <button class="secondary-button reject-detail-btn">Reject</button>
              <button class="secondary-button needs-info-btn">Request Info</button>
            ` : ''}
            ${request.status === 'UNDER_REVIEW' ? `
              <button class="primary-button approve-detail-btn">Approve</button>
              <button class="secondary-button start-training-detail-btn">Start Training</button>
              <button class="secondary-button reject-detail-btn">Reject</button>
              <button class="secondary-button needs-info-btn">Request Info</button>
            ` : ''}
            ${request.status === 'NEEDS_INFORMATION' ? `
              <button class="primary-button approve-detail-btn">Approve</button>
              <button class="secondary-button under-review-detail-btn">Return to Review</button>
              <button class="secondary-button reject-detail-btn">Reject</button>
            ` : ''}
            ${request.status === 'TRAINING' ? `
              <button class="primary-button validate-btn">Mark Validating</button>
              <button class="secondary-button reject-detail-btn">Reject</button>
              <button class="secondary-button needs-info-btn">Request Info</button>
            ` : ''}
            ${request.status === 'VALIDATING' ? `
              <button class="primary-button final-approve-detail-btn">Final Approve</button>
              <button class="secondary-button reject-detail-btn">Reject</button>
            ` : ''}
          </div>
          <textarea id="admin-notes" placeholder="Admin notes...">${request.admin_notes || ''}</textarea>
        </div>
        ${request.model_metadata && Object.keys(request.model_metadata).length > 0 ? `
          <div class="detail-section">
            <h4>Model Metadata</h4>
            <pre>${JSON.stringify(request.model_metadata, null, 2)}</pre>
          </div>
        ` : ''}
        ${request.validation_metrics && Object.keys(request.validation_metrics).length > 0 ? `
          <div class="detail-section">
            <h4>Validation Metrics</h4>
            <pre>${JSON.stringify(request.validation_metrics, null, 2)}</pre>
          </div>
        ` : ''}
      </div>
    </div>
  `;

  document.body.appendChild(modal);
  modal.hidden = false;

  modal.querySelector(".modal-close").onclick = () => modal.remove();

  const getAdminNotes = () => (modal.querySelector("#admin-notes")?.value || "").trim();
  const bindBtn = (sel, handler) => modal.querySelector(sel)?.addEventListener("click", () => { handler(); modal.remove(); });

  bindBtn(".begin-review-detail-btn", () => updateRequestStatus(request.request_id, "UNDER_REVIEW", getAdminNotes()));
  bindBtn(".approve-detail-btn",      () => updateRequestStatus(request.request_id, "APPROVED", getAdminNotes()));
  bindBtn(".start-training-detail-btn", () => updateRequestStatus(request.request_id, "TRAINING", getAdminNotes()));
  bindBtn(".under-review-detail-btn", () => updateRequestStatus(request.request_id, "UNDER_REVIEW", getAdminNotes()));
  bindBtn(".validate-btn",            () => updateRequestStatus(request.request_id, "VALIDATING", getAdminNotes()));
  bindBtn(".reject-detail-btn",       () => {
    const reason = getAdminNotes() || "Rejected by admin";
    updateRequestStatus(request.request_id, "REJECTED", reason);
  });
  bindBtn(".needs-info-btn",          () => {
    const reason = getAdminNotes() || "Additional information required";
    updateRequestStatus(request.request_id, "NEEDS_INFORMATION", reason);
  });
  bindBtn(".final-approve-detail-btn", () => {
    const modelPath = prompt("Model path/identifier:");
    if (modelPath) finalApproveRequest(request.request_id, modelPath, getAdminNotes());
  });
}

function formatStatus(status) {
  const labels = {
    "DRAFT": "Draft",
    "PAYMENT_PENDING": "Payment Pending",
    "PAID_PENDING_REVIEW": "Paid - Pending Review",
    "UNDER_REVIEW": "Under Review",
    "NEEDS_INFORMATION": "Needs Information",
    "TRAINING": "Training",
    "VALIDATING": "Validating",
    "APPROVED": "Approved",
    "REJECTED": "Rejected",
    "REFUNDED": "Refunded",
  };
  return labels[status] || status;
}

async function updateRequestStatus(requestId, newStatus, notes = "") {
  try {
    const data = await apiFetch(`/api/admin/training-request/${requestId}/status`, {
      method: "POST",
      body: { status: newStatus, notes },
    });
    if (data.success) {
      showError(`Request ${newStatus.toLowerCase().replace('_', ' ')}`);
      loadAdminTrainingRequests();
      loadAdminDashboard();
    } else {
      showError(data.error || "Failed to update status");
    }
  } catch (err) {
    console.error("Failed to update status:", err);
    showError("Failed to update status");
  }
}

async function finalApproveRequest(requestId, modelPath, notes = "") {
  try {
    const data = await apiFetch(`/api/admin/training-request/${requestId}/approve`, {
      method: "POST",
      body: { model_path: modelPath, notes },
    });
    if (data.success) {
      showError("Model approved and activated");
      loadAdminTrainingRequests();
      loadAdminDashboard();
    } else {
      showError(data.error || "Failed to approve");
    }
  } catch (err) {
    console.error("Failed to approve:", err);
    showError("Failed to approve");
  }
}

async function loadAdminPayments() {
  try {
    const data = await apiFetch("/api/admin/payments");
    if (data.success && data.data) {
      renderAdminPayments(data.data);
    }
  } catch (err) {
    console.error("Failed to load payments:", err);
  }
}

function renderAdminPayments(payments) {
  const container = document.getElementById("admin-payments");
  if (!container) return;

  const subs = payments.subscriptions || [];
  const training = payments.training_payments || [];

  container.innerHTML = `
    <h4>Subscription Payments</h4>
    <table class="admin-table">
      <thead>
        <tr><th>User</th><th>Plan</th><th>Amount</th><th>Status</th><th>Date</th></tr>
      </thead>
      <tbody>
        ${subs.slice(0, 20).map(p => `
          <tr>
            <td>${p.user_id}</td>
            <td>${p.plan}</td>
            <td>$${p.amount}</td>
            <td><span class="status-${p.status}">${p.status}</span></td>
            <td>${new Date(p.created_at).toLocaleString()}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <h4>Training Payments</h4>
    <table class="admin-table">
      <thead>
        <tr><th>User</th><th>Request</th><th>Amount</th><th>Status</th><th>Date</th></tr>
      </thead>
      <tbody>
        ${training.slice(0, 20).map(p => `
          <tr>
            <td>${p.user_id}</td>
            <td>${p.request_id}</td>
            <td>$${p.amount_usd}</td>
            <td><span class="status-${p.status}">${p.status}</span></td>
            <td>${new Date(p.created_at).toLocaleString()}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function loadAdminLanguages() {
  try {
    const data = await apiFetch("/api/admin/languages");
    if (data.success && data.data) {
      renderAdminLanguages(data.data.languages);
    }
  } catch (err) {
    console.error("Failed to load languages:", err);
  }
}

function renderAdminLanguages(languages) {
  const container = document.getElementById("admin-languages");
  if (!container) return;

  container.innerHTML = `
    <table class="admin-table">
      <thead>
        <tr><th>ID</th><th>Name</th><th>Native</th><th>Country</th><th>Variant</th><th>Status</th><th>Entitlement</th><th>Active</th><th>Actions</th></tr>
      </thead>
      <tbody>
        ${languages.map(lang => `
          <tr>
            <td>${lang.id}</td>
            <td>${lang.name}</td>
            <td>${lang.native_name}</td>
            <td>${lang.country}</td>
            <td>${lang.variant}</td>
            <td>${lang.status}</td>
            <td>${lang.required_entitlement}</td>
            <td><input type="checkbox" ${lang.is_active ? 'checked' : ''} data-lang="${lang.id}" class="lang-active-toggle"></td>
            <td>
              <button class="secondary-button btn-sm edit-lang-btn" data-lang="${lang.id}">Edit</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <button id="add-custom-lang-btn" class="primary-button btn-sm" style="margin-top: 1rem;">Add Custom Language</button>
  `;

  container.querySelectorAll(".lang-active-toggle").forEach(cb => {
    cb.addEventListener("change", (e) => {
      updateLanguage(e.target.dataset.lang, { is_active: e.target.checked });
    });
  });

  container.querySelectorAll(".edit-lang-btn").forEach(btn => {
    btn.addEventListener("click", () => showEditLanguageModal(btn.dataset.lang));
  });

  if (DOM["add-custom-lang-btn"]) {
    DOM["add-custom-lang-btn"].addEventListener("click", showAddCustomLanguageModal);
  }
}

async function updateLanguage(languageId, updates) {
  try {
    const data = await apiFetch("/api/admin/languages", {
      method: "POST",
      body: { language_id: languageId, updates },
    });
    if (data.success) {
      showError("Language updated");
      loadAdminLanguages();
    } else {
      showError(data.error || "Failed to update");
    }
  } catch (err) {
    console.error("Failed to update language:", err);
  }
}

function showEditLanguageModal(languageId) {
  const field = prompt("Field to update (status, required_entitlement, is_active, sort_order):");
  if (!field) return;
  const value = prompt(`New value for ${field}:`);
  if (value === null) return;
  
  let parsedValue = value;
  if (value === "true") parsedValue = true;
  else if (value === "false") parsedValue = false;
  else if (!isNaN(value)) parsedValue = Number(value);
  
  updateLanguage(languageId, { [field]: parsedValue });
}

async function showAddCustomLanguageModal() {
  const id = prompt("Language ID (e.g., custom_mylang):");
  if (!id) return;
  const name = prompt("Language Name:");
  if (!name) return;
  const nativeName = prompt("Native Name:");
  if (!nativeName) return;
  const country = prompt("Country Code (e.g., US):");
  if (!country) return;
  const variant = prompt("Variant (e.g., Custom):");
  if (!variant) return;
  const modelId = prompt("Model ID:");
  if (!modelId) return;

  try {
    const data = await apiFetch("/api/admin/languages/custom", {
      method: "POST",
      body: { id, name, native_name: nativeName, country, variant, model_id: modelId },
    });
    if (data.success) {
      showError("Custom language added");
      loadAdminLanguages();
    } else {
      showError(data.error || "Failed to add");
    }
  } catch (err) {
    console.error("Failed to add custom language:", err);
  }
}

export function showAdminDashboard() {
  const page = document.getElementById("admin-dashboard-page");
  const modeS = document.getElementById("mode-sign-to-voice");
  const modeV = document.getElementById("mode-voice-to-sign");
  const shell = document.getElementById("app-shell");
  if (page) page.hidden = false;
  if (modeS) modeS.hidden = true;
  if (modeV) modeV.hidden = true;
  if (shell) shell.hidden = false;
  loadAdminDashboard();
}

export function hideAdminDashboard() {
  const page = document.getElementById("admin-dashboard-page");
  const modeS = document.getElementById("mode-sign-to-voice");
  if (page) page.hidden = true;
  if (modeS) modeS.hidden = false;
}

export function initAdmin() {
  document.addEventListener("click", (e) => {
    const adminBtn = e.target.closest("#admin-btn, .admin-nav-btn");
    if (adminBtn) {
      e.preventDefault();
      showAdminDashboard();
    }
    const backBtn = e.target.closest("#admin-back-btn");
    if (backBtn) {
      e.preventDefault();
      hideAdminDashboard();
    }
  });
}