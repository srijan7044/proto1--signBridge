// api.js — Centralized authenticated API request client helper

import { state } from "./state.js";

/**
 * Retrieves the current valid authentication token.
 * Prefers active Clerk session token if available, falling back to localStorage.
 */
export async function getAuthToken() {
  if (state.clerkInstance && state.clerkInstance.session) {
    try {
      const token = await state.clerkInstance.session.getToken();
      if (token) {
        localStorage.setItem("signbridge_token", token);
        return token;
      }
    } catch (err) {
      console.warn("Failed to get fresh Clerk session token:", err);
    }
  }
  return localStorage.getItem("signbridge_token") || null;
}

/**
 * Perform an API fetch request with automatic authorization header and error handling.
 * @param {string} endpoint - The relative endpoint path (e.g. "/api/usage/summary")
 * @param {Object} options - Standard fetch options (method, headers, body, requireAuth)
 */
export async function apiFetch(endpoint, options = {}) {
  const {
    method = "GET",
    body = null,
    headers = {},
    requireAuth = true,
    ...restOptions
  } = options;

  const requestHeaders = { ...headers };

  if (body && typeof body === "object" && !(body instanceof FormData)) {
    requestHeaders["Content-Type"] = "application/json";
  }

  if (requireAuth) {
    const token = await getAuthToken();
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    } else if (requireAuth === true && method !== "GET") {
      console.warn(`Unauthenticated request blocked for protected endpoint: ${endpoint}`);
      return { success: false, error: "Unauthorized: Missing authentication token", status_code: 401 };
    }
  }

  const fetchConfig = {
    method,
    headers: requestHeaders,
    ...restOptions,
  };

  if (body) {
    fetchConfig.body = typeof body === "string" || body instanceof FormData ? body : JSON.stringify(body);
  }

  try {
    const response = await fetch(endpoint, fetchConfig);
    const data = await response.json().catch(() => ({
      success: false,
      error: `HTTP Error ${response.status}: ${response.statusText}`,
      status_code: response.status,
    }));

    if (!response.ok) {
      return {
        success: false,
        status_code: response.status,
        error: data.error || `HTTP ${response.status}`,
        data: data.data || null,
      };
    }

    return data;
  } catch (err) {
    console.error(`API request failed [${method} ${endpoint}]:`, err.message);
    return {
      success: false,
      error: err.message || "Network request failed",
      status_code: 0,
    };
  }
}
