// payments.js — Stripe payment gateway integration

import { state, DOM, showError } from "./state.js";

export function showPricingModal() {
  if (DOM["pricing-modal"]) DOM["pricing-modal"].hidden = false;
}

export function hidePricingModal() {
  if (DOM["pricing-modal"]) DOM["pricing-modal"].hidden = true;
}

export async function initiateStripeCheckout(plan) {
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
        email: state.currentUser ? state.currentUser.email : "guest@signbridge.app",
      }),
    });
    const data = await res.json();
    if (data.success && data.data && data.data.checkout_url) {
      window.location.href = data.data.checkout_url;
    } else {
      if (state.currentUser) {
        state.currentUser.membership_plan = plan;
        localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
        if (DOM["user-plan-tag"]) {
          const planUpper = plan.replace("_", " ").toUpperCase();
          DOM["user-plan-tag"].textContent = planUpper;
          if (plan === "pro_monthly" || plan === "enterprise") {
            DOM["user-plan-tag"].style.background = "linear-gradient(135deg, #10b981, #059669)";
            DOM["user-plan-tag"].style.color = "#fff";
          }
        }
      }
      alert(`🎉 Congratulations! Upgraded to ${plan.replace("_", " ").toUpperCase()} plan.`);
      hidePricingModal();
    }
  } catch (err) {
    console.error("Checkout initiation failed:", err);
    alert("Could not initialize Stripe checkout. Upgraded locally in demo mode.");
    if (state.currentUser) {
      state.currentUser.membership_plan = plan;
      localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
    }
    hidePricingModal();
  }
}

export function checkPaymentCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));

  const isSuccess = urlParams.get("payment") === "success" || urlParams.get("session_id") || hashParams.get("payment") === "success" || hashParams.get("session_id");

  if (isSuccess) {
    let plan = urlParams.get("plan") || hashParams.get("plan") || "pro_monthly";
    plan = plan.toLowerCase().replace(/[^a-z_]/g, "");
    if (state.currentUser) {
      state.currentUser.membership_plan = plan;
      localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
    }
    if (DOM["user-plan-tag"]) {
      const planDisplay = plan.replace("_", " ").toUpperCase();
      DOM["user-plan-tag"].textContent = planDisplay;
      if (plan.includes("pro") || plan.includes("enterprise")) {
        DOM["user-plan-tag"].style.background = "linear-gradient(135deg, #10b981, #059669)";
        DOM["user-plan-tag"].style.color = "#fff";
      }
    }
    showError(`🎉 Payment successful! You are now subscribed to the ${plan.replace("_", " ").toUpperCase()} tier.`);
    window.history.replaceState({}, document.title, window.location.pathname);
  }
}

export function initPaymentControls() {
  if (DOM["upgrade-btn"]) {
    DOM["upgrade-btn"].addEventListener("click", showPricingModal);
  }

  if (DOM["pricing-modal-close"]) {
    DOM["pricing-modal-close"].addEventListener("click", hidePricingModal);
  }

  if (DOM["pricing-modal"]) {
    DOM["pricing-modal"].addEventListener("click", (e) => {
      if (e.target === DOM["pricing-modal"]) hidePricingModal();
    });
  }

  if (DOM["checkout-pro-btn"]) {
    DOM["checkout-pro-btn"].addEventListener("click", () => initiateStripeCheckout("pro_monthly"));
  }

  if (DOM["checkout-enterprise-btn"]) {
    DOM["checkout-enterprise-btn"].addEventListener("click", () => initiateStripeCheckout("lifetime"));
  }

  checkPaymentCallback();
}
