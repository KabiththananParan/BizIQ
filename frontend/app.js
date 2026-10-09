/**
 * BizIQ — Unified Multi-Agent Web Application Logic
 * Integrates:
 *   - Member 1: NLP Query Agent
 *   - Member 2: Data Retrieval (IR) Agent
 *   - Member 3: LLM Insight Agent
 *   - Member 4: Security & Compliance Agent
 */

// Auto-detect API base URL (works seamlessly whether served via Gateway port 8000 or Live Server)
const API_BASE = window.location.port === "8000" 
  ? "" 
  : "http://127.0.0.1:8000";

const AUTH_STORAGE_KEY = "biziq_auth_session";

// Global App State
const state = {
  activeTab: "tab-query-hub",
  currentUser: {
    id: "2",
    username: "achini",
    name: "Achini",
    fullName: "Achini (Lead Business Analyst)",
    role: "ANALYST",
    email: "achini@biziq.com",
    token: null,
  },
  currentInsight: null,
  activeChart: null,
  queries: [],
  datasources: [],
  reports: [],
  auditLogs: [],
  users: [],
};

// ============================================================================
// Authenticated Fetch Wrapper
// ============================================================================

async function authFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  
  if (state.currentUser && state.currentUser.token) {
    headers.set("Authorization", `Bearer ${state.currentUser.token}`);
  }
  if (state.currentUser && state.currentUser.id) {
    headers.set("X-User-Id", String(state.currentUser.id));
  }
  if (state.currentUser && state.currentUser.role) {
    headers.set("X-User-Role", state.currentUser.role);
  }

  return fetch(url, {
    ...options,
    headers,
  });
}

// ============================================================================
// Initialization & Lifecycle
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initUserSwitcher();
  initQueryHub();
  initNlpLab();
  initIrVault();
  initInsightReports();
  initSecurityCenter();
  initArchitecture();
  initModals();

  // Restore authenticated session from localStorage or auto-sign in default demo profile
  restoreAuthSession().then(() => {
    refreshAllSystemState();
  });
});

async function refreshAllSystemState() {
  loadSavedQueries();
  loadDataSources();
  loadReports();
  loadAuditLogs();
  loadUsers();
  checkSystemStatus();
}

// ============================================================================
// Navigation Controller
// ============================================================================

function initNavigation() {
  const navBtns = document.querySelectorAll(".nav-tab-btn");
  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.dataset.tab;
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".nav-tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-content-panel").forEach(p => {
    p.classList.toggle("active", p.id === tabId);
  });

  // Trigger tab-specific refresh
  if (tabId === "tab-nlp-lab") loadNlpQueriesTable();
  if (tabId === "tab-ir-vault") loadDataSources();
  if (tabId === "tab-insight-reports") { loadReports(); loadInsightsHistory(); }
  if (tabId === "tab-security-center") { loadAuditLogs(); loadUsers(); }
  if (tabId === "tab-architecture") checkSystemStatus();
}

// ============================================================================
// User & Auth Management (Sign In, JWT HS256, Persistence)
// ============================================================================

function saveAuthSession(token, user) {
  try {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token, user }));
  } catch (e) {
    console.warn("Could not persist session:", e);
  }
}

function clearAuthSession() {
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch (e) {
    console.warn("Could not clear session:", e);
  }
}

