// payments.js — Stripe payment gateway integration

import { state, DOM, showError } from "./state.js";
import { apiFetch } from "./api.js";

let stripePromise = null;
let plansLoaded = false;

// ── Modal open/close ──────────────────────────────────────────────
export function showPricingModal() {
  const modal = document.getElementById("pricing-modal");
  if (modal) modal.hidden = false;
  if (!plansLoaded) {
    loadPlansIntoModal();
  }
}

export function hidePricingModal() {
  const modal = document.getElementById("pricing-modal");
  if (modal) modal.hidden = true;
}

// ── Load & render plans into the in-app modal ────────────────────
async function loadPlansIntoModal() {
  const grid = document.getElementById("pricing-modal-grid");
  if (!grid) return;

  grid.innerHTML = "<p style='text-align:center;opacity:.6'>Loading plans…</p>";

  try {
    const data = await apiFetch("/api/payment/plans", { requireAuth: false });
    if (data.success && data.data) {
      renderPlansInGrid(grid, data.data);
      plansLoaded = true;
    } else {
      grid.innerHTML =
        "<p style='color:#f87171;text-align:center'>Unable to load plans — check server.</p>";
    }
  } catch (err) {
    console.error("Failed to load plans:", err);
    grid.innerHTML =
      "<p style='color:#f87171;text-align:center'>Unable to load plans — check server.</p>";
  }
}

function renderPlansInGrid(grid, plans) {
  const planOrder = ["free", "premium", "lifetime"];
  const currentPlan = (state.currentUser?.plan || state.currentUser?.membership_plan || "free").toLowerCase();

  grid.innerHTML = planOrder
    .map((planId) => {
      const plan = plans[planId];
      if (!plan) return "";

      const priceDisplay =
        plan.price_usd === 0 ? "Free" : `$${plan.price_usd.toFixed(2)}`;
      const inrDisplay =
        plan.price_usd > 0
          ? `≈ ₹${Math.round(plan.price_inr || plan.price_usd * 83).toLocaleString("en-IN")}`
          : "";
      const interval =
        plan.billing_interval === "month"
          ? "/month"
          : plan.price_usd > 0 && !plan.billing_interval
          ? " one-time"
          : "";
      const isPopular = planId === "premium";
      const features = buildFeatureList(plan, planId);

      const isCurrent = (currentPlan === planId);
      const btnHtml = isCurrent
        ? `<button class="secondary-button full-width" disabled>Current ${plan.name}</button>`
        : `<button class="primary-button full-width pricing-card-btn" data-plan="${planId}">
             ${planId === "premium" ? "Upgrade to Premium" : "Get Lifetime Access"}
           </button>`;

      return `
        <div class="pricing-card${isPopular ? " pricing-card-featured" : ""}${isCurrent ? " pricing-card-active" : ""}">
          ${isPopular ? '<div class="featured-tag">MOST POPULAR</div>' : ""}
          <div class="pricing-header">
            <h3>${plan.name}</h3>
            <p class="price">${priceDisplay}<span>${interval}</span></p>
            ${inrDisplay ? `<p class="price-inr">${inrDisplay} <small style="opacity:.6">(approx. INR)</small></p>` : ""}
            <p style="font-size:.8rem;opacity:.7;margin-top:.5rem">${plan.description}</p>
          </div>
          <ul class="pricing-features">
            ${features.map((f) => `<li>${f}</li>`).join("")}
          </ul>
          ${btnHtml}
        </div>
      `;
    })
    .join("");

  grid.querySelectorAll(".pricing-card-btn[data-plan]").forEach((btn) => {
    btn.addEventListener("click", () => initiateStripeCheckout(btn.dataset.plan));
  });
}

function buildFeatureList(plan, planId) {
  const f = plan.features || {};
  const list = [];
  if (f.productive_hours_monthly) list.push(`✓ ${f.productive_hours_monthly} productive hours/month`);
  if (f.unlimited_usage) list.push("✓ Unlimited productive usage");
  if (f.languages && f.languages.length) {
    list.push(`✓ ${f.languages.length} supported language${f.languages.length > 1 ? "s" : ""}`);
  }
  if (f.ai_assistant) list.push("✓ AI Assistant (coming soon)");
  if (planId === "lifetime") list.push("✓ All future regional language packs");
  if (!list.length) list.push("✓ Core SignBridge features");
  return list;
}

