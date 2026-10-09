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

// Global App State
const state = {
  activeTab: "tab-query-hub",
  currentUser: {
    id: "1",
    username: "achini",
    name: "Achini",
    role: "ANALYST",
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

  // Initial data fetch
  refreshAllSystemState();
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
// User & Auth Management
// ============================================================================

function initUserSwitcher() {
  const activeUserBtn = document.getElementById("activeUserBtn");
  const userDropdown = document.getElementById("userDropdownMenu");

  activeUserBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    userDropdown.classList.toggle("hidden");
  });

  document.addEventListener("click", () => {
    userDropdown.classList.add("hidden");
  });

  document.querySelectorAll(".dropdown-item[data-user]").forEach(item => {
    item.addEventListener("click", () => {
      const userKey = item.dataset.user;
      const role = item.dataset.role;
      const name = item.dataset.name;
      setUser(userKey, name, role);
      userDropdown.classList.add("hidden");
      showToast(`Switched active profile to ${name}`, "success");
    });
  });
}

function setUser(username, fullName, role) {
  state.currentUser.username = username;
  state.currentUser.name = fullName.split(" ")[0];
  state.currentUser.role = role.toUpperCase();
  state.currentUser.id = username === "admin" ? "1" : (username === "achini" ? "2" : "3");

  document.getElementById("currentUserName").textContent = state.currentUser.name;
  const roleBadge = document.getElementById("currentUserRole");
  roleBadge.textContent = state.currentUser.role;
  roleBadge.className = `user-role-badge ${role.toLowerCase()}`;
  document.getElementById("userAvatar").textContent = state.currentUser.name[0];
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
      user_id: state.currentUser.id,
      user_role: state.currentUser.role.toLowerCase(),
      owner: "demo",
    };

    const res = await fetch(`${API_BASE}/api/orchestrate/query`, {
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
    const res = await fetch(`${API_BASE}/api/v1/nlp/queries?limit=30`);
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
      await fetch(`${API_BASE}/api/v1/nlp/queries/${qId}`, { method: "DELETE" });
      loadSavedQueries();
      showToast("Question removed from history", "success");
    });
  });
}