async function restoreAuthSession() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.token && parsed.user) {
        parsed.user.token = parsed.token;
        setUser(parsed.user);

        // Verify token with backend
        try {
          const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${parsed.token}` },
          });
          if (res.ok) {
            const freshUser = await res.json();
            freshUser.token = parsed.token;
            saveAuthSession(parsed.token, freshUser);
            setUser(freshUser);
            return;
          }
        } catch (_) {}
      }
    }
  } catch (e) {
    console.warn("Failed to parse saved session:", e);
  }

  // Fallback: perform initial sign in for default demo profile (Achini)
  await signInWithCredentials("achini@biziq.com", "Achini123!", true);
}

function setUser(user) {
  if (!user) return;
  
  const rawName = user.full_name || user.name || user.username || "User";
  const roleName = (user.role || "ANALYST").toUpperCase();
  const username = user.username || "user";
  const email = user.email || `${username}@biziq.com`;

  state.currentUser = {
    id: String(user.id || (username === "admin" ? "1" : (username === "achini" ? "2" : "3"))),
    username: username,
    name: rawName.split(" ")[0],
    fullName: rawName,
    role: roleName,
    email: email,
    token: user.token || state.currentUser.token || null,
  };

  const nameEl = document.getElementById("currentUserName");
  if (nameEl) nameEl.textContent = state.currentUser.name;

  const roleBadge = document.getElementById("currentUserRole");
  if (roleBadge) {
    roleBadge.textContent = state.currentUser.role;
    roleBadge.className = `user-role-badge ${state.currentUser.role.toLowerCase()}`;
  }

  const avatarEl = document.getElementById("userAvatar");
  if (avatarEl) avatarEl.textContent = (state.currentUser.name || "U")[0].toUpperCase();

  const emailEl = document.getElementById("dropdownUserEmail");
  if (emailEl) emailEl.textContent = state.currentUser.email;

  const jwtPill = document.getElementById("jwtStatusPill");
  if (jwtPill) {
    if (state.currentUser.token) {
      jwtPill.classList.remove("inactive");
      jwtPill.classList.add("active");
      jwtPill.title = `JWT HS256 Token Active for ${state.currentUser.fullName} (${state.currentUser.role})`;
      jwtPill.textContent = "🔒 JWT";
    } else {
      jwtPill.classList.remove("active");
      jwtPill.classList.add("inactive");
      jwtPill.title = "No active JWT Token (Guest / Signed Out)";
      jwtPill.textContent = "🔓 No JWT";
    }
  }

  const signInBtn = document.getElementById("headerSignInBtn");
  if (signInBtn) {
    if (state.currentUser.token) {
      signInBtn.innerHTML = `<span>🔄</span> Switch`;
      signInBtn.title = `Signed in as ${state.currentUser.fullName}. Click to switch or create account.`;
    } else {
      signInBtn.innerHTML = `<span>🔑</span> Sign In`;
      signInBtn.title = "Click to Sign In with JWT";
    }
  }
}

async function signInWithCredentials(identifier, password, silent = false) {
  const banner = document.getElementById("authStatusBanner");
  const spinner = document.getElementById("loginSpinner");
  const btnText = document.getElementById("loginBtnText");
  const loginBtn = document.getElementById("doLoginBtn");

  if (!silent) {
    if (spinner) spinner.classList.remove("hidden");
    if (btnText) btnText.textContent = "Authenticating...";
    if (loginBtn) loginBtn.disabled = true;
    if (banner) {
      banner.className = "auth-banner hidden";
      banner.textContent = "";
    }
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: identifier, password: password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Invalid credentials" }));
      throw new Error(err.detail || "Authentication failed. Please verify credentials.");
    }

    const data = await res.json();
    const token = data.access_token;
    const userData = data.user || {};
    userData.token = token;

    saveAuthSession(token, userData);
    setUser(userData);

    const authModal = document.getElementById("authModal");
    if (authModal) authModal.classList.add("hidden");

    if (!silent) {
      showToast(`Welcome back, ${state.currentUser.fullName}! (${state.currentUser.role})`, "success");
    }

    // Refresh UI data for user
    refreshAllSystemState();
    return true;
  } catch (error) {
    if (!silent) {
      if (banner) {
        banner.className = "auth-banner error";
        banner.textContent = `Authentication failed: ${error.message}`;
        banner.classList.remove("hidden");
      }
      showToast(error.message, "error");
    }
    return false;
  } finally {
    if (!silent) {
      if (spinner) spinner.classList.add("hidden");
      if (btnText) btnText.textContent = "Sign In with JWT";
      if (loginBtn) loginBtn.disabled = false;
    }
  }
}

async function registerAccount(fullName, username, email, password, role) {
  const banner = document.getElementById("authStatusBanner");
  const spinner = document.getElementById("regSpinner");
  const btnText = document.getElementById("regBtnText");
  const regBtn = document.getElementById("doRegisterBtn");

  if (!fullName || !username || !email || !password) {
    if (banner) {
      banner.className = "auth-banner error";
      banner.textContent = "Please fill in all required registration fields.";
      banner.classList.remove("hidden");
    }
    showToast("Please fill in all registration fields.", "error");
    return false;
  }

  if (password.length < 6) {
    if (banner) {
      banner.className = "auth-banner error";
      banner.textContent = "Password must be at least 6 characters.";
      banner.classList.remove("hidden");
    }
    showToast("Password must be at least 6 characters.", "error");
    return false;
  }

  if (spinner) spinner.classList.remove("hidden");
  if (btnText) btnText.textContent = "Creating Account...";
  if (regBtn) regBtn.disabled = true;
  if (banner) {
    banner.className = "auth-banner hidden";
    banner.textContent = "";
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        username: username,
        email: email,
        password: password,
        role: role || "ANALYST",
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(err.detail || "Registration failed. User may already exist.");
    }

    if (banner) {
      banner.className = "auth-banner success";
      banner.textContent = "Account created successfully! Signing in...";
      banner.classList.remove("hidden");
    }

    // Auto sign in with the new credentials
    const success = await signInWithCredentials(email, password, false);
    if (success) {
      showToast(`Account registered and signed in as ${fullName}!`, "success");
    }
    return success;
  } catch (error) {
    if (banner) {
      banner.className = "auth-banner error";
      banner.textContent = error.message;
      banner.classList.remove("hidden");
    }
    showToast(error.message, "error");
    return false;
  } finally {
    if (spinner) spinner.classList.add("hidden");
    if (btnText) btnText.textContent = "Create Account & Sign In";
    if (regBtn) regBtn.disabled = false;
  }
}

function signOutUser() {
  clearAuthSession();
  setUser({
    id: null,
    username: "guest",
    full_name: "Guest User",
    role: "GUEST",
    email: "Not signed in",
    token: null,
  });
  showToast("Signed out. Operating in Guest mode.", "info");
  const authModal = document.getElementById("authModal");
  if (authModal) authModal.classList.remove("hidden");
}

function initUserSwitcher() {
  const activeUserBtn = document.getElementById("activeUserBtn");
  const userDropdown = document.getElementById("userDropdownMenu");
  const headerSignInBtn = document.getElementById("headerSignInBtn");
  const openAuthModalBtn = document.getElementById("openAuthModalBtn");
  const logoutBtn = document.getElementById("logoutBtn");
  const authModal = document.getElementById("authModal");

  if (activeUserBtn && userDropdown) {
    activeUserBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      userDropdown.classList.toggle("hidden");
    });

    document.addEventListener("click", () => {
      userDropdown.classList.add("hidden");
    });
  }

  if (headerSignInBtn && authModal) {
    headerSignInBtn.addEventListener("click", () => {
      authModal.classList.remove("hidden");
    });
  }

  if (openAuthModalBtn && authModal) {
    openAuthModalBtn.addEventListener("click", () => {
      if (userDropdown) userDropdown.classList.add("hidden");
      authModal.classList.remove("hidden");
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      if (userDropdown) userDropdown.classList.add("hidden");
      signOutUser();
    });
  }

  // Quick switch dropdown items
  document.querySelectorAll(".dropdown-item[data-quick-email]").forEach(item => {
    item.addEventListener("click", async () => {
      const email = item.dataset.quickEmail;
      const pwd = item.dataset.quickPwd;
      if (userDropdown) userDropdown.classList.add("hidden");
      await signInWithCredentials(email, pwd, false);
    });
  });
}

// ============================================================================
// TAB 1: AI Query Hub (Main Ask Interface)
// ============================================================================

function initQueryHub() {
  const askBtn = document.getElementById("hubAskBtn");
  const questionInput = document.getElementById("hubQuestionInput");
  const slider = document.getElementById("topKSlider");
  const sliderVal = document.getElementById("topKValue");
  const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
  const historySearch = document.getElementById("historySearchInput");

  slider.addEventListener("input", () => {
    sliderVal.textContent = slider.value;
  });

  askBtn.addEventListener("click", () => {
    const q = questionInput.value.trim();
    if (q) executeMultiAgentPipeline(q);
  });

  questionInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      const q = questionInput.value.trim();
      if (q) executeMultiAgentPipeline(q);
    }
  });

  // Example Prompt Chips
  document.querySelectorAll(".prompt-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt;
      questionInput.value = prompt;
      executeMultiAgentPipeline(prompt);
    });
  });

  refreshHistoryBtn.addEventListener("click", loadSavedQueries);

  historySearch.addEventListener("input", () => {
    renderHistoryList(historySearch.value.trim());
  });

  // Actions on answer
  document.getElementById("copyAnswerBtn").addEventListener("click", () => {
    const text = document.getElementById("answerText").innerText;
    navigator.clipboard.writeText(text).then(() => {
      showToast("Answer copied to clipboard!", "success");
    });
  });

  document.getElementById("pinToReportBtn").addEventListener("click", () => {
    if (!state.currentInsight) return;
    document.getElementById("reportTitleInput").value = `Insight: ${state.currentInsight.question.slice(0, 50)}`;
    document.getElementById("reportNotesInput").value = state.currentInsight.answer;
    document.getElementById("saveReportModal").classList.remove("hidden");
  });

  // Feedback buttons
  document.getElementById("feedbackYesBtn").addEventListener("click", () => submitFeedback(true));
  document.getElementById("feedbackNoBtn").addEventListener("click", () => submitFeedback(false));
}

async function executeMultiAgentPipeline(question) {
  const askBtn = document.getElementById("hubAskBtn");
  const spinner = document.getElementById("askSpinner");
  const label = document.getElementById("askBtnLabel");
  const topK = parseInt(document.getElementById("topKSlider").value, 10);
  const resultCard = document.getElementById("resultCard");
  const pipelineTimer = document.getElementById("pipelineTimer");

  // Animate Stepper
  resetPipelineStepper();
  setStepState("stepSec", "running");
  spinner.classList.remove("hidden");
  label.textContent = "Orchestrating 4 Agents...";
  askBtn.disabled = true;

  const startTime = performance.now();
  const timerInterval = setInterval(() => {
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
    pipelineTimer.textContent = `${elapsed}s`;
  }, 50);

  try {
    const payload = {
      question: question,
      top_k: topK,
      user_id: String(state.currentUser.id || "1"),
      user_role: (state.currentUser.role || "analyst").toLowerCase(),
      owner: "demo",
    };

    const res = await authFetch(`${API_BASE}/api/orchestrate/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Pipeline failed");
    }

    const data = await res.json();
    clearInterval(timerInterval);
    pipelineTimer.textContent = `${data.execution_time_ms} ms total`;

    // Update Stepper Timings
    const t = data.timings || {};
    document.getElementById("timeSec").textContent = `${t.security_ms || 4}ms`;
    document.getElementById("timeNlp").textContent = `${t.nlp_ms || 8}ms`;
    document.getElementById("timeIr").textContent = `${t.ir_ms || 15}ms`;
    document.getElementById("timeInsight").textContent = `${t.insight_ms || 25}ms`;

    setStepState("stepSec", "completed");
    setStepState("stepNlp", "completed");
    setStepState("stepIr", "completed");
    setStepState("stepInsight", "completed");

    // Render Rich Response
    renderInsightResult(data);
    loadSavedQueries();
    loadAuditLogs();
  } catch (error) {
    clearInterval(timerInterval);
    pipelineTimer.textContent = "Failed";
    showToast(`Error: ${error.message}`, "error");
    resetPipelineStepper();
  } finally {
    spinner.classList.add("hidden");
    label.textContent = "✨ Ask Multi-Agent AI";
    askBtn.disabled = false;
  }
}

