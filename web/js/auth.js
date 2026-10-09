// auth.js — Clerk authentication and OTP fallback

import { state, DOM } from "./state.js";
import { apiFetch } from "./api.js";

let clerkSignInMounted = false;
let clerkUserButtonMounted = false;
let clerkCapturedEmail = "";
let otpPopupActive = false;

export function extractClerkDomain(publishableKey) {
  try {
    const b64 = publishableKey.split("_")[2] || "";
    const decoded = atob(b64);
    return decoded.replace(/\$$/, "");
  } catch (_) {
    return "brief-dingo-2050.clerk.accounts.dev";
  }
}

export function loadClerkSDK(publishableKey) {
  if (window.Clerk && (window.Clerk.loaded || typeof window.Clerk.mountSignIn === "function")) {
    return Promise.resolve(window.Clerk);
  }
  if (window.Clerk && typeof window.Clerk.load === "function") {
    return window.Clerk.load().then(() => window.Clerk).catch(() => window.Clerk);
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-clerk-sdk]");
    if (existing) existing.remove();

    const domain = extractClerkDomain(publishableKey);
    const script = document.createElement("script");
    script.setAttribute("data-clerk-sdk", "true");
    script.setAttribute("data-clerk-publishable-key", publishableKey);
    script.src = `https://${domain}/npm/@clerk/clerk-js@5/dist/clerk.browser.js`;
    script.crossOrigin = "anonymous";
    script.onload = async () => {
      try {
        if (window.Clerk) {
          if (!window.Clerk.loaded && typeof window.Clerk.load === "function") {
            await window.Clerk.load();
          }
          resolve(window.Clerk);
        } else {
          reject(new Error("Clerk object not found on window"));
        }
      } catch (e) {
        reject(e);
      }
    };
    script.onerror = () => {
      const fallbackScript = document.createElement("script");
      fallbackScript.setAttribute("data-clerk-sdk", "true");
      fallbackScript.setAttribute("data-clerk-publishable-key", publishableKey);
      fallbackScript.src = "https://cdn.jsdelivr.net/npm/@clerk/clerk-js@latest/dist/clerk.browser.js";
      fallbackScript.crossOrigin = "anonymous";
      fallbackScript.onload = async () => {
        try {
          if (window.Clerk) {
            if (!window.Clerk.loaded && typeof window.Clerk.load === "function") {
              await window.Clerk.load();
            }
            resolve(window.Clerk);
          } else {
            reject(new Error("Clerk object not found"));
          }
        } catch (e) {
          reject(e);
        }
      };
      fallbackScript.onerror = () => reject(new Error("Failed to load Clerk JS SDK from CDN"));
      document.head.appendChild(fallbackScript);
    };
    document.head.appendChild(script);
  });
}

