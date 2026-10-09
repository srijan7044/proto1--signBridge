// usage.js — Productive usage tracking and dashboard

import { state, DOM, showError } from "./state.js";
import { apiFetch, getAuthToken } from "./api.js";

let usageInterval = null;
let currentSessionId = null;

export async function startUsageTracking(activityType = "sign_recognition") {
  if (!state.currentUser || state.currentUser.plan === "premium" || state.currentUser.plan === "lifetime") {
    return { unlimited: true };
  }

  try {
    const data = await apiFetch("/api/usage/start", {
      method: "POST",
      body: { activity_type: activityType },
    });
    if (data.success && data.data) {
      currentSessionId = data.data.session?.session_id;
      startHeartbeat();
      updateUsageDashboard(data.data);
      return data.data;
    } else if (data.data?.limit_reached) {
      showLimitReachedModal(data.data.usage);
    }
  } catch (err) {
    console.error("Failed to start usage tracking:", err);
  }
  return null;
}

export function startHeartbeat() {
  if (usageInterval) return;
  usageInterval = setInterval(async () => {
    if (!currentSessionId) return;
    await sendHeartbeat();
  }, 30000);
}

export async function sendHeartbeat() {
  if (!currentSessionId) return;

  try {
    const data = await apiFetch("/api/usage/heartbeat", {
      method: "POST",
      body: { session_id: currentSessionId },
    });
    if (data.success) {
      updateUsageDashboard({ accumulated_seconds: data.data.accumulated_seconds });
    } else if (data.data?.limit_reached) {
      stopUsageTracking();
      showLimitReachedModal(data.data.usage);
    }
  } catch (err) {
    console.error("Heartbeat failed:", err);
  }
}

export async function stopUsageTracking() {
  if (!currentSessionId) return;

  try {
    const data = await apiFetch("/api/usage/stop", {
      method: "POST",
      body: { session_id: currentSessionId },
    });
    if (data.success) {
      currentSessionId = null;
      if (usageInterval) {
        clearInterval(usageInterval);
        usageInterval = null;
      }
    }
  } catch (err) {
    console.error("Failed to stop usage tracking:", err);
  }
}

export async function loadUsageSummary() {
  const token = await getAuthToken();
  if (!token) return null;

  try {
    const data = await apiFetch("/api/usage/summary");
    if (data.success && data.data) {
      updateUsageDashboard(data.data.usage);
      updateUserProfileUsage(data.data.usage);
      return data.data;
    }
  } catch (err) {
    console.error("Failed to load usage summary:", err);
  }
  return null;
}

function updateUsageDashboard(usageData) {
  if (!DOM["usage-dashboard"]) return;

  const usage = usageData.usage || usageData;
  const used = usage.used_seconds || usage.accumulated_seconds || 0;
  const allowance = usage.allowance_seconds || 14400;
  const remaining = Math.max(0, allowance - used);
  const percentage = Math.min(100, (used / allowance) * 100);

  if (state.currentUser && (state.currentUser.plan === "free" || !state.currentUser.plan)) {
    DOM["usage-dashboard"].hidden = false;
  } else {
    DOM["usage-dashboard"].hidden = true;
    return;
  }

  if (DOM["usage-fill"]) {
    DOM["usage-fill"].style.width = `${percentage}%`;
    DOM["usage-fill"].style.backgroundColor = percentage >= 100 ? "#ef4444" : percentage >= 80 ? "#f59e0b" : "#10b981";
  }

  if (DOM["usage-used"]) {
    DOM["usage-used"].textContent = `${formatSeconds(used)} used`;
  }
  if (DOM["usage-remaining"]) {
    DOM["usage-remaining"].textContent = `${formatSeconds(remaining)} remaining`;
  }

  if (DOM["usage-message"]) {
    if (percentage >= 100) {
      DOM["usage-message"].textContent = "Monthly allowance exhausted. Upgrade for unlimited usage.";
      DOM["usage-message"].style.color = "#ef4444";
      if (DOM["upgrade-from-usage"]) DOM["upgrade-from-usage"].hidden = false;
    } else if (percentage >= 80) {
      DOM["usage-message"].textContent = `You've used ${percentage.toFixed(0)}% of your monthly allowance.`;
      DOM["usage-message"].style.color = "#f59e0b";
    } else {
      DOM["usage-message"].textContent = `You have ${formatSeconds(remaining)} remaining this month.`;
      DOM["usage-message"].style.color = "#10b981";
    }
  }
}