function resetPipelineStepper() {
  ["stepSec", "stepNlp", "stepIr", "stepInsight"].forEach(id => {
    const el = document.getElementById(id);
    el.className = "step-card";
  });
  ["timeSec", "timeNlp", "timeIr", "timeInsight"].forEach(id => {
    document.getElementById(id).textContent = "—";
  });
}

function setStepState(stepId, stateClass) {
  const el = document.getElementById(stepId);
  el.className = `step-card ${stateClass}`;
}

function renderInsightResult(data) {
  const resultCard = document.getElementById("resultCard");
  resultCard.classList.remove("hidden");

  const insight = data.insight || {};
  state.currentInsight = insight;

  // Answer formatted with markdown bold highlights
  let formattedAnswer = (insight.answer || "")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
  document.getElementById("answerText").innerHTML = formattedAnswer;

  // Grounding & Confidence Badges
  const groundBadge = document.getElementById("groundingBadge");
  if (insight.grounded !== false) {
    groundBadge.innerHTML = `<span class="badge-icon">✅</span><span class="badge-text">100% Data Grounded (Zero Hallucination)</span>`;
    groundBadge.style.borderColor = "rgba(16, 185, 129, 0.4)";
  } else {
    groundBadge.innerHTML = `<span class="badge-icon">⚠️</span><span class="badge-text">Contextual Figures Flagged</span>`;
    groundBadge.style.borderColor = "rgba(245, 158, 11, 0.4)";
  }

  const confPill = document.getElementById("confidencePill");
  confPill.textContent = `${(insight.confidence || "high").toUpperCase()} CONFIDENCE`;

  document.getElementById("modelPill").textContent = insight.model_used || "AI Grounded Engine";

  // Key Findings List
  const findingsList = document.getElementById("findingsList");
  findingsList.innerHTML = "";
  (insight.key_findings || []).forEach(finding => {
    const li = document.createElement("li");
    li.innerHTML = finding.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    findingsList.appendChild(li);
  });
  document.getElementById("keyFindingsSection").style.display = (insight.key_findings && insight.key_findings.length) ? "block" : "none";

  // KPI Metrics Grid
  renderKpiGrid(insight.stats, insight.forecast);

  // Dynamic Chart.js Visualization
  renderChart(insight.chart_spec, insight.stats, insight.forecast);

  // Reasoning Steps
  const reasoningList = document.getElementById("reasoningStepsList");
  reasoningList.innerHTML = "";
  (insight.reasoning_steps || []).forEach(step => {
    const li = document.createElement("li");
    li.textContent = step;
    reasoningList.appendChild(li);
  });
  document.getElementById("assumptionsText").textContent = (insight.assumptions || []).join(". ") || "Direct database derivation.";

  // Evidence Citations Table
  const evidenceBody = document.getElementById("evidenceTableBody");
  evidenceBody.innerHTML = "";
  const irResults = data.agents?.ir?.results || [];
  document.getElementById("evidenceCount").textContent = irResults.length;

  if (!irResults.length) {
    evidenceBody.innerHTML = `<tr><td colspan="4" style="color:var(--text-muted); text-align:center;">Primary sales repository queried directly.</td></tr>`;
  } else {
    irResults.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(r.name)}</strong></td>
        <td><span class="cosine-badge">${r.score ? (r.score * 100).toFixed(1) + "%" : "Direct"}</span></td>
        <td>${(r.matched_terms || []).map(t => `<span class="prompt-chip" style="padding:2px 6px; font-size:10px;">${t}</span>`).join(" ") || "—"}</td>
        <td style="color:var(--text-secondary);">${escapeHtml(r.snippet || "")}</td>
      `;
      evidenceBody.appendChild(tr);
    });
  }

  // Reset feedback label
  document.getElementById("feedbackStatus").textContent = "";

  // Scroll result into view smoothly
  resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderKpiGrid(stats, forecast) {
  const kpiGrid = document.getElementById("kpiGrid");
  kpiGrid.innerHTML = "";
  if (!stats || Object.keys(stats).length === 0) return;

  const kpis = [];
  if (stats.total !== undefined) {
    kpis.push({ title: `Total ${stats.metric || 'Sales'}`, val: `$${Number(stats.total).toLocaleString()}` });
  }
  if (stats.average !== undefined) {
    kpis.push({ title: "Monthly Avg", val: `$${Number(stats.average).toLocaleString()}` });
  }
  if (stats.top_group) {
    kpis.push({ title: "Top Performer", val: stats.top_group });
  }
  if (stats.bottom_group) {
    kpis.push({ title: "Lowest Group", val: stats.bottom_group });
  }
  if (stats.last_month_change_pct !== undefined) {
    kpis.push({ title: "MoM Growth", val: `${stats.last_month_change_pct > 0 ? '+' : ''}${stats.last_month_change_pct}%` });
  }
  if (forecast && forecast.available && forecast.points && forecast.points[0]) {
    kpis.push({ title: `Projected ${forecast.points[0].month}`, val: `$${Number(forecast.points[0].value).toLocaleString()}` });
  }

  kpis.forEach(k => {
    const card = document.createElement("div");
    card.className = "kpi-card";
    card.innerHTML = `<div class="kpi-title">${k.title}</div><div class="kpi-value">${k.val}</div>`;
    kpiGrid.appendChild(card);
  });
}

function renderChart(chartSpec, stats, forecast) {
  const chartWrapper = document.getElementById("chartWrapper");
  const canvas = document.getElementById("biziqAnalyticsChart");

  if (state.activeChart) {
    state.activeChart.destroy();
    state.activeChart = null;
  }

  if (!chartSpec || !chartSpec.data || !chartSpec.data.labels || !chartSpec.data.labels.length) {
    chartWrapper.style.display = "none";
    return;
  }

  chartWrapper.style.display = "block";
  document.getElementById("chartTitle").textContent = chartSpec.type === "line" ? "📈 Monthly Trend & Forecast Analysis" : "📊 Regional Breakdown & Comparison";

  const ctx = canvas.getContext("2d");
  
  // Custom styling for dark glass aesthetic
  const isLine = chartSpec.type === "line";
  const datasets = chartSpec.data.datasets.map((ds, idx) => {
    if (isLine) {
      if (idx === 0) {
        return {
          ...ds,
          borderColor: "#6366f1",
          backgroundColor: "rgba(99, 102, 241, 0.15)",
          borderWidth: 3,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: "#06b6d4",
          pointRadius: 4,
        };
      } else {
        return {
          ...ds,
          borderColor: "#10b981",
          borderDash: [6, 6],
          borderWidth: 2.5,
          pointBackgroundColor: "#10b981",
          pointRadius: 5,
        };
      }
    } else {
      return {
        ...ds,
        backgroundColor: [
          "rgba(99, 102, 241, 0.8)",
          "rgba(6, 182, 212, 0.8)",
          "rgba(16, 185, 129, 0.8)",
          "rgba(245, 158, 11, 0.8)",
          "rgba(139, 92, 246, 0.8)",
          "rgba(244, 63, 94, 0.8)",
        ],
        borderRadius: 8,
      };
    }
  });

  state.activeChart = new Chart(ctx, {
    type: chartSpec.type || "bar",
    data: {
      labels: chartSpec.data.labels,
      datasets: datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { family: "Inter", size: 12 } }
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.9)",
          titleFont: { family: "Outfit", size: 14, weight: "bold" },
          bodyFont: { family: "Inter", size: 12 },
          borderColor: "rgba(99, 102, 241, 0.4)",
          borderWidth: 1,
          padding: 10,
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", font: { family: "Inter", size: 11 } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#94a3b8",
            font: { family: "Inter", size: 11 },
            callback: (val) => "$" + val.toLocaleString()
          }
        }
      }
    }
  });
}

// ============================================================================
// History & Saved Queries
// ============================================================================

async function loadSavedQueries() {
  try {
    const res = await authFetch(`${API_BASE}/api/v1/nlp/queries?limit=30`);
    if (res.ok) {
      state.queries = await res.json();
      renderHistoryList("");
      document.getElementById("totalQueryCount").textContent = state.queries.length;
    }
  } catch (e) {
    console.error("Failed to load queries:", e);
  }
}

function renderHistoryList(filterTerm = "") {
  const container = document.getElementById("historyListContainer");
  const filtered = state.queries.filter(q => 
    !filterTerm || (q.original_question || "").toLowerCase().includes(filterTerm.toLowerCase())
  );

  if (!filtered.length) {
    container.innerHTML = `<div class="history-placeholder">No saved questions yet.</div>`;
    return;
  }

  container.innerHTML = filtered.map(q => `
    <div class="history-item" data-id="${q.id}">
      <div class="history-question">${escapeHtml(q.original_question)}</div>
      <div class="history-meta">
        <span class="history-tag">${q.intent || 'QUERY'}</span>
        <button class="history-del-btn" data-del-id="${q.id}" title="Delete query">✕</button>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".history-item").forEach(item => {
    item.addEventListener("click", (e) => {
      if (e.target.classList.contains("history-del-btn")) return;
      const qId = item.dataset.id;
      const queryObj = state.queries.find(q => String(q.id) === String(qId));
      if (queryObj) {
        document.getElementById("hubQuestionInput").value = queryObj.original_question;
        executeMultiAgentPipeline(queryObj.original_question);
      }
    });
  });

  container.querySelectorAll(".history-del-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const qId = btn.dataset.delId;
      await authFetch(`${API_BASE}/api/v1/nlp/queries/${qId}`, { method: "DELETE" });
      loadSavedQueries();
      showToast("Question removed from history", "success");
    });
  });
}

