// pricing-page.js — Pricing page UI and plan selection

import { initDOMElements, DOM } from "./state.js";
import { initThemeToggle } from "./theme.js";
import { initiateStripeCheckout } from "./payments.js";

async function loadPlans() {
  try {
    const res = await fetch("/api/payment/plans");
    const data = await res.json();
    if (data.success && data.data) {
      renderPlans(data.data);
    }
  } catch (err) {
    console.error("Failed to load plans:", err);
    renderPlansFallback();
  }
}

function renderPlans(plans) {
  const grid = document.getElementById("pricing-grid");
  if (!grid) return;

  const planOrder = ["free", "premium", "lifetime"];
  const planCards = planOrder.map(planId => {
    const plan = plans[planId];
    if (!plan) return "";

    const isCurrentPlan = planId === "free"; // We don't know user's plan here
    const isPopular = planId === "premium";
    const priceDisplay = plan.price_usd === 0 ? "Free" : `$${plan.price_usd.toFixed(2)}`;
    const inrDisplay = plan.price_inr > 0 ? `≈ ₹${plan.price_inr.toLocaleString()}` : "";
    const billingInterval = plan.billing_interval ? `/ ${plan.billing_interval}` : " one-time";

    const features = getPlanFeatures(plan);

    return `
      <div class="pricing-card ${isPopular ? 'pricing-card-featured' : ''} ${isCurrentPlan ? 'current-plan' : ''}" data-plan="${planId}">
        ${isPopular ? '<div class="featured-tag">MOST POPULAR</div>' : ''}
        ${isCurrentPlan ? '<div class="current-tag">CURRENT</div>' : ''}
        <div class="pricing-header">
          <h3>${plan.name}</h3>
          <p class="price">${priceDisplay} <span>${billingInterval}</span></p>
          ${inrDisplay ? `<p class="price-inr">${inrDisplay}</p>` : ''}
        </div>
        <ul class="pricing-features">
          ${features.map(f => `<li>${f}</li>`).join('')}
        </ul>
        <button class="${isCurrentPlan ? 'secondary-button' : 'primary-button'} full-width" 
                data-plan="${planId}" 
                ${isCurrentPlan ? 'disabled' : ''}
                onclick="initiateStripeCheckout('${planId}')">
          ${isCurrentPlan ? 'Current Plan' : (plan.price_usd === 0 ? 'Get Started' : `Upgrade to ${plan.name}`)}
        </button>
      </div>
    `;
  }).join('');

  grid.innerHTML = planCards;
}

function getPlanFeatures(plan) {
  const features = plan.features || {};
  const featureList = [];

  if (features.productive_hours_monthly) {
    featureList.push(`✓ ${features.productive_hours_monthly} productive hours/month`);
  } else if (features.unlimited_usage) {
    featureList.push('✓ Unlimited productive usage');
  }

  if (features.languages && features.languages.length > 0) {
    const langNames = features.languages.map(code => getLanguageName(code)).join(', ');
    featureList.push(`✓ Languages: ${langNames}`);
  }

  if (features.ai_assistant) {
    featureList.push('✓ AI Assistant (coming soon)');
  }

  if (plan.id === 'lifetime' && features.languages) {
    featureList.push('✓ All regional language packs');
  }

  if (plan.id === 'custom_training') {
    featureList.push('✓ Custom model training request');
    featureList.push('✓ Admin review & approval');
    featureList.push('✓ Model activation upon approval');
  }

  return featureList.length > 0 ? featureList : ['✓ Core SignBridge features'];
}

function getLanguageName(code) {
  const names = {
    'en': 'English',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'or': 'Odia',
    'as': 'Assamese',
    'regional': 'Regional variants'
  };
  return names[code] || code;
}

function renderPlansFallback() {
  const grid = document.getElementById("pricing-grid");
  if (!grid) return;
  grid.innerHTML = '<p class="error">Unable to load plans. Please try again later.</p>';
}

// Initialize
initDOMElements();
initThemeToggle();
loadPlans();

// Make initiateStripeCheckout globally available for inline onclick
window.initiateStripeCheckout = initiateStripeCheckout;