export function getClerkAppearance() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || document.documentElement.dataset.theme || "dark";
  const isDark = currentTheme !== "light";

  if (isDark) {
    return {
      variables: {
        colorPrimary: "#38bdf8",
        colorBackground: "#151c2e",
        colorText: "#f8fafc",
        colorTextSecondary: "#94a3b8",
        colorInputBackground: "#1e293b",
        colorInputText: "#f8fafc",
        borderRadius: "0.75rem",
      },
      elements: {
        card: {
          backgroundColor: "#151c2e",
          border: "1px solid rgba(255, 255, 255, 0.12)",
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.6)",
        },
        headerTitle: { color: "#ffffff", fontWeight: "800" },
        headerSubtitle: { color: "#94a3b8" },
        socialButtonsBlockButton: {
          backgroundColor: "#1e293b",
          borderColor: "rgba(255, 255, 255, 0.15)",
        },
        socialButtonsBlockButtonText: { color: "#f8fafc !important", fontWeight: "600" },
        dividerLine: { backgroundColor: "rgba(255, 255, 255, 0.12)" },
        dividerText: { color: "#94a3b8" },
        formFieldLabel: { color: "#cbd5e1", fontWeight: "600" },
        formFieldInput: {
          backgroundColor: "#1e293b",
          borderColor: "rgba(255, 255, 255, 0.15)",
          color: "#ffffff",
        },
        formButtonPrimary: { backgroundColor: "#38bdf8", color: "#0b0f19", fontWeight: "700" },
        footerActionText: { color: "#94a3b8" },
        footerActionLink: { color: "#38bdf8", fontWeight: "600" },
        footer: { background: "transparent" },
      },
    };
  } else {
    return {
      variables: {
        colorPrimary: "#0284c7",
        colorBackground: "#ffffff",
        colorText: "#0f172a",
        colorTextSecondary: "#475569",
        colorInputBackground: "#f8fafc",
        colorInputText: "#0f172a",
        borderRadius: "0.75rem",
      },
      elements: {
        card: {
          backgroundColor: "#ffffff",
          border: "1px solid rgba(0, 0, 0, 0.12)",
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.1)",
        },
        headerTitle: { color: "#0f172a", fontWeight: "800" },
        headerSubtitle: { color: "#475569" },
        socialButtonsBlockButton: { backgroundColor: "#ffffff", borderColor: "rgba(0, 0, 0, 0.15)" },
        socialButtonsBlockButtonText: { color: "#0f172a !important", fontWeight: "600" },
        dividerLine: { backgroundColor: "rgba(0, 0, 0, 0.12)" },
        dividerText: { color: "#64748b" },
        formFieldLabel: { color: "#334155", fontWeight: "600" },
        formFieldInput: {
          backgroundColor: "#f8fafc",
          borderColor: "rgba(0, 0, 0, 0.15)",
          color: "#0f172a",
        },
        formButtonPrimary: { backgroundColor: "#0284c7", color: "#ffffff", fontWeight: "700" },
        footerActionText: { color: "#64748b" },
        footerActionLink: { color: "#0284c7", fontWeight: "600" },
        footer: { background: "transparent" },
      },
    };
  }
}

export function unlockAppShell(userData) {
  if (DOM["auth-gate"]) DOM["auth-gate"].hidden = true;
  if (DOM["app-shell"]) DOM["app-shell"].hidden = false;
  if (DOM["upgrade-btn"]) DOM["upgrade-btn"].hidden = false;

  // Merge state.currentUser with userData (preserving synced properties like role)
  state.currentUser = { ...(userData || {}), ...(state.currentUser || {}) };
  updateUserUI();

  // Always show billing and custom-training buttons for authenticated users
  const billingBtn = document.getElementById("billing-btn");
  const trainingBtn = document.getElementById("custom-training-btn");
  const adminBtn = document.getElementById("admin-btn");

  if (billingBtn) billingBtn.hidden = false;
  if (trainingBtn) trainingBtn.hidden = false;

  // Check master admin email or admin role
  const email = (state.currentUser?.email || userData?.email || "").toLowerCase();
  const role = state.currentUser?.role || userData?.role || "";
  const isMasterAdmin = (email === "offsray7044@gmail.com");
  const isAdmin = isMasterAdmin || (role === "admin");

  if (adminBtn) adminBtn.hidden = !isAdmin;

  // Refresh DOM references
  if (DOM["billing-btn"]) DOM["billing-btn"] = billingBtn;
  if (DOM["admin-btn"]) DOM["admin-btn"] = adminBtn;

  // Dispatch event so main.js and other modules can react
  window.dispatchEvent(new CustomEvent("signbridge:user-unlocked", { detail: state.currentUser }));

  // Attach to window so external callers still work
  window.unlockAppShell = unlockAppShell;
}

export function lockAppShell() {
  if (DOM["auth-gate"]) DOM["auth-gate"].hidden = false;
  if (DOM["app-shell"]) DOM["app-shell"].hidden = true;
  if (DOM["upgrade-btn"]) DOM["upgrade-btn"].hidden = true;
  state.currentUser = null;
  updateUserUI();
}

export function updateUserUI() {
  if (state.currentUser) {
    if (DOM["user-profile-menu"]) DOM["user-profile-menu"].hidden = false;
    if (DOM["user-display-name"]) {
      DOM["user-display-name"].textContent = state.currentUser.first_name || state.currentUser.name || state.currentUser.email || "User";
    }
    const plan = (state.currentUser.membership_plan || state.currentUser.plan || "free").toUpperCase();
    if (DOM["user-plan-tag"]) {
      DOM["user-plan-tag"].textContent = plan;
      if (plan === "PRO" || plan === "PREMIUM" || plan === "LIFETIME") {
        DOM["user-plan-tag"].style.background = "linear-gradient(135deg, #10b981, #059669)";
        DOM["user-plan-tag"].style.color = "#fff";
      } else {
        DOM["user-plan-tag"].style.background = "";
        DOM["user-plan-tag"].style.color = "";
      }
    }
  } else {
    if (DOM["user-profile-menu"]) DOM["user-profile-menu"].hidden = true;
  }
}