// ── Stripe lazy-loader ────────────────────────────────────────────
async function getStripe() {
  if (!stripePromise) {
    const configData = await apiFetch("/api/auth/config", { requireAuth: false });
    const publishableKey = configData.data?.stripe_publishable_key || "";
    if (!publishableKey) return null;

    if (window.Stripe) {
      stripePromise = Promise.resolve(window.Stripe(publishableKey));
    } else {
      stripePromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://js.stripe.com/v3/";
        script.async = true;
        script.onload = () => resolve(window.Stripe(publishableKey));
        script.onerror = () => reject(new Error("Failed to load Stripe.js"));
        document.head.appendChild(script);
      });
    }
  }
  return stripePromise;
}

// ── Plan upgrade helper ───────────────────────────────────────────
function applyPlanUpgrade(plan) {
  if (state.currentUser) {
    state.currentUser.membership_plan = plan;
    state.currentUser.plan = plan;
    localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
  }
  const planTag = document.getElementById("user-plan-tag");
  if (planTag) {
    planTag.textContent = plan.replace("_", " ").toUpperCase();
    if (plan === "premium" || plan === "lifetime") {
      planTag.style.background = "linear-gradient(135deg, #10b981, #059669)";
      planTag.style.color = "#fff";
    }
  }
  showError(`🎉 Payment successful! You are now on the ${plan.replace("_", " ").toUpperCase()} plan.`);
  window.history.replaceState({}, document.title, window.location.pathname);
  
  import("./usage.js").then(({ loadUsageSummary }) => {
    if (loadUsageSummary) loadUsageSummary();
  });
}

// ── Stripe Checkout ───────────────────────────────────────────────
export async function initiateStripeCheckout(plan) {
  try {
    const data = await apiFetch("/api/payment/create-checkout-session", {
      method: "POST",
      body: {
        plan_id: plan,
        email: state.currentUser ? state.currentUser.email : "guest@signbridge.app",
      },
    });

    if (data.success && data.data && data.data.checkout_url) {
      window.location.href = data.data.checkout_url;
    } else {
      showError(data.error || "Checkout unavailable. Please try again.");
    }
  } catch (err) {
    console.error("Checkout initiation failed:", err);
    showError("Could not connect to payment server. Please try again.");
  }
}

// ── Verify payment after redirect back ───────────────────────────
export async function checkPaymentCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));

  const sessionId = urlParams.get("session_id") || hashParams.get("session_id");
  let plan = urlParams.get("plan") || hashParams.get("plan") || "premium";
  plan = plan.toLowerCase().replace(/[^a-z_]/g, "");

  const isSuccess =
    urlParams.get("payment") === "success" ||
    sessionId ||
    hashParams.get("payment") === "success";

  if (!isSuccess) return;

  if (sessionId) {
    try {
      const data = await apiFetch("/api/payment/verify-session", {
        method: "POST",
        body: { session_id: sessionId },
      });
      if (data.success && data.data && data.data.payment_status === "paid") {
        const verifiedPlan = data.data.plan_id || plan;
        applyPlanUpgrade(verifiedPlan);

        if (verifiedPlan === "custom_training") {
          import("./custom-training.js").then((mod) => {
            if (mod && mod.showCustomTrainingModal) {
              mod.showCustomTrainingModal();
            }
          });
        }
      } else {
        showError("Payment could not be verified. If you completed checkout, please refresh.");
      }
    } catch (err) {
      console.error("Payment verification failed:", err);
      showError("Could not verify payment. Check your email for a receipt.");
    }
  }
}

// ── Init ──────────────────────────────────────────────────────────
export function initPaymentControls() {
  const closeBtn = document.getElementById("pricing-modal-close");
  if (closeBtn) closeBtn.addEventListener("click", hidePricingModal);

  const modal = document.getElementById("pricing-modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) hidePricingModal();
    });
  }

  document.addEventListener("click", (e) => {
    const billingOrUpgrade = e.target.closest("#billing-btn, #upgrade-btn, .pro-badge-button, .upgrade-from-usage");
    if (billingOrUpgrade) {
      e.preventDefault();
      showPricingModal();
      return;
    }

    const btn = e.target.closest(".pricing-card-btn[data-plan]");
    if (btn && btn.dataset.plan) {
      initiateStripeCheckout(btn.dataset.plan);
    }
  });

  checkPaymentCallback();
}