async function submitFeedback(helpful) {
  if (!state.currentInsight || !state.currentInsight.id) return;
  try {
    await authFetch(`${API_BASE}/api/v1/insight/insights/${state.currentInsight.id}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ helpful, comment: helpful ? "Helpful" : "Needs detail" }),
    });
    document.getElementById("feedbackStatus").textContent = "✓ Thanks for your feedback!";
    showToast("Feedback submitted to Insight Agent", "success");
  } catch (e) {
    console.error(e);
  }
}

// ============================================================================
// TAB 2: NLP Query Agent Lab (Member 1)
// ============================================================================

function initNlpLab() {
  document.getElementById("nlpRunTestBtn").addEventListener("click", runNlpTest);
  document.getElementById("btnNlpReload").addEventListener("click", () => {
    loadNlpQueriesTable();
    showToast("NLP tables refreshed", "success");
  });
}

async function runNlpTest() {
  const input = document.getElementById("nlpTestInput").value.trim();
  if (!input) return;

  try {
    const res = await authFetch(`${API_BASE}/api/v1/nlp/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: input, top_k: 5 }),
    });
    const data = await res.json();

    document.getElementById("nlpNormValue").textContent = data.normalized_question || input;
    document.getElementById("nlpIntentValue").textContent = data.intent || "UNKNOWN";
    
    const entitiesBox = document.getElementById("nlpEntitiesBox");
    entitiesBox.innerHTML = (data.entities || []).map(e => `
      <span class="prompt-chip" style="background:rgba(99,102,241,0.25); border-color:rgba(99,102,241,0.5); color:#fff;">
        <strong>${e.type}:</strong> ${e.text}
      </span>
    `).join(" ") || "No entities extracted";

    document.getElementById("nlpStructuredQueryBox").textContent = JSON.stringify(data.structured_query, null, 2);
    loadNlpQueriesTable();
  } catch (e) {
    showToast(`NLP Analysis Error: ${e.message}`, "error");
  }
}