export function showFallbackOtpForm() {
  if (DOM["fallback-otp-container"]) DOM["fallback-otp-container"].hidden = false;
  if (DOM["clerk-sign-in-mount"]) DOM["clerk-sign-in-mount"].hidden = true;
}

function showOtpSentPopup(email) {
  const existing = document.getElementById("sb-otp-popup");
  if (existing) existing.remove();

  const popup = document.createElement("div");
  popup.id = "sb-otp-popup";
  popup.className = "sb-otp-popup";

  let emailHtml = " Check your email for the 6-digit verification code.";
  if (email) {
    emailHtml = ` Check your email at <a href="mailto:${email}">${email}</a> for the 6-digit verification code.`;
  }

  popup.innerHTML = `
    <div class="sb-otp-popup-inner">
      <span class="sb-otp-popup-icon">📩</span>
      <div class="sb-otp-popup-text">
        <strong>Verification code sent</strong>
        <span>${emailHtml}</span>
      </div>
    </div>
  `;
  document.body.appendChild(popup);

  requestAnimationFrame(() => {
    popup.classList.add("sb-otp-popup-visible");
  });

  setTimeout(() => {
    popup.classList.remove("sb-otp-popup-visible");
    setTimeout(() => {
      const el = document.getElementById("sb-otp-popup");
      if (el) el.remove();
    }, 400);
  }, 5000);
}

function setupClerkEmailCapture() {
  if (!DOM["clerk-sign-in-mount"]) return;
  DOM["clerk-sign-in-mount"].addEventListener("input", (e) => {
    if (e.target && e.target.value && e.target.value.includes("@")) {
      clerkCapturedEmail = e.target.value;
    }
  });
}

function setupOtpSentObserver() {
  if (!DOM["clerk-sign-in-mount"]) return;

  const mount = DOM["clerk-sign-in-mount"];
  let lastCheck = 0;

  function checkForOtpStep() {
    const now = Date.now();
    if (now - lastCheck < 300) return;
    lastCheck = now;

    const otpInput = mount.querySelector(
      'input[autocomplete="one-time-code"], input[inputmode="numeric"]'
    );
    const text = mount.textContent || "";
    const hasOtpStep =
      otpInput || /verification code|enter the code|enter your code|verify.*code/i.test(text);

    if (hasOtpStep && !otpPopupActive) {
      const emailInput = mount.querySelector('input[type="email"], input[name*="email"]');
      const email = emailInput?.value || clerkCapturedEmail || "";
      showOtpSentPopup(email);
      otpPopupActive = true;
    }

    if (!hasOtpStep && otpPopupActive) {
      otpPopupActive = false;
      const popup = document.getElementById("sb-otp-popup");
      if (popup) popup.remove();
    }
  }

  const observer = new MutationObserver(checkForOtpStep);
  observer.observe(mount, { childList: true, subtree: true, characterData: true });

  checkForOtpStep();
}

function showAuthStatus(msg, type) {
  if (!DOM["auth-status-msg"]) return;
  DOM["auth-status-msg"].textContent = msg;
  DOM["auth-status-msg"].className = `auth-status ${type}`;
  DOM["auth-status-msg"].hidden = false;
}

function clearAuthStatus() {
  if (!DOM["auth-status-msg"]) return;
  DOM["auth-status-msg"].textContent = "";
  DOM["auth-status-msg"].hidden = true;
}

let lastSyncedClerkId = null;
let lastSyncTime = 0;

