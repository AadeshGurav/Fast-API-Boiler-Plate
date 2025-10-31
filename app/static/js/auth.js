// Lightweight client-side auth helper for demo pages
// Stores tokens in localStorage and provides authFetch with automatic refresh

const AUTH_STORAGE_KEY = "demo_auth_tokens";

function getStoredTokens() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function setStoredTokens(tokens) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
}

function clearStoredTokens() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

function getAccessToken() {
  const tokens = getStoredTokens();
  return tokens?.access_token || null;
}

function getRefreshToken() {
  const tokens = getStoredTokens();
  return tokens?.refresh_token || null;
}

async function demoLogin(username, password) {
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Login failed (${res.status})`);
  }
  const data = await res.json();
  if (!data?.tokens?.access_token || !data?.tokens?.refresh_token) {
    throw new Error("Invalid login response");
  }
  setStoredTokens({
    access_token: data.tokens.access_token,
    refresh_token: data.tokens.refresh_token,
  });
  return data;
}

async function demoRefresh() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error("No refresh token");
  const res = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) throw new Error("Token refresh failed");
  const data = await res.json();
  if (!data?.access_token || !data?.refresh_token) throw new Error("Invalid refresh response");
  setStoredTokens({ access_token: data.access_token, refresh_token: data.refresh_token });
  return data;
}

async function authFetch(url, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  const token = getAccessToken();
  if (token) {
    opts.headers["Authorization"] = `Bearer ${token}`;
  }
  let res = await fetch(url, opts);
  if (res.status === 401) {
    try {
      await demoRefresh();
      const refreshed = getAccessToken();
      if (refreshed) {
        opts.headers["Authorization"] = `Bearer ${refreshed}`;
        res = await fetch(url, opts);
      }
    } catch (_) {
      // refresh failed, clear tokens
      clearStoredTokens();
    }
  }
  return res;
}

function isAuthenticated() {
  return !!getAccessToken();
}

function demoLogout() {
  clearStoredTokens();
}

window.DemoAuth = {
  login: demoLogin,
  refresh: demoRefresh,
  fetch: authFetch,
  logout: demoLogout,
  isAuthenticated,
  getAccessToken,
};


