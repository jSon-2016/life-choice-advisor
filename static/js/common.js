const API_BASE = window.location.origin;
const TOKEN_KEY = "lca_token";
const USER_KEY = "lca_user";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setAuth(token, userId, role) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify({ userId, role }));
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

function authHeaders() {
  const token = getToken();
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...options.headers },
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : `请求失败 ${res.status}`);
  }
  return data;
}

async function login(userId, password) {
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ userId, password }),
  });
  setAuth(data.accessToken, data.userId, data.role);
  return data;
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch (_) {}
  clearAuth();
  window.location.href = "/";
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "/";
    return false;
  }
  return true;
}

function showStatus(el, message, type = "info") {
  el.className = `status-bar ${type}`;
  el.textContent = message;
  el.classList.remove("hidden");
}

function splitList(value) {
  if (!value || !value.trim()) return [];
  return value.split(/[,，、\n]/).map((s) => s.trim()).filter(Boolean);
}

function parseScores(text) {
  if (!text || !text.trim()) return null;
  const result = {};
  text.split(/[,，\n]/).forEach((pair) => {
    const [k, v] = pair.split(/[:：]/).map((s) => s.trim());
    if (k && v) result[k] = parseInt(v, 10);
  });
  return Object.keys(result).length ? result : null;
}

function renderReport(container, data) {
  let html = `<div class="result-section">`;
  html += `<p><strong>报告 ID：</strong>${data.reportId || data.report_id || "-"}</p>`;
  html += `<h3>摘要</h3><p>${data.summary || ""}</p>`;

  const lists = [
    ["冲", data.rushSchools || data.rush_schools],
    ["稳", data.stableSchools || data.stable_schools],
    ["保", data.safeSchools || data.safe_schools],
    ["推荐行业", data.recommendedIndustries || data.recommended_industries],
    ["推荐岗位", data.recommendedRoles || data.recommended_roles],
  ];
  lists.forEach(([title, list]) => {
    if (list && list.length) {
      html += `<h3>${title}</h3><ul>${list.map((i) => `<li>${i}</li>`).join("")}</ul>`;
    }
  });

  const report = data.fullReport || data.full_report;
  if (report) {
    html += `<h3>完整报告</h3><pre>${escapeHtml(report)}</pre>`;
  }
  html += `</div>`;
  container.innerHTML = html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function updateNavAuth() {
  const userEl = document.getElementById("user-info");
  const loginEl = document.getElementById("nav-login");
  const logoutEl = document.getElementById("nav-logout");
  const user = getUser();
  if (user && getToken()) {
    if (userEl) userEl.textContent = `${user.userId} (${user.role})`;
    if (loginEl) loginEl.classList.add("hidden");
    if (logoutEl) logoutEl.classList.remove("hidden");
  } else {
    if (userEl) userEl.textContent = "";
    if (loginEl) loginEl.classList.remove("hidden");
    if (logoutEl) logoutEl.classList.add("hidden");
  }
}

document.addEventListener("DOMContentLoaded", updateNavAuth);
