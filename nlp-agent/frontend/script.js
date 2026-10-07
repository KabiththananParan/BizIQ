const API = "http://127.0.0.1:8001";

const questionInput = document.getElementById("questionInput");
const askBtn = document.getElementById("askBtn");
const askBtnText = document.getElementById("askBtnText");
const editMode = document.getElementById("editMode");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const statusMessage = document.getElementById("statusMessage");

const intentValue = document.getElementById("intentValue");
const entitiesValue = document.getElementById("entitiesValue");
const summaryValue = document.getElementById("summaryValue");
const structuredValue = document.getElementById("structuredValue");

const llmResponse = document.getElementById("llmResponse");
const llmMeta = document.getElementById("llmMeta");

const recentList = document.getElementById("recentList");
const searchInput = document.getElementById("searchInput");
const refreshBtn = document.getElementById("refreshBtn");

const menu = document.getElementById("menu");
const menuEdit = document.getElementById("menuEdit");
const menuDelete = document.getElementById("menuDelete");

const confirmModal = document.getElementById("confirmModal");
const deleteQuestionText = document.getElementById("deleteQuestionText");
const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");
const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");

let allQueries = [];
let selectedQuery = null;
let editingQueryId = null;
let deletingQueryId = null;

document.addEventListener("DOMContentLoaded", () => {
  loadQueries();
});

askBtn.addEventListener("click", submitQuestion);
cancelEditBtn.addEventListener("click", cancelEdit);
refreshBtn.addEventListener("click", loadQueries);
searchInput.addEventListener("input", renderRecentQuestions);

document.querySelectorAll(".example-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    questionInput.value = btn.textContent.trim();
    questionInput.focus();
  });
});

document.addEventListener("click", (event) => {
  if (!menu.contains(event.target) && !event.target.classList.contains("more-btn")) {
    closeMenu();
  }
});

menuEdit.addEventListener("click", () => {
  if (!selectedQuery) return;

  editingQueryId = selectedQuery.id;
  questionInput.value = selectedQuery.original_question;
  editMode.classList.remove("hidden");
  askBtnText.textContent = "Update & Ask";
  questionInput.focus();
  closeMenu();

  setStatus("Editing an existing query. Change the question and click Update & Ask.");
});

menuDelete.addEventListener("click", () => {
  if (!selectedQuery) return;

  deletingQueryId = selectedQuery.id;
  deleteQuestionText.textContent = selectedQuery.original_question;
  confirmModal.classList.remove("hidden");
  closeMenu();
});

cancelDeleteBtn.addEventListener("click", closeDeleteModal);

confirmDeleteBtn.addEventListener("click", async () => {
  if (!deletingQueryId) return;

  try {
    setStatus("Deleting question...");
    const response = await fetch(`${API}/queries/${deletingQueryId}`, {
      method: "DELETE"
    });

    if (!response.ok) {
      throw new Error(await getError(response));
    }

    closeDeleteModal();
    setStatus("Question deleted successfully.");
    await loadQueries();
  } catch (error) {
    setStatus(`Delete failed: ${error.message}`, true);
  }
});

questionInput.addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    submitQuestion();
  }
});

