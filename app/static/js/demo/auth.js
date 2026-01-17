// Authentication helpers for demo pages - cookies only (no localStorage)

const DemoAuth = {
  getCookie(name) {
    if (!document.cookie) return null;
    const cookies = document.cookie.split(';').reduce((acc, cookie) => {
      const [key, value] = cookie.trim().split('=');
      if (key && value) {
        acc[key] = decodeURIComponent(value);
      }
      return acc;
    }, {});
    return cookies[name] || null;
  },
  
  getAccessToken() {
    const accessTokenKey = (window.APP_CONFIG && window.APP_CONFIG.accessTokenCookie) || 'access_token';
    return this.getCookie(accessTokenKey) || this.getCookie('access_token');
  },
  
  getRefreshToken() {
    const refreshTokenKey = (window.APP_CONFIG && window.APP_CONFIG.refreshTokenCookie) || 'refresh_token';
    return this.getCookie(refreshTokenKey) || this.getCookie('refresh_token');
  },
  
  isAuthenticated() {
    return !!this.getAccessToken();
  },
  
  async login(username, password, rememberMe = false) {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, remember_me: rememberMe }),
    });
    
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Login failed (${res.status})`);
    }
    
    const data = await res.json();
    
    // Server sets cookies automatically via CookieManager
    // Cookies will be available on subsequent requests
    // No need to verify immediately - browser handles cookie persistence
    
    return data;
  },
  
  async refresh() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) throw new Error('No refresh token');
    
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    
    if (!res.ok) throw new Error('Token refresh failed');
    
    // Server sets cookies automatically via CookieManager
    // Cookies will be available on subsequent requests
    // No need to verify immediately - browser handles cookie persistence
    
    return await res.json();
  },
  
  async fetch(url, options = {}) {
    const opts = { ...options, headers: { ...(options.headers || {}) } };
    
    // Cookies are automatically sent by browser
    // Optionally add Authorization header as fallback for API clients
    const token = this.getAccessToken();
    if (token) {
      opts.headers['Authorization'] = `Bearer ${token}`;
    }
    
    let res = await fetch(url, opts);
    
    if (res.status === 401) {
      try {
        await this.refresh();
        // Retry request - cookies are automatically sent
        res = await fetch(url, opts);
      } catch (_) {
        window.location.href = '/demo/auth/login';
        return res;
      }
    }
    
    return res;
  },
  
  logout() {
    // Server handles cookie clearing via /demo/auth/logout route
    window.location.href = '/demo/auth/logout';
  },
};

// Export to window
window.DemoAuth = DemoAuth;