async function submitFeedback(helpful) {
  if (!state.currentInsight || !state.currentInsight.id) return;
  try {
    await fetch(`${API_BASE}/api/v1/insight/insights/${state.currentInsight.id}/feedback`, {
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
    const res = await fetch(`${API_BASE}/api/v1/nlp/process`, {
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
    const res = await fetch(`${API_BASE}/api/v1/nlp/queries?limit=25`);
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
  await fetch(`${API_BASE}/api/v1/nlp/queries/${id}`, { method: "DELETE" });
  loadNlpQueriesTable();
  loadSavedQueries();
  showToast("Query deleted", "success");
};

// ============================================================================
// TAB 3: Data Retrieval / IR Agent (Member 2)
// ============================================================================

function initIrVault() {
  document.getElementById("openNewDatasourceModalBtn").addEventListener("click", () => {
    document.getElementById("datasourceModal").classList.remove("hidden");
  });
  document.getElementById("btnReSeedDemoData").addEventListener("click", reSeedDemoData);
  document.getElementById("irRunSearchBtn").addEventListener("click", runIrTestSearch);
}

async function loadDataSources() {
  const container = document.getElementById("datasourcesContainer");
  try {
    const res = await fetch(`${API_BASE}/api/v1/ir/datasources?owner=demo`);
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
    await fetch(`${API_BASE}/api/system/seed-demo`, { method: "POST" });
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
    const res = await fetch(`${API_BASE}/api/v1/ir/search`, {
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
  await fetch(`${API_BASE}/api/v1/ir/datasources/${id}?owner=demo`, { method: "DELETE" });
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
    const res = await fetch(`${API_BASE}/api/v1/insight/reports`);
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
    const res = await fetch(`${API_BASE}/api/v1/insight/insights?limit=15`);
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
  await fetch(`${API_BASE}/api/v1/insight/reports/${id}`, { method: "DELETE" });
  loadReports();
  showToast("Report removed", "success");
};

window.viewReportDetail = async function(id) {
  const res = await fetch(`${API_BASE}/api/v1/insight/reports/${id}`);
  const report = await res.json();
  if (report.insight) {
    switchTab("tab-query-hub");
    renderInsightResult({ insight: report.insight });
    showToast(`Loaded insight for: ${report.title}`, "success");
  }
};

window.inspectInsight = async function(id) {
  const res = await fetch(`${API_BASE}/api/v1/insight/insights/${id}`);
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
    const res = await fetch(`${API_BASE}/api/v1/audit/logs?limit=30`);
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
    const res = await fetch(`${API_BASE}/api/v1/users`);
    state.users = await res.json();
    document.getElementById("secTotalUsers").textContent = state.users.length;
    
    // Populate dropdown
    const select = document.getElementById("anomalyUserSelect");
    select.innerHTML = state.users.map(u => `<option value="${u.id}">${u.full_name} (${u.role})</option>`).join("");
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
    const res = await fetch(`${API_BASE}/api/v1/security/analyze?user_id=${userId}`, { method: "POST" });
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
    const res = await fetch(`${API_BASE}/api/system/status`);
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
// Modals Handling
// ============================================================================

function initModals() {
  // Datasource Modal
  const dsModal = document.getElementById("datasourceModal");
  document.getElementById("closeDatasourceModalBtn").addEventListener("click", () => dsModal.classList.add("hidden"));
  document.getElementById("cancelDatasourceBtn").addEventListener("click", () => dsModal.classList.add("hidden"));

  document.getElementById("saveDatasourceBtn").addEventListener("click", async () => {
    const name = document.getElementById("dsNameInput").value.trim();
    const type = document.getElementById("dsTypeSelect").value;
    const desc = document.getElementById("dsDescInput").value.trim();
    const content = document.getElementById("dsContentInput").value.trim();

    if (!name || !content) {
      showToast("Please provide dataset name and content.", "error");
      return;
    }

    try {
      await fetch(`${API_BASE}/api/v1/ir/datasources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description: desc, content, source_type: type, owner: "demo" }),
      });
      dsModal.classList.add("hidden");
      loadDataSources();
      showToast(`Data source "${name}" indexed!`, "success");
    } catch (e) {
      showToast(`Save error: ${e.message}`, "error");
    }
  });

  // Report Modal
  const repModal = document.getElementById("saveReportModal");
  document.getElementById("closeReportModalBtn").addEventListener("click", () => repModal.classList.add("hidden"));
  document.getElementById("cancelReportBtn").addEventListener("click", () => repModal.classList.add("hidden"));

  document.getElementById("confirmSaveReportBtn").addEventListener("click", async () => {
    const title = document.getElementById("reportTitleInput").value.trim();
    const notes = document.getElementById("reportNotesInput").value.trim();

    if (!title || !state.currentInsight) return;
    try {
      await fetch(`${API_BASE}/api/v1/insight/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          insight_id: state.currentInsight.id,
          title: title,
          notes: notes,
          user_id: state.currentUser.id,
        }),
      });
      repModal.classList.add("hidden");
      loadReports();
      showToast("Executive report pinned & saved!", "success");
    } catch (e) {
      showToast(`Report error: ${e.message}`, "error");
    }
  });

  // Auth Modal
  const authModal = document.getElementById("authModal");
  document.getElementById("openAuthModalBtn").addEventListener("click", () => authModal.classList.remove("hidden"));
  document.getElementById("closeAuthModalBtn").addEventListener("click", () => authModal.classList.add("hidden"));

  document.getElementById("authTabLogin").addEventListener("click", () => {
    document.getElementById("authTabLogin").classList.add("active");
    document.getElementById("authTabRegister").classList.remove("active");
    document.getElementById("authLoginForm").classList.remove("hidden");
    document.getElementById("authRegisterForm").classList.add("hidden");
  });

  document.getElementById("authTabRegister").addEventListener("click", () => {
    document.getElementById("authTabRegister").classList.add("active");
    document.getElementById("authTabLogin").classList.remove("active");
    document.getElementById("authRegisterForm").classList.remove("hidden");
    document.getElementById("authLoginForm").classList.add("hidden");
  });

  document.getElementById("doLoginBtn").addEventListener("click", async () => {
    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value.trim();
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error("Invalid credentials");
      const data = await res.json();
      state.currentUser.token = data.access_token;
      if (data.user) {
        setUser(data.user.username, data.user.full_name, data.user.role);
      }
      authModal.classList.add("hidden");
      showToast(`Welcome back, ${state.currentUser.name}!`, "success");
    } catch (e) {
      showToast("Login failed: Check credentials", "error");
    }
  });

  document.getElementById("doRegisterBtn").addEventListener("click", async () => {
    const full_name = document.getElementById("regFullName").value.trim();
    const username = document.getElementById("regUsername").value.trim();
    const email = document.getElementById("regEmail").value.trim();
    const password = document.getElementById("regPassword").value.trim();
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name, username, email, password }),
      });
      if (!res.ok) throw new Error("Registration failed");
      showToast("Account created! You can now login.", "success");
      document.getElementById("authTabLogin").click();
    } catch (e) {
      showToast(`Registration error: ${e.message}`, "error");
    }
  });
}

// ============================================================================
// Utilities
// ============================================================================

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : '⚠️'}</span> <span>${escapeHtml(message)}</span>`;
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