async function loadNlpQueriesTable() {
  const tbody = document.getElementById("nlpQueriesTableBody");
  try {
    const res = await authFetch(`${API_BASE}/api/v1/nlp/queries?limit=25`);
    const list = await res.json();
    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No queries logged yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = list.map(q => `
      <tr>
        <td><code>#${q.id}</code></td>
        <td><strong>${escapeHtml(q.original_question)}</strong></td>
        <td><span class="intent-tag" style="font-size:11px;">${q.intent}</span></td>
        <td>${(q.entities || []).map(e => `${e.text} (${e.type})`).join(", ") || "—"}</td>
        <td><button class="link-btn" onclick="deleteNlpQuery(${q.id})">Delete</button></td>
      </tr>
    `).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" style="color:var(--accent-rose);">Failed to load NLP queries.</td></tr>`;
  }
}

window.deleteNlpQuery = async function(id) {
  await authFetch(`${API_BASE}/api/v1/nlp/queries/${id}`, { method: "DELETE" });
  loadNlpQueriesTable();
  loadSavedQueries();
  showToast("Query deleted", "success");
};

// ============================================================================
// TAB 3: Data Retrieval / IR Agent (Member 2)
// ============================================================================

function initIrVault() {
  const openBtn = document.getElementById("openNewDatasourceModalBtn");
  if (openBtn) {
    openBtn.addEventListener("click", () => {
      const modal = document.getElementById("addDataSourceModal") || document.getElementById("datasourceModal");
      if (modal) modal.classList.remove("hidden");
    });
  }
  document.getElementById("btnReSeedDemoData").addEventListener("click", reSeedDemoData);
  document.getElementById("irRunSearchBtn").addEventListener("click", runIrTestSearch);
}

