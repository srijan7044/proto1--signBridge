// payments.js — Stripe payment gateway integration (Test Mode)

import { state, DOM, showError } from "./state.js";

let stripePromise = null;

export function showPricingModal() {
  if (DOM["pricing-modal"]) DOM["pricing-modal"].hidden = false;
}

export function hidePricingModal() {
  if (DOM["pricing-modal"]) DOM["pricing-modal"].hidden = true;
}

async function getStripe() {
  if (!stripePromise) {
    const res = await fetch("/api/auth/config");
    const configData = await res.json();
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

function applyPlanUpgrade(plan) {
  if (state.currentUser) {
    state.currentUser.membership_plan = plan;
    localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
  }
  if (DOM["user-plan-tag"]) {
    const planDisplay = plan.replace("_", " ").toUpperCase();
    DOM["user-plan-tag"].textContent = planDisplay;
    if (plan.includes("pro") || plan.includes("enterprise") || plan.includes("lifetime")) {
      DOM["user-plan-tag"].style.background = "linear-gradient(135deg, #10b981, #059669)";
      DOM["user-plan-tag"].style.color = "#fff";
    }
  }
  showError(`🎉 Payment successful! You are now subscribed to the ${plan.replace("_", " ").toUpperCase()} tier.`);
  window.history.replaceState({}, document.title, window.location.pathname);
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
      if (data.data.simulated) {
        window.location.href = data.data.checkout_url;
      } else if (data.data.session_id) {
        const stripe = await getStripe();
        if (stripe) {
          const { error } = await stripe.redirectToCheckout({
            sessionId: data.data.session_id,
          });
          if (error) {
            console.error("Stripe redirect error:", error.message);
            alert("Could not redirect to Stripe checkout. Please try again.");
          }
        } else {
          window.location.href = data.data.checkout_url;
        }
      } else {
        window.location.href = data.data.checkout_url;
      }
    } else {
      if (state.currentUser) {
        state.currentUser.membership_plan = plan;
        localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
        if (DOM["user-plan-tag"]) {
          const planUpper = plan.replace("_", " ").toUpperCase();
          DOM["user-plan-tag"].textContent = planUpper;
          if (plan === "pro_monthly" || plan === "enterprise" || plan === "lifetime") {
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

export async function checkPaymentCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));

  const isSuccess =
    urlParams.get("payment") === "success" ||
    urlParams.get("session_id") ||
    hashParams.get("payment") === "success" ||
    hashParams.get("session_id");

  if (!isSuccess) return;

  const sessionId = urlParams.get("session_id") || hashParams.get("session_id");
  let plan = urlParams.get("plan") || hashParams.get("plan") || "pro_monthly";
  plan = plan.toLowerCase().replace(/[^a-z_]/g, "");

  const token = localStorage.getItem("signbridge_token") || "";
  if (sessionId) {
    try {
      const res = await fetch("/api/payment/verify-session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      if (data.success && data.data && data.data.payment_status === "paid") {
        const verifiedPlan = data.data.plan_id || plan;
        applyPlanUpgrade(verifiedPlan);
      } else {
        showError("Payment could not be verified. If you just completed checkout, wait a moment and refresh.");
      }
    } catch (err) {
      console.error("Payment verification failed:", err);
      showError("Could not verify payment. Please check your email for a receipt and try again later.");
    }
  } else {
    showError("No session ID found in the URL.");
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