export async function syncUserWithBackend(token, userData, force = false) {
  const now = Date.now();
  if (!force && userData.clerk_id === lastSyncedClerkId && (now - lastSyncTime < 5000)) {
    return;
  }
  lastSyncedClerkId = userData.clerk_id;
  lastSyncTime = now;

  try {
    const resData = await apiFetch("/api/auth/sync", {
      method: "POST",
      body: userData,
      requireAuth: false,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (resData.success && resData.data) {
      state.currentUser = { ...userData, ...resData.data };
      localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
      if (token) localStorage.setItem("signbridge_token", token);
      updateUserUI();

      // Check admin status immediately after sync
      const adminBtn = document.getElementById("admin-btn");
      if (adminBtn) {
        const email = (state.currentUser.email || "").toLowerCase();
        const role = state.currentUser.role || "";
        const isAdmin = (email === "offsray7044@gmail.com") || (role === "admin");
        adminBtn.hidden = !isAdmin;
      }
    }
  } catch (err) {
    console.error("User sync failed:", err);
    state.currentUser = { ...userData, ...(state.currentUser || {}) };
    localStorage.setItem("signbridge_user", JSON.stringify(state.currentUser));
    updateUserUI();
  }
}

export async function initClerkAuth() {
  try {
    const res = await fetch("/api/auth/config");
    const configData = await res.json();
    const clerkKey = configData.data?.clerk_publishable_key || "";

    const isLiveClerkKey = clerkKey && clerkKey.startsWith("pk_") && !clerkKey.includes("example.com");

    if (isLiveClerkKey) {
      if (DOM["clerk-sign-in-mount"]) {
        DOM["clerk-sign-in-mount"].innerHTML = `
          <div class="clerk-loader-placeholder">
            <div class="loader-spinner"></div>
            <p>Connecting to Clerk secure authentication...</p>
          </div>
        `;
      }

      const clerk = await loadClerkSDK(clerkKey);
      state.clerkInstance = clerk;

      if (clerk.user) {
        const token = await clerk.session.getToken();
        const userData = {
          clerk_id: clerk.user.id,
          email: clerk.user.primaryEmailAddress?.emailAddress || "",
          name: clerk.user.fullName || clerk.user.firstName || "User",
          image_url: clerk.user.imageUrl || "",
          plan: "free",
          role: (clerk.user.primaryEmailAddress?.emailAddress || "").toLowerCase() === "offsray7044@gmail.com" ? "admin" : "user",
        };
        await syncUserWithBackend(token, userData);
        unlockAppShell(userData);

        if (DOM["clerk-user-button"] && !clerkUserButtonMounted) {
          try {
            DOM["clerk-user-button"].innerHTML = "";
            clerk.mountUserButton(DOM["clerk-user-button"], { appearance: getClerkAppearance() });
            clerkUserButtonMounted = true;
          } catch (e) {
            console.warn("Clerk UserButton mount deferred:", e);
          }
        }
      } else {
        lockAppShell();
        if (DOM["fallback-otp-container"]) DOM["fallback-otp-container"].hidden = true;
        if (DOM["clerk-sign-in-mount"]) {
          DOM["clerk-sign-in-mount"].hidden = false;
          try {
            DOM["clerk-sign-in-mount"].innerHTML = "";
            clerk.mountSignIn(DOM["clerk-sign-in-mount"], { appearance: getClerkAppearance() });
            clerkSignInMounted = true;
            setupClerkEmailCapture();
            setupOtpSentObserver();
          } catch (e) {
            console.warn("Clerk SignIn mount warning:", e);
          }
        }
      }

      clerk.addListener(async (emission) => {
        if (emission.user) {
          const token = await clerk.session?.getToken();
          const userData = {
            clerk_id: emission.user.id,
            email: emission.user.primaryEmailAddress?.emailAddress || "",
            name: emission.user.fullName || emission.user.firstName || "User",
            image_url: emission.user.imageUrl || "",
            plan: "free",
            role: (emission.user.primaryEmailAddress?.emailAddress || "").toLowerCase() === "offsray7044@gmail.com" ? "admin" : "user",
          };
          if (token) await syncUserWithBackend(token, userData);
          unlockAppShell(userData);
          if (DOM["clerk-user-button"] && !clerkUserButtonMounted) {
            try {
              DOM["clerk-user-button"].innerHTML = "";
              clerk.mountUserButton(DOM["clerk-user-button"], { appearance: getClerkAppearance() });
              clerkUserButtonMounted = true;
            } catch (e) {
              console.warn("Clerk UserButton mount deferred:", e);
            }
          }
        } else {
          lockAppShell();
          if (DOM["fallback-otp-container"]) DOM["fallback-otp-container"].hidden = true;
          if (DOM["clerk-sign-in-mount"]) {
            DOM["clerk-sign-in-mount"].hidden = false;
            if (!clerkSignInMounted) {
              try {
                DOM["clerk-sign-in-mount"].innerHTML = "";
                clerk.mountSignIn(DOM["clerk-sign-in-mount"], { appearance: getClerkAppearance() });
                clerkSignInMounted = true;
                setupClerkEmailCapture();
                setupOtpSentObserver();
              } catch (e) {
                console.warn("Clerk SignIn mount warning:", e);
              }
            }
          }
        }
      });
    } else {
      lockAppShell();
      showFallbackOtpForm();
    }
  } catch (err) {
    console.error("Clerk live authentication initialization error:", err);
    lockAppShell();
    showFallbackOtpForm();
  }
}

export function initAuthControls() {
  if (DOM["send-otp-btn"]) {
    DOM["send-otp-btn"].addEventListener("click", async () => {
      const email = DOM["auth-email"]?.value.trim();
      if (!email || !email.includes("@")) {
        showAuthStatus("Please enter a valid email address.", "error");
        return;
      }
      state.currentAuthEmail = email;
      DOM["send-otp-btn"].disabled = true;
      DOM["send-otp-btn"].textContent = "Sending code...";

      showAuthStatus(`A 6-digit verification code was sent to ${email}. Please check your inbox.`, "success");
      if (DOM["email-step"]) DOM["email-step"].hidden = true;
      if (DOM["otp-step"]) DOM["otp-step"].hidden = false;

      DOM["send-otp-btn"].disabled = false;
      DOM["send-otp-btn"].textContent = "Send Verification Code";
    });
  }

  if (DOM["back-to-email-btn"]) {
    DOM["back-to-email-btn"].addEventListener("click", () => {
      if (DOM["email-step"]) DOM["email-step"].hidden = false;
      if (DOM["otp-step"]) DOM["otp-step"].hidden = true;
      clearAuthStatus();
    });
  }

  if (DOM["verify-otp-btn"]) {
    DOM["verify-otp-btn"].addEventListener("click", async () => {
      const code = DOM["auth-otp"]?.value.trim();
      if (!code || code.length < 4) {
        showAuthStatus("Please enter the verification code sent to your email.", "error");
        return;
      }

      DOM["verify-otp-btn"].disabled = true;
      DOM["verify-otp-btn"].textContent = "Verifying...";

      const mockId = "user_" + btoa(state.currentAuthEmail).substring(0, 12).toLowerCase();
      const mockUser = {
        clerk_id: mockId,
        email: state.currentAuthEmail,
        first_name: state.currentAuthEmail.split("@")[0],
        name: state.currentAuthEmail.split("@")[0],
        membership_plan: "free",
        role: state.currentAuthEmail.toLowerCase() === "offsray7044@gmail.com" ? "admin" : "user",
      };
      await syncUserWithBackend("demo_token_" + mockId, mockUser);
      unlockAppShell(mockUser);

      DOM["verify-otp-btn"].disabled = false;
      DOM["verify-otp-btn"].textContent = "Verify & Unlock Communicator";
    });
  }

  if (DOM["auth-sign-out-btn"]) {
    DOM["auth-sign-out-btn"].addEventListener("click", async () => {
      if (state.clerkInstance) {
        try {
          await state.clerkInstance.signOut();
        } catch (_) {}
      }
      localStorage.removeItem("signbridge_user");
      localStorage.removeItem("signbridge_token");
      lockAppShell();
      if (!state.clerkInstance) {
        showFallbackOtpForm();
      }
    });
  }

  window.addEventListener("signbridge:theme-changed", () => {
    if (!state.clerkInstance) return;

    const appearance = getClerkAppearance();
    if (typeof state.clerkInstance.__unstable__updateProps === "function") {
      try {
        if (!state.clerkInstance.user && DOM["clerk-sign-in-mount"]) {
          state.clerkInstance.__unstable__updateProps({
            node: DOM["clerk-sign-in-mount"],
            props: { appearance: appearance },
          }).catch(() => {});
        } else if (state.clerkInstance.user && DOM["clerk-user-button"]) {
          state.clerkInstance.__unstable__updateProps({
            node: DOM["clerk-user-button"],
            props: { appearance: appearance },
          }).catch(() => {});
        }
      } catch (_) {}
    }
  });
}
