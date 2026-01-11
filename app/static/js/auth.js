// Lightweight client-side auth helper for demo pages - cookies only (no localStorage)

function getCookie(name) {
  const cookies = document.cookie.split(';').reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split('=');
    acc[key] = value;
    return acc;
  }, {});
  return cookies[name] || null;
}

function getAccessToken() {
  const accessTokenKey = (window.APP_CONFIG && window.APP_CONFIG.accessTokenCookie) || 'access_token';
  return getCookie(accessTokenKey) || getCookie('access_token');
}

function getRefreshToken() {
  const refreshTokenKey = (window.APP_CONFIG && window.APP_CONFIG.refreshTokenCookie) || 'refresh_token';
  return getCookie(refreshTokenKey) || getCookie('refresh_token');
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
  
  // Server sets cookies automatically via CookieManager
  // Cookies will be available on subsequent requests
  // No need to verify immediately - browser handles cookie persistence
  
  return await res.json();
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
  
  // Server sets cookies automatically via CookieManager
  // Cookies will be available on subsequent requests
  // No need to verify immediately - browser handles cookie persistence
  
  return await res.json();
}

async function authFetch(url, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  
  // Cookies are automatically sent by browser
  // Optionally add Authorization header as fallback for API clients
  const token = getAccessToken();
  if (token) {
    opts.headers["Authorization"] = `Bearer ${token}`;
  }
  
  let res = await fetch(url, opts);
  if (res.status === 401) {
    try {
      await demoRefresh();
      // Retry request - cookies are automatically sent
      res = await fetch(url, opts);
    } catch (_) {
      // refresh failed
      return res;
    }
  }
  
  return res;
}

function isAuthenticated() {
  return !!getAccessToken();
}

function demoLogout() {
  // Server handles cookie clearing via /demo/auth/logout route
  window.location.href = '/demo/auth/logout';
}

window.DemoAuth = {
  login: demoLogin,
  refresh: demoRefresh,
  fetch: authFetch,
  logout: demoLogout,
  isAuthenticated,
  getAccessToken,
};