async function submitQuestion() {
  const question = questionInput.value.trim();

  if (!question) {
    setStatus("Please enter a question.", true);
    questionInput.focus();
    return;
  }

  setBusy(true);
  setStatus(editingQueryId ? "Updating the existing query and running NLP analysis..." : "Running NLP analysis...");

  try {
    let data;

    if (editingQueryId) {
      /*
       * Important:
       * PUT /queries/{id} updates the SAME database record.
       * It does not create a new query.
       */
      data = await apiRequest(`/queries/${editingQueryId}`, {
        method: "PUT",
        body: JSON.stringify({ question })
      });

      showNlpResult(data);
      showLLMResponse(data);

      setStatus("Query updated successfully. The existing record was updated.");
      finishEdit();
      await loadQueries();
    } else {
      /*
       * POST /query already saves the question in the current backend.
       * send_to_ir=false is used while the other agents are not integrated.
       * After Member 2 + Member 3 integration, change this to true.
       */
      data = await apiRequest("/query", {
        method: "POST",
        body: JSON.stringify({
          question,
          send_to_ir: false,
          top_k: 5
        })
      });

      showNlpResult(data);
      showLLMResponse(data);

      setStatus("Question processed and saved successfully.");
      await loadQueries();
    }
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function loadQueries() {
  try {
    recentList.innerHTML = `<div class="loading">Loading questions...</div>`;

    const data = await apiRequest("/queries", { method: "GET" });

    allQueries = Array.isArray(data) ? data : (data.items || data.queries || []);
    allQueries.sort((a, b) => {
      return Number(b.id || 0) - Number(a.id || 0);
    });

    renderRecentQuestions();
  } catch (error) {
    recentList.innerHTML = `<div class="empty">Could not load saved questions.<br><small>${escapeHtml(error.message)}</small></div>`;
  }
}

function renderRecentQuestions() {
  const term = searchInput.value.trim().toLowerCase();

  const filtered = allQueries.filter(q =>
    String(q.original_question || "").toLowerCase().includes(term) ||
    String(q.normalized_question || "").toLowerCase().includes(term)
  );

  const visible = filtered.slice(0, 10);

  if (!visible.length) {
    recentList.innerHTML = `<div class="empty">No saved questions found.</div>`;
    return;
  }

  recentList.innerHTML = visible.map(q => `
    <div class="recent-item">
      <button class="more-btn" type="button" data-id="${q.id}" title="Options">⋮</button>
      <div class="recent-question">${escapeHtml(q.original_question || "")}</div>
      <div class="recent-time">${formatDate(q.created_at)}</div>
    </div>
  `).join("");

  recentList.querySelectorAll(".more-btn").forEach(btn => {
    btn.addEventListener("click", event => {
      event.stopPropagation();

      const id = Number(btn.dataset.id);
      selectedQuery = allQueries.find(q => Number(q.id) === id);

      if (!selectedQuery) return;

      const rect = btn.getBoundingClientRect();

      menu.style.left = `${Math.min(rect.left, window.innerWidth - 155)}px`;
      menu.style.top = `${rect.bottom + 5}px`;
      menu.classList.remove("hidden");
    });
  });

  recentList.querySelectorAll(".recent-item").forEach(item => {
    item.addEventListener("click", event => {
      if (event.target.classList.contains("more-btn")) return;

      const button = item.querySelector(".more-btn");
      const id = Number(button.dataset.id);
      const query = allQueries.find(q => Number(q.id) === id);

      if (query) {
        displaySavedQuery(query);
      }
    });
  });
}

function displaySavedQuery(query) {
  questionInput.value = query.original_question || "";
  showNlpResult(query);
  showLLMResponse(query);
  setStatus("Previous question loaded. Use ⋮ → Edit if you want to update it.");
}

function showNlpResult(data) {
  intentValue.textContent = data.intent || data.structured_query?.intent || "—";

  const entities = Array.isArray(data.entities) ? data.entities : [];
  if (!entities.length) {
    entitiesValue.innerHTML = "—";
  } else {
    entitiesValue.innerHTML = entities.map(entity => `
      <span class="chip">
        ${escapeHtml(entity.text || "")}
        <span class="chip-type">${escapeHtml(entity.type || "")}</span>
      </span>
    `).join("");
  }

  summaryValue.textContent = data.summary || "No summary generated.";

  const structured = data.structured_query || {};
  structuredValue.textContent = JSON.stringify(structured, null, 2);
}

function showLLMResponse(data) {
  /*
   * This function intentionally does NOT invent an LLM answer.
   * It displays the actual LLM response when the integrated backend
   * returns one.
   *
   * It supports common response wrappers so the frontend can adapt
   * when Member 3's final response contract is connected.
   */
  const candidate = findLLMResponse(data);

  if (!candidate) {
    llmResponse.classList.add("empty-response");
    llmResponse.textContent =
      "LLM Insight Agent response will appear here after the IR + LLM agents are connected.";
    llmMeta.classList.add("hidden");
    return;
  }

  llmResponse.classList.remove("empty-response");

  if (typeof candidate === "string") {
    llmResponse.textContent = candidate;
  } else {
    const answer =
      candidate.answer ??
      candidate.response ??
      candidate.insight ??
      candidate.text ??
      candidate.message;

    if (answer) {
      llmResponse.textContent = String(answer);
    } else {
      llmResponse.textContent = JSON.stringify(candidate, null, 2);
    }

    const confidence = candidate.confidence;
    if (confidence !== undefined) {
      llmMeta.textContent = `Confidence: ${confidence}`;
      llmMeta.classList.remove("hidden");
    } else {
      llmMeta.classList.add("hidden");
    }
  }
}

function findLLMResponse(data) {
  const possible = [
    data?.llm_result,
    data?.llm_response,
    data?.llm,
    data?.insight,
    data?.answer,
    data?.response?.llm_result,
    data?.response?.llm_response,
    data?.ir_result?.llm_result,
    data?.ir_result?.llm_response,
    data?.ir_result?.llm,
    data?.ir_result?.insight,
    data?.ir_result?.answer,
    data?.ir_result?.response
  ];

  return possible.find(value =>
    value !== undefined &&
    value !== null &&
    value !== ""
  );
}

async function apiRequest(path, options = {}) {
  const finalOptions = {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  };

  const response = await fetch(`${API}${path}`, finalOptions);

  if (!response.ok) {
    throw new Error(await getError(response));
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function getError(response) {
  try {
    const data = await response.json();

    if (typeof data.detail === "string") {
      return data.detail;
    }

    return JSON.stringify(data);
  } catch {
    return `HTTP ${response.status}`;
  }
}

function startEditMode() {
  editMode.classList.remove("hidden");
  askBtnText.textContent = "Update & Ask";
}

function finishEdit() {
  editingQueryId = null;
  editMode.classList.add("hidden");
  askBtnText.textContent = "Ask BizIQ";
}

function cancelEdit() {
  finishEdit();
  questionInput.value = "";
  setStatus("Edit cancelled.");
}

function closeMenu() {
  menu.classList.add("hidden");
}

function closeDeleteModal() {
  confirmModal.classList.add("hidden");
  deletingQueryId = null;
}

function setBusy(isBusy) {
  askBtn.disabled = isBusy;
  askBtnText.textContent = isBusy
    ? "Processing..."
    : (editingQueryId ? "Update & Ask" : "Ask BizIQ");
}

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.style.color = isError ? "#e5484d" : "#7180a0";
}

function formatDate(value) {
  if (!value) return "Saved query";

  const date = new Date(value.replace(" ", "T") + (value.endsWith("Z") ? "" : "Z"));

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
