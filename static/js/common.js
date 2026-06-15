const API_BASE = window.location.origin;
const TOKEN_KEY = "lca_token";   // JWT 存 localStorage
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
  const { signal, ...fetchOptions } = options;
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      signal,
      headers: { ...authHeaders(), ...fetchOptions.headers },
    });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("分析已取消");
    }
    throw err;
  }
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

function setFormFieldsDisabled(form, disabled) {
  form.querySelectorAll("input, select, textarea, button").forEach((el) => {
    if (el.id === "cancel-btn") {
      el.disabled = false;
      return;
    }
    el.disabled = disabled;
  });
}

async function apiStream(path, { body, signal, onEvent }) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("分析已取消");
    }
    throw err;
  }

  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail || text;
    } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : `请求失败 ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      if (!chunk.trim()) continue;
      let eventType = "message";
      let dataLine = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) eventType = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (!dataLine) continue;
      const data = JSON.parse(dataLine);
      if (eventType === "progress" && onEvent) {
        onEvent(data);
      } else if (eventType === "result") {
        result = data;
      } else if (eventType === "error") {
        if (data.code === 499) throw new Error("分析已取消");
        throw new Error(data.message || "分析失败");
      }
    }
  }

  if (!result) {
    throw new Error("未收到分析结果，请重试");
  }
  return result;
}

function stepLabel(event) {
  if (event.agent) return event.agent;
  const map = {
    rag: "知识库检索",
    parallel_phase1: "阶段1：并行专家",
    parallel_phase2: "阶段2：专业/院校专家",
    debate_supervisor: "阶段3：辩论协调",
    coordinator: "阶段4：总协调员",
  };
  if (event.message && event.step === "rag") return `知识库检索（${event.message}）`;
  return map[event.step] || event.step || event.message || "处理中";
}

function updateProgress(listEl, event) {
  if (!listEl) return;
  const panel = listEl.closest(".progress-panel");
  if (panel) panel.classList.remove("hidden");
  const key = `${event.step || "sys"}:${event.agent || event.message || ""}`;
  let li = listEl.querySelector(`[data-key="${CSS.escape(key)}"]`);
  if (!li) {
    li = document.createElement("li");
    li.dataset.key = key;
    listEl.appendChild(li);
  }
  const label = stepLabel(event);
  const suffix = event.elapsed_ms ? ` · ${event.elapsed_ms}ms` : "";
  if (event.status === "started") {
    li.className = "progress-running";
    li.textContent = `⏳ ${label}…`;
  } else if (event.status === "done") {
    li.className = "progress-done";
    li.textContent = `✓ ${label}${suffix}`;
  } else {
    li.className = "progress-info";
    li.textContent = `• ${label}${suffix}`;
  }
}

function clearProgress(listEl) {
  if (!listEl) return;
  listEl.innerHTML = "";
  const panel = listEl.closest(".progress-panel");
  if (panel) panel.classList.add("hidden");
}

function bindAdvisoryForm({ formId, endpoint, streamEndpoint, buildPayload, runningMessage, getImportContext }) {
  /** 问卷提交通用逻辑：调 API → 展示报告 → 支持 AbortController 停止分析 */
  const form = document.getElementById(formId);
  const submitBtn = document.getElementById("submit-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const status = document.getElementById("status");
  const progress = document.getElementById("progress-steps");
  const result = document.getElementById("result");
  let abortController = null;
  const streamPath = streamEndpoint || `${endpoint}/stream`;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    abortController = new AbortController();
    submitBtn.disabled = true;
    cancelBtn.classList.remove("hidden");
    setFormFieldsDisabled(form, true);
    showStatus(status, runningMessage, "info");
    clearProgress(progress);
    result.classList.add("hidden");

    try {
      const payload = {
        profile: buildPayload(new FormData(form)),
        imported_report_context: getImportContext ? getImportContext() : null,
      };
      const data = await apiStream(streamPath, {
        body: payload,
        signal: abortController.signal,
        onEvent: (ev) => updateProgress(progress, ev),
      });
      showStatus(status, "分析完成！报告已保存。", "success");
      result.classList.remove("hidden");
      renderReport(result, data);
    } catch (err) {
      const cancelled = err.message === "分析已取消";
      showStatus(status, err.message, cancelled ? "info" : "error");
    } finally {
      abortController = null;
      submitBtn.disabled = false;
      cancelBtn.classList.add("hidden");
      setFormFieldsDisabled(form, false);
      submitBtn.disabled = false;
    }
  });

  cancelBtn.addEventListener("click", () => {
    if (abortController) {
      showStatus(status, "正在取消分析…", "info");
      abortController.abort();
    }
  });
}

async function parseReportFile(file, advisoryType) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("advisory_type", advisoryType);
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/report-import/parse`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : `解析失败 ${res.status}`);
  }
  return data;
}

function bindReportImport({ fileInputId, buttonId, previewId, advisoryType, onParsed, hideSelectors = [] }) {
  const input = document.getElementById(fileInputId);
  const btn = document.getElementById(buttonId);
  const preview = document.getElementById(previewId);
  if (!input || !btn) return;

  btn.addEventListener("click", async () => {
    const file = input.files && input.files[0];
    if (!file) {
      alert("请先选择 PDF 或图片文件");
      return;
    }
    btn.disabled = true;
    btn.textContent = "解析中…";
    try {
      const data = await parseReportFile(file, advisoryType);
      if (preview) {
        preview.classList.remove("hidden");
        preview.innerHTML = `
          <p><strong>已解析：</strong>${escapeHtml(data.filename)}（${data.chunk_count} 个语义分块）</p>
          <pre class="import-preview">${escapeHtml(data.structured_summary || "")}</pre>
          ${data.missing_fields && data.missing_fields.length
            ? `<p class="hint-warn">请补充：${data.missing_fields.join("、")}</p>` : ""}
        `;
      }
      hideSelectors.forEach((sel) => {
        const el = document.querySelector(sel);
        if (el) el.classList.add("hidden");
      });
      if (onParsed) onParsed(data);
    } catch (err) {
      alert(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "解析报告";
    }
  });
}

function setInputValue(form, name, value) {
  const el = form.querySelector(`[name="${name}"]`);
  if (!el || value === null || value === undefined) return;
  if (Array.isArray(value)) {
    el.value = value.join(", ");
  } else {
    el.value = value;
  }
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