function updateUserProfileUsage(usage) {
  if (!DOM["user-usage-summary"] || !DOM["user-usage-text"]) return;

  const used = usage.used_seconds || 0;
  const allowance = usage.allowance_seconds || 14400;
  const percentage = allowance > 0 ? Math.min(100, Math.round((used / allowance) * 100)) : 0;

  if (state.currentUser && (state.currentUser.plan === "free" || !state.currentUser.plan)) {
    DOM["user-usage-summary"].hidden = false;
    DOM["user-usage-text"].textContent = `${percentage}%`;
  } else {
    DOM["user-usage-summary"].hidden = true;
  }
}

function formatSeconds(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
  return parts.join(" ");
}

function showLimitReachedModal(usage) {
  if (!DOM["limit-reached-modal"]) return;

  const used = usage.used_seconds || 0;
  const allowance = usage.allowance_seconds || 14400;
  const remaining = Math.max(0, allowance - used);

  if (DOM["limit-message"]) {
    DOM["limit-message"].textContent = `You've used ${formatSeconds(used)} of your ${formatSeconds(allowance)} monthly allowance.`;
  }
  if (DOM["limit-details"]) {
    DOM["limit-details"].innerHTML = `
      <p><strong>Used:</strong> ${formatSeconds(used)}</p>
      <p><strong>Remaining:</strong> ${formatSeconds(remaining)}</p>
      <p><strong>Resets:</strong> ${usage.period_end ? new Date(usage.period_end).toLocaleDateString() : "Start of next month"}</p>
    `;
  }

  DOM["limit-reached-modal"].hidden = false;

  if (DOM["limit-upgrade-premium"]) {
    DOM["limit-upgrade-premium"].onclick = () => {
      import("./payments.js").then(({ initiateStripeCheckout }) => {
        initiateStripeCheckout("premium");
        DOM["limit-reached-modal"].hidden = true;
      });
    };
  }
  if (DOM["limit-upgrade-lifetime"]) {
    DOM["limit-upgrade-lifetime"].onclick = () => {
      import("./payments.js").then(({ initiateStripeCheckout }) => {
        initiateStripeCheckout("lifetime");
        DOM["limit-reached-modal"].hidden = true;
      });
    };
  }
  if (DOM["limit-continue-free"]) {
    DOM["limit-continue-free"].onclick = () => {
      DOM["limit-reached-modal"].hidden = true;
    };
  }
  if (DOM["limit-modal-close"]) {
    DOM["limit-modal-close"].onclick = () => {
      DOM["limit-reached-modal"].hidden = true;
    };
  }
}

export function initUsageTracking() {
  if (DOM["camera-toggle"]) {
    DOM["camera-toggle"].addEventListener("change", async () => {
      if (DOM["camera-toggle"].checked) {
        await startUsageTracking("sign_recognition");
      } else {
        stopUsageTracking();
      }
    });
  }

  if (DOM["toggle-realtime"]) {
    DOM["toggle-realtime"].addEventListener("click", async () => {
      if (!state.isRealtimeActive) {
        await startUsageTracking("sign_recognition");
      } else {
        stopUsageTracking();
      }
    });
  }

  if (state.currentUser) {
    loadUsageSummary();
  }

  window.addEventListener("signbridge:user-unlocked", () => {
    loadUsageSummary();
  });

  if (DOM["generate-sign-btn"]) {
    DOM["generate-sign-btn"].addEventListener("click", async () => {
      if (!currentSessionId) {
        await startUsageTracking("text_to_sign");
      }
    });
  }

  window.addEventListener("beforeunload", () => {
    stopUsageTracking();
  });
}