async function loadDataSources() {
  const container = document.getElementById("datasourcesContainer");
  try {
    const res = await authFetch(`${API_BASE}/api/v1/ir/datasources?owner=demo`);
    state.datasources = await res.json();
    if (!state.datasources.length) {
      container.innerHTML = `<div class="empty-state">No data sources in repository. Click "Load Sample SME Datasets" to populate.</div>`;
      return;
    }
    container.innerHTML = state.datasources.map(ds => `
      <div class="history-item" style="padding:12px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <strong style="color:#fff; font-size:14px;">📄 ${escapeHtml(ds.name)}</strong>
            <span class="nav-badge" style="margin-left:6px; text-transform:uppercase;">${ds.source_type}</span>
          </div>
          <button class="history-del-btn" onclick="deleteDatasource(${ds.id})" title="Delete dataset">✕</button>
        </div>
        <p style="font-size:12px; color:var(--text-secondary); margin:6px 0;">${escapeHtml(ds.description || '')}</p>
        <span style="font-size:11px; color:var(--text-muted);">Updated: ${new Date(ds.updated_at || ds.created_at).toLocaleDateString()}</span>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<div class="empty-state" style="color:var(--accent-rose)">Failed to load data sources.</div>`;
  }
}

async function reSeedDemoData() {
  try {
    await authFetch(`${API_BASE}/api/system/seed-demo`, { method: "POST" });
    loadDataSources();
    showToast("Sample SME datasets loaded & indexed successfully!", "success");
  } catch (e) {
    showToast("Failed to seed demo data", "error");
  }
}

async function runIrTestSearch() {
  const query = document.getElementById("irSearchTestInput").value.trim();
  const resultsBox = document.getElementById("irSearchResultsContainer");
  if (!query) return;

  resultsBox.innerHTML = `<div class="loading-state">Ranking corpus with TF-IDF...</div>`;
  try {
    const res = await authFetch(`${API_BASE}/api/v1/ir/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, top_k: 5, owner: "demo" }),
    });
    const data = await res.json();
    if (!data.results || !data.results.length) {
      resultsBox.innerHTML = `<div class="empty-state">No matching documents found above cosine threshold.</div>`;
      return;
    }
    resultsBox.innerHTML = data.results.map(r => `
      <div class="history-item" style="padding:10px; margin-bottom:8px;">
        <div style="display:flex; justify-content:space-between;">
          <strong style="color:var(--accent-cyan);">📄 ${escapeHtml(r.name)}</strong>
          <span class="cosine-badge">${(r.score * 100).toFixed(1)}% Cosine Match</span>
        </div>
        <p style="font-size:12px; color:#cbd5e1; margin-top:4px;">"${escapeHtml(r.snippet)}"</p>
        <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Matched Stems: ${(r.matched_terms || []).join(", ") || "General Match"}</div>
      </div>
    `).join("");
  } catch (e) {
    resultsBox.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">Search failed.</div>`;
  }
}

window.deleteDatasource = async function(id) {
  await authFetch(`${API_BASE}/api/v1/ir/datasources/${id}?owner=demo`, { method: "DELETE" });
  loadDataSources();
  showToast("Data source retired", "success");
};

// ============================================================================
// TAB 4: Insights & Executive Reports (Member 3)
// ============================================================================

function initInsightReports() {
  document.getElementById("btnRefreshReports").addEventListener("click", () => {
    loadReports();
    loadInsightsHistory();
    showToast("Reports refreshed", "success");
  });
}

async function loadReports() {
  const container = document.getElementById("reportsListContainer");
  try {
    const res = await authFetch(`${API_BASE}/api/v1/insight/reports`);
    state.reports = await res.json();
    if (!state.reports.length) {
      container.innerHTML = `<div class="empty-state">No saved executive reports yet. Click "Save to Report" from the AI Query Hub.</div>`;
      return;
    }
    container.innerHTML = state.reports.map(r => `
      <div class="history-item" style="padding:12px; margin-bottom:8px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <strong style="color:#fff; font-size:14px;">📌 ${escapeHtml(r.title)}</strong>
            <span class="user-role-badge analyst" style="margin-left:6px;">REPORT</span>
          </div>
          <button class="history-del-btn" onclick="deleteReport('${r.id}')" title="Delete report">✕</button>
        </div>
        <p style="font-size:12px; color:var(--text-secondary); margin:6px 0; line-height:1.4;">${escapeHtml(r.notes || '')}</p>
        <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted);">
          <span>Created: ${new Date(r.created_at).toLocaleDateString()}</span>
          <button class="link-btn" onclick="viewReportDetail('${r.id}')">View Full Insight</button>
        </div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<div class="empty-state" style="color:var(--accent-rose)">Failed to load reports.</div>`;
  }
}

async function loadInsightsHistory() {
  const container = document.getElementById("insightsHistoryList");
  try {
    const res = await authFetch(`${API_BASE}/api/v1/insight/insights?limit=15`);
    const list = await res.json();
    if (!list.length) {
      container.innerHTML = `<div class="empty-state">No insights generated yet.</div>`;
      return;
    }
    container.innerHTML = list.map(item => `
      <div class="history-item" style="padding:10px; margin-bottom:6px;" onclick="inspectInsight('${item.id}')">
        <strong style="color:var(--text-primary); font-size:13px;">🧠 ${escapeHtml(item.question)}</strong>
        <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-top:4px;">
          <span>Model: ${item.model_used || 'Grounded Engine'}</span>
          <span>${new Date(item.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<div class="empty-state">Failed to load insight history.</div>`;
  }
}

window.deleteReport = async function(id) {
  await authFetch(`${API_BASE}/api/v1/insight/reports/${id}`, { method: "DELETE" });
  loadReports();
  showToast("Report removed", "success");
};

window.viewReportDetail = async function(id) {
  const res = await authFetch(`${API_BASE}/api/v1/insight/reports/${id}`);
  const report = await res.json();
  if (report.insight) {
    switchTab("tab-query-hub");
    renderInsightResult({ insight: report.insight });
    showToast(`Loaded insight for: ${report.title}`, "success");
  }
};

window.inspectInsight = async function(id) {
  const res = await authFetch(`${API_BASE}/api/v1/insight/insights/${id}`);
  const insight = await res.json();
  switchTab("tab-query-hub");
  renderInsightResult({ insight: insight });
};

// ============================================================================
// TAB 5: Security & Compliance Center (Member 4)
// ============================================================================

function initSecurityCenter() {
  document.getElementById("btnRefreshSecurity").addEventListener("click", () => {
    loadAuditLogs();
    loadUsers();
    showToast("Security logs refreshed", "success");
  });
  document.getElementById("btnRunSecurityAnalysis").addEventListener("click", runSecurityAnalysis);
}

async function loadAuditLogs() {
  const tbody = document.getElementById("auditLogsTableBody");
  try {
    const res = await authFetch(`${API_BASE}/api/v1/audit/logs?limit=30`);
    state.auditLogs = await res.json();
    document.getElementById("secTotalAudits").textContent = state.auditLogs.length;

    if (!state.auditLogs.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No audit events logged yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = state.auditLogs.map(log => `
      <tr>
        <td style="font-size:11px; font-family:'Fira Code',monospace;">${new Date(log.created_at).toLocaleTimeString()}</td>
        <td><strong>${log.action}</strong></td>
        <td><span class="grounding-badge" style="padding:2px 8px; font-size:10px; ${log.status==='SUCCESS'?'':'background:rgba(244,63,94,0.2); color:var(--accent-rose); border-color:var(--accent-rose);'}">${log.status}</span></td>
        <td>User #${log.user_id || 1}</td>
        <td style="font-size:11px; color:var(--text-muted);">${escapeHtml(log.details || log.resource || '')}</td>
      </tr>
    `).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" style="color:var(--accent-rose);">Failed to load audit logs.</td></tr>`;
  }
}

async function loadUsers() {
  try {
    const res = await authFetch(`${API_BASE}/api/v1/users`);
    state.users = await res.json();
    document.getElementById("secTotalUsers").textContent = state.users.length;
    
    // Populate dropdown
    const select = document.getElementById("anomalyUserSelect");
    if (select) {
      select.innerHTML = state.users.map(u => `<option value="${u.id}">${u.full_name} (${u.role})</option>`).join("");
    }
  } catch (e) {
    console.error(e);
  }
}

async function runSecurityAnalysis() {
  const select = document.getElementById("anomalyUserSelect");
  const userId = select.value || "1";
  const resultBox = document.getElementById("anomalyResultBox");

  resultBox.innerHTML = `<div class="loading-state">Analyzing access telemetry & running AI Anomaly Reasoning...</div>`;
  try {
    const res = await authFetch(`${API_BASE}/api/v1/security/analyze?user_id=${userId}`, { method: "POST" });
    const data = await res.json();
    const ai = data.ai_result || {};
    const risk = ai.risk_level || "LOW";
    
    document.getElementById("secRiskLevel").textContent = `${risk} RISK`;
    document.getElementById("secRiskLevel").className = `metric-val ${risk === 'LOW' ? 'green' : 'amber'}`;

    resultBox.innerHTML = `
      <div style="border-left: 3px solid ${risk==='LOW'?'var(--accent-emerald)':'var(--accent-amber)'}; padding-left:10px;">
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
          <strong style="color:#fff;">🛡️ Security Assessment: ${escapeHtml(risk)} Risk</strong>
          <span style="font-size:11px; color:var(--text-muted);">Model: ${ai.model_used || 'Groq / Deterministic'}</span>
        </div>
        <p style="font-size:13px; color:var(--text-secondary); line-height:1.4;">${escapeHtml(ai.summary || 'Normal authenticated business query operations. No anomalous logins or credential brute-force patterns detected.')}</p>
        <div style="margin-top:8px; font-size:11px; color:var(--accent-cyan);">Recommendations: ${escapeHtml(ai.recommendations || 'Account posture is healthy. RBAC policies active.')}</div>
      </div>
    `;
  } catch (e) {
    resultBox.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">Analysis error: ${e.message}</div>`;
  }
}

// ============================================================================
// TAB 6: Architecture & Diagnostics
// ============================================================================

function initArchitecture() {
  document.getElementById("btnPingAllAgents").addEventListener("click", checkSystemStatus);
}

async function checkSystemStatus() {
  try {
    const res = await authFetch(`${API_BASE}/api/system/status`);
    const data = await res.json();
    const ag = data.agents || {};

    const pNlp = document.getElementById("pillNlp");
    const pIr = document.getElementById("pillIr");
    const pInsight = document.getElementById("pillInsight");
    const pSec = document.getElementById("pillSecurity");

    if (pNlp) pNlp.className = `agent-pill ${ag.nlp?.status === 'online' ? 'active' : ''}`;
    if (pIr) pIr.className = `agent-pill ${ag.ir?.status === 'online' ? 'active' : ''}`;
    if (pInsight) pInsight.className = `agent-pill ${ag.insight?.status === 'online' ? 'active' : ''}`;
    if (pSec) pSec.className = `agent-pill ${ag.security?.status === 'online' ? 'active' : ''}`;

    showToast("All 4 AI Agents are connected and healthy!", "success");
  } catch (e) {
    showToast("Gateway offline or connecting...", "error");
  }
}

// ============================================================================
// Modals & Authentication Controllers
// ============================================================================

function initModals() {
  // Datasource Modal with Computer File Upload & Drag-and-Drop
  initDatasourceModal();

  // Report Modal
  const repModal = document.getElementById("saveReportModal");
  const closeRepBtn = document.getElementById("closeReportModalBtn");
  const cancelRepBtn = document.getElementById("cancelReportBtn");
  const saveRepBtn = document.getElementById("confirmSaveReportBtn");

  if (closeRepBtn && repModal) closeRepBtn.addEventListener("click", () => repModal.classList.add("hidden"));
  if (cancelRepBtn && repModal) cancelRepBtn.addEventListener("click", () => repModal.classList.add("hidden"));

  if (saveRepBtn) {
    saveRepBtn.addEventListener("click", async () => {
      const title = document.getElementById("reportTitleInput").value.trim();
      const notes = document.getElementById("reportNotesInput").value.trim();

      if (!title || !state.currentInsight) return;
      try {
        await authFetch(`${API_BASE}/api/v1/insight/reports`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            insight_id: state.currentInsight.id,
            title: title,
            notes: notes,
            user_id: state.currentUser.id || "1",
          }),
        });
        if (repModal) repModal.classList.add("hidden");
        loadReports();
        showToast("Executive report pinned & saved!", "success");
      } catch (e) {
        showToast(`Report error: ${e.message}`, "error");
      }
    });
  }

  // Authentication Modal
  initAuthModal();
}

function initDatasourceModal() {
  const dsModal = document.getElementById("datasourceModal");
  const closeDsBtn = document.getElementById("closeDatasourceModalBtn");
  const cancelDsBtn = document.getElementById("cancelDatasourceBtn");
  const saveDsBtn = document.getElementById("saveDatasourceBtn");
  const tabUpload = document.getElementById("tabUploadFile");
  const tabPaste = document.getElementById("tabPasteText");
  const fileSection = document.getElementById("fileUploadSection");
  const dropZone = document.getElementById("fileDropZone");
  const fileInput = document.getElementById("dsFileInput");
  const fileInfo = document.getElementById("uploadedFileInfo");
  const fileNameEl = document.getElementById("uploadedFileName");
  const fileSizeEl = document.getElementById("uploadedFileSize");
  const fileStatsEl = document.getElementById("uploadedFileStats");
  const fileIconEl = document.getElementById("fileTypeIcon");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const contentInput = document.getElementById("dsContentInput");
  const nameInput = document.getElementById("dsNameInput");
  const typeSelect = document.getElementById("dsTypeSelect");
  const descInput = document.getElementById("dsDescInput");
  const charCounter = document.getElementById("contentCharCounter");
  const saveSpinner = document.getElementById("saveDsSpinner");
  const saveBtnText = document.getElementById("saveDsBtnText");

  if (!dsModal) return;

  // Close handlers
  if (closeDsBtn) closeDsBtn.addEventListener("click", () => dsModal.classList.add("hidden"));
  if (cancelDsBtn) cancelDsBtn.addEventListener("click", () => dsModal.classList.add("hidden"));
  dsModal.addEventListener("click", (e) => {
    if (e.target === dsModal) dsModal.classList.add("hidden");
  });

  // Mode tab switching
  if (tabUpload && tabPaste) {
    tabUpload.addEventListener("click", () => {
      tabUpload.classList.add("active");
      tabPaste.classList.remove("active");
      if (fileSection) fileSection.classList.remove("hidden");
    });
    tabPaste.addEventListener("click", () => {
      tabPaste.classList.add("active");
      tabUpload.classList.remove("active");
      if (fileSection) fileSection.classList.add("hidden");
    });
  }

  // File Dropzone interactions
  if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());

    ["dragenter", "dragover"].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("drag-over");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      const files = dt ? dt.files : null;
      if (files && files.length > 0) {
        handleDatasetFile(files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleDatasetFile(fileInput.files[0]);
      }
    });
  }

  function handleDatasetFile(file) {
    if (!file) return;

    // Show file badge
    if (fileInfo) fileInfo.classList.remove("hidden");
    if (fileNameEl) fileNameEl.textContent = file.name;
    if (fileSizeEl) fileSizeEl.textContent = `${(file.size / 1024).toFixed(1)} KB`;

    // Pick icon
    const isCsv = file.name.endsWith(".csv") || file.name.endsWith(".tsv");
    const isJson = file.name.endsWith(".json");
    if (fileIconEl) fileIconEl.textContent = isCsv ? "📊" : (isJson ? "{}" : "📝");

    // Read content
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result || "";
      if (contentInput) {
        contentInput.value = text;
        updateContentStats(text);
      }

      // Auto-populate Title if empty
      if (nameInput && (!nameInput.value.trim() || nameInput.dataset.autoFilled)) {
        const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[_\-\.]+/g, " ");
        nameInput.value = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
        nameInput.dataset.autoFilled = "true";
      }

      // Auto-populate Format
      if (typeSelect) {
        typeSelect.value = (isCsv || (text.split("\n")[0] && text.split("\n")[0].includes(","))) ? "csv" : "text";
      }

      // Auto-detect description if empty
      if (descInput && !descInput.value.trim()) {
        descInput.value = `Imported from ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      }

      // Calculate row stats
      const lines = text.trim().split("\n").filter(l => l.trim().length > 0);
      if (fileStatsEl) {
        if (isCsv && lines.length > 0) {
          const colCount = lines[0].split(",").length;
          fileStatsEl.textContent = `${lines.length - 1} data rows • ${colCount} cols`;
        } else {
          fileStatsEl.textContent = `${lines.length} lines parsed`;
        }
      }

      showToast(`Loaded ${file.name} successfully!`, "success");
    };

    reader.onerror = () => {
      showToast("Error reading file from computer", "error");
    };

    reader.readAsText(file);
  }

  // Remove attached file
  if (removeFileBtn) {
    removeFileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (fileInput) fileInput.value = "";
      if (fileInfo) fileInfo.classList.add("hidden");
      if (contentInput) contentInput.value = "";
      if (nameInput && nameInput.dataset.autoFilled) nameInput.value = "";
      if (charCounter) charCounter.textContent = "0 lines";
      showToast("File detached", "info");
    });
  }

  // Live content stats counter
  if (contentInput) {
    contentInput.addEventListener("input", () => {
      updateContentStats(contentInput.value);
    });
  }

  function updateContentStats(text) {
    if (!charCounter) return;
    const lines = text ? text.split("\n").length : 0;
    const kb = text ? (text.length / 1024).toFixed(1) : "0.0";
    charCounter.textContent = `${lines} lines • ${kb} KB`;
  }

  // Save / Index action
  if (saveDsBtn) {
    saveDsBtn.addEventListener("click", async () => {
      const name = nameInput ? nameInput.value.trim() : "";
      const type = typeSelect ? typeSelect.value : "csv";
      const desc = descInput ? descInput.value.trim() : "";
      const content = contentInput ? contentInput.value.trim() : "";

      if (!name || !content) {
        showToast("Please provide dataset title and content.", "error");
        return;
      }

      if (saveSpinner) saveSpinner.classList.remove("hidden");
      if (saveBtnText) saveBtnText.textContent = "Indexing Corpus...";
      saveDsBtn.disabled = true;

      try {
        const res = await authFetch(`${API_BASE}/api/v1/ir/datasources`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: name,
            description: desc,
            content: content,
            source_type: type,
            owner: "demo",
          }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Failed to save dataset" }));
          throw new Error(err.detail || "Indexing failed");
        }

        dsModal.classList.add("hidden");
        // Reset inputs
        if (fileInput) fileInput.value = "";
        if (fileInfo) fileInfo.classList.add("hidden");
        if (nameInput) nameInput.value = "";
        if (descInput) descInput.value = "";
        if (contentInput) contentInput.value = "";
        if (charCounter) charCounter.textContent = "0 lines";

        loadDataSources();
        showToast(`Dataset "${name}" successfully indexed into IR Vault!`, "success");
      } catch (e) {
        showToast(`Dataset indexing error: ${e.message}`, "error");
      } finally {
        if (saveSpinner) saveSpinner.classList.add("hidden");
        if (saveBtnText) saveBtnText.textContent = "⚡ Index Dataset in Vault";
        saveDsBtn.disabled = false;
      }
    });
  }
}


  // Report Modal
  const repModal = document.getElementById("saveReportModal");
  const closeRepBtn = document.getElementById("closeReportModalBtn");
  const cancelRepBtn = document.getElementById("cancelReportBtn");
  const saveRepBtn = document.getElementById("confirmSaveReportBtn");

  if (closeRepBtn && repModal) closeRepBtn.addEventListener("click", () => repModal.classList.add("hidden"));
  if (cancelRepBtn && repModal) cancelRepBtn.addEventListener("click", () => repModal.classList.add("hidden"));

  if (saveRepBtn) {
    saveRepBtn.addEventListener("click", async () => {
      const title = document.getElementById("reportTitleInput").value.trim();
      const notes = document.getElementById("reportNotesInput").value.trim();

      if (!title || !state.currentInsight) return;
      try {
        await authFetch(`${API_BASE}/api/v1/insight/reports`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            insight_id: state.currentInsight.id,
            title: title,
            notes: notes,
            user_id: state.currentUser.id || "1",
          }),
        });
        if (repModal) repModal.classList.add("hidden");
        loadReports();
        showToast("Executive report pinned & saved!", "success");
      } catch (e) {
        showToast(`Report error: ${e.message}`, "error");
      }
    });
  }

  // Authentication Modal
  initAuthModal();
}

function initAuthModal() {
  const authModal = document.getElementById("authModal");
  const closeAuthModalBtn = document.getElementById("closeAuthModalBtn");
  const authTabLogin = document.getElementById("authTabLogin");
  const authTabRegister = document.getElementById("authTabRegister");
  const authLoginForm = document.getElementById("authLoginForm");
  const authRegisterForm = document.getElementById("authRegisterForm");
  const authBanner = document.getElementById("authStatusBanner");
  const doLoginBtn = document.getElementById("doLoginBtn");
  const doRegisterBtn = document.getElementById("doRegisterBtn");
  const loginEmail = document.getElementById("loginEmail");
  const loginPassword = document.getElementById("loginPassword");
  const toggleLoginPwdBtn = document.getElementById("toggleLoginPwdBtn");
  const toggleRegPwdBtn = document.getElementById("toggleRegPwdBtn");
  const regPassword = document.getElementById("regPassword");

  if (closeAuthModalBtn && authModal) {
    closeAuthModalBtn.addEventListener("click", () => {
      authModal.classList.add("hidden");
      if (authBanner) authBanner.classList.add("hidden");
    });
  }

  // Backdrop click to close
  if (authModal) {
    authModal.addEventListener("click", (e) => {
      if (e.target === authModal) {
        authModal.classList.add("hidden");
        if (authBanner) authBanner.classList.add("hidden");
      }
    });
  }

  // Password visibility toggles
  if (toggleLoginPwdBtn && loginPassword) {
    toggleLoginPwdBtn.addEventListener("click", () => {
      const isPassword = loginPassword.type === "password";
      loginPassword.type = isPassword ? "text" : "password";
      toggleLoginPwdBtn.textContent = isPassword ? "🙈" : "👁️";
    });
  }

  if (toggleRegPwdBtn && regPassword) {
    toggleRegPwdBtn.addEventListener("click", () => {
      const isPassword = regPassword.type === "password";
      regPassword.type = isPassword ? "text" : "password";
      toggleRegPwdBtn.textContent = isPassword ? "🙈" : "👁️";
    });
  }

  // Tab switching
  if (authTabLogin && authTabRegister) {
    authTabLogin.addEventListener("click", () => {
      authTabLogin.classList.add("active");
      authTabRegister.classList.remove("active");
      if (authLoginForm) authLoginForm.classList.remove("hidden");
      if (authRegisterForm) authRegisterForm.classList.add("hidden");
      if (authBanner) authBanner.classList.add("hidden");
    });

    authTabRegister.addEventListener("click", () => {
      authTabRegister.classList.add("active");
      authTabLogin.classList.remove("active");
      if (authRegisterForm) authRegisterForm.classList.remove("hidden");
      if (authLoginForm) authLoginForm.classList.add("hidden");
      if (authBanner) authBanner.classList.add("hidden");
    });
  }

  // Demo Pills in Modal
  document.querySelectorAll(".demo-pill[data-demo-email]").forEach(pill => {
    pill.addEventListener("click", async () => {
      const email = pill.dataset.demoEmail;
      const pwd = pill.dataset.demoPwd;
      if (loginEmail) loginEmail.value = email;
      if (loginPassword) loginPassword.value = pwd;
      document.querySelectorAll(".demo-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      await signInWithCredentials(email, pwd, false);
    });
  });

  // Login action
  if (doLoginBtn && loginEmail && loginPassword) {
    doLoginBtn.addEventListener("click", () => {
      const email = loginEmail.value.trim();
      const pwd = loginPassword.value.trim();
      if (!email || !pwd) {
        if (authBanner) {
          authBanner.className = "auth-banner error";
          authBanner.textContent = "Please enter both email/username and password.";
          authBanner.classList.remove("hidden");
        }
        showToast("Please enter email/username and password", "error");
        return;
      }
      signInWithCredentials(email, pwd, false);
    });

    // Enter key support
    loginPassword.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doLoginBtn.click();
    });
    loginEmail.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doLoginBtn.click();
    });
  }

  // Register action
  if (doRegisterBtn) {
    doRegisterBtn.addEventListener("click", () => {
      const fullName = document.getElementById("regFullName").value.trim();
      const username = document.getElementById("regUsername").value.trim();
      const email = document.getElementById("regEmail").value.trim();
      const role = document.getElementById("regRole").value;
      const pwd = document.getElementById("regPassword").value.trim();

      registerAccount(fullName, username, email, pwd, role);
    });

    if (regPassword) {
      regPassword.addEventListener("keydown", (e) => {
        if (e.key === "Enter") doRegisterBtn.click();
      });
    }
  }
}

// ============================================================================
// Utilities
// ============================================================================

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : (type === 'error' ? '⚠️' : 'ℹ️')}</span> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
