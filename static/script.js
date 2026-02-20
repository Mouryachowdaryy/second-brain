/* ============================================================
   AI Second Brain — Application Script
   Handles: navigation, dashboard, goals CRUD, tasks CRUD,
            analytics charts, AI chat
   ============================================================ */

"use strict";

// ─── State ────────────────────────────────────────────────────
const state = {
  currentPage: "dashboard",
  analytics:   null,
  goals:       [],
  selectedGoalId: null,
};

// ─── Init ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  bindNav();
  bindChat();
  loadAll();
});

async function loadAll() {
  await loadAnalytics();
  await loadGoals();
}

// ─── Navigation ───────────────────────────────────────────────
function bindNav() {
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => navigate(item.dataset.page));
  });
}

function navigate(page) {
  state.currentPage = page;
  document.querySelectorAll(".page-section").forEach(s => s.classList.add("hidden"));
  document.querySelectorAll(".nav-item").forEach(n => {
    n.classList.toggle("active", n.dataset.page === page);
  });
  const el = document.getElementById("page-" + page);
  if (el) el.classList.remove("hidden");

  // lazy-load page data
  if (page === "analytics") renderAnalyticsPage();
  if (page === "tasks")     renderGoalSelector();
  if (page === "goals")     renderGoalsTable();
  if (page === "dashboard") renderDashboard();
}

// ─── API helpers ──────────────────────────────────────────────
async function api(path, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}

// ─── Load data ────────────────────────────────────────────────
async function loadAnalytics() {
  try {
    state.analytics = await api("/api/analytics");
    renderTopbar();
    renderDashboard();
  } catch (e) {
    console.error("Analytics load failed:", e);
  }
}

async function loadGoals() {
  try {
    state.goals = await api("/api/goals");
  } catch (e) {
    console.error("Goals load failed:", e);
  }
}

// ─── Topbar ───────────────────────────────────────────────────
function renderTopbar() {
  const a = state.analytics;
  if (!a) return;
  document.getElementById("tb-mood").textContent   = a.mood || "—";
  document.getElementById("tb-streak").textContent = a.streak + "-Day Streak";
}

// ─── Dashboard ────────────────────────────────────────────────
function renderDashboard() {
  const a = state.analytics;
  if (!a) return;

  setText("stat-week-hours", a.week_hours + "h");
  setText("stat-streak",     a.streak + "d");
  setText("stat-active",     a.active_count);
  setText("stat-completed",  a.completed_count);

  // Goal list
  const list = document.getElementById("dash-goal-list");
  if (!list) return;
  list.innerHTML = "";
  const active = (a.goals || []).filter(g => g.status === "active");
  if (!active.length) {
    list.innerHTML = '<div class="text-muted">No active goals. Add one in the Goals section.</div>';
  } else {
    active.forEach(g => {
      const item = el("div", "goal-summary-item");
      item.innerHTML = `
        <div class="gsi-top">
          <span class="gsi-title">${esc(g.title)}</span>
          <span class="badge badge-${g.priority}">${g.priority}</span>
        </div>
        <div class="gsi-meta">${g.tasks_done}/${g.total_tasks} tasks &nbsp;·&nbsp; ${g.days_left >= 0 ? g.days_left + " days left" : "Overdue"}</div>
        <div class="progress-bar">
          <div class="progress-fill" style="width:${g.progress}%"></div>
        </div>`;
      list.appendChild(item);
    });
  }

  // Bar chart
  renderBarChart("bar-chart", a.log_chart || []);
}

function renderBarChart(containerId, logs) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";
  const max = Math.max(...logs.map(l => l.hours), 1);
  logs.forEach(l => {
    const pct = (l.hours / max) * 100;
    const day = l.date ? new Date(l.date).toLocaleDateString("en", { weekday: "short" }) : "";
    const col = el("div", "bar-col");
    col.innerHTML = `
      <div class="bar-val">${l.hours > 0 ? l.hours + "h" : ""}</div>
      <div class="bar-fill" style="height:${Math.max(pct, l.hours > 0 ? 4 : 0)}%" title="${l.hours}h"></div>
      <div class="bar-label">${day}</div>`;
    container.appendChild(col);
  });
}

// ─── Quick log hours / mood ────────────────────────────────────
async function quickLogHours() {
  const val = parseFloat(document.getElementById("quick-hours").value);
  if (!val || val <= 0) return toast("Enter valid hours", "err");
  await api("/api/log-hours", "POST", { hours: val });
  document.getElementById("quick-hours").value = "";
  toast("Logged " + val + " hours");
  await loadAnalytics();
}

async function quickMood() {
  const mood = document.getElementById("quick-mood").value;
  await api("/api/mood", "POST", { mood });
  toast("Mood updated: " + mood);
  await loadAnalytics();
}

// ─── Goals CRUD ───────────────────────────────────────────────
function renderGoalsTable() {
  const tbody = document.getElementById("goals-tbody");
  if (!tbody) return;

  const goals = state.goals;
  if (!goals.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-muted" style="padding:20px">No goals yet. Click "+ Add Goal" to create one.</td></tr>';
    return;
  }

  tbody.innerHTML = "";
  goals.forEach(g => {
    const pri = g.priority || "MEDIUM";
    const isComplete = g.status === "completed";
    const tr = document.createElement("tr");
    if (isComplete) tr.className = "row-completed";

    tr.innerHTML = `
      <td>
        <div class="goal-title-cell ${isComplete ? "completed-line" : ""}">
          ${esc(g.title)}
        </div>
      </td>
      <td><span class="badge badge-${pri}">${pri}</span></td>
      <td style="color:var(--ink-muted);font-size:0.82rem">${g.deadline}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <div class="mini-progress"><div class="mini-progress-fill" style="width:${g.progress}%"></div></div>
          <span style="font-size:0.78rem;color:var(--ink-muted)">${g.progress}%</span>
        </div>
      </td>
      <td style="font-size:0.82rem;color:${g.days_left < 0 ? "var(--warn)" : "var(--ink-muted)"}">
        ${g.days_left < 0 ? "Overdue" : g.days_left + "d"}
      </td>
      <td>
        <div class="action-row">
          ${!isComplete ? `<button class="btn btn-success btn-sm btn-icon" title="Mark complete" onclick="confirmMarkGoalComplete(${g.id}, '${esc(g.title)}')">&#10003;</button>` : ""}
          <button class="btn btn-ghost btn-sm btn-icon" title="Edit" onclick="openEditGoal(${g.id})">&#9998;</button>
          <button class="btn btn-danger btn-sm btn-icon" title="Delete" onclick="confirmDeleteGoal(${g.id}, '${esc(g.title)}')">&#128465;</button>
        </div>
      </td>`;
    tbody.appendChild(tr);
  });
}

// Add goal modal
function openAddGoalModal() {
  document.getElementById("modal-goal-title").value    = "";
  document.getElementById("modal-goal-deadline").value = "";
  openModal("add-goal-modal");
}

async function submitAddGoal() {
  const title    = document.getElementById("modal-goal-title").value.trim();
  const deadline = document.getElementById("modal-goal-deadline").value;
  if (!title)    return toast("Enter a goal title", "err");
  if (!deadline) return toast("Pick a deadline", "err");

  const goal = await api("/api/goals", "POST", { title, deadline });
  if (goal.error) return toast(goal.error, "err");

  state.goals.push(goal);
  closeModal("add-goal-modal");
  renderGoalsTable();
  await loadAnalytics();
  toast("Goal added");
}

// Edit goal panel
function openEditGoal(goalId) {
  const g = state.goals.find(x => x.id === goalId);
  if (!g) return;
  document.getElementById("edit-goal-id").value         = g.id;
  document.getElementById("edit-goal-title").value      = g.title;
  document.getElementById("edit-goal-deadline").value   = g.deadline;
  document.getElementById("edit-panel-title").textContent = "Edit Goal";
  document.getElementById("goal-edit-panel").style.display = "block";
}

function closeEditPanel() {
  document.getElementById("goal-edit-panel").style.display = "none";
}

async function saveGoalEdit() {
  const id       = parseInt(document.getElementById("edit-goal-id").value);
  const title    = document.getElementById("edit-goal-title").value.trim();
  const deadline = document.getElementById("edit-goal-deadline").value;
  if (!title)    return toast("Enter a title", "err");
  if (!deadline) return toast("Pick a deadline", "err");

  const updated = await api(`/api/goals/${id}`, "PUT", { title, deadline });
  if (updated.error) return toast(updated.error, "err");

  const idx = state.goals.findIndex(g => g.id === id);
  if (idx >= 0) state.goals[idx] = updated;
  closeEditPanel();
  renderGoalsTable();
  await loadAnalytics();
  toast("Goal updated");
}

function confirmDeleteGoal(id, title) {
  showConfirm(
    "Delete Goal",
    `Delete "${title}"? This action cannot be undone and will remove all its tasks.`,
    async () => {
      const res = await api(`/api/goals/${id}`, "DELETE");
      if (res.error) return toast(res.error, "err");
      state.goals = state.goals.filter(g => g.id !== id);
      renderGoalsTable();
      await loadAnalytics();
      toast("Goal deleted");
    }
  );
}

function confirmMarkGoalComplete(id, title) {
  showConfirm(
    "Mark Goal Complete",
    `Mark "${title}" as completed? All its tasks will be checked off.`,
    async () => {
      const updated = await api(`/api/goals/${id}/complete`, "POST");
      if (updated.error) return toast(updated.error, "err");
      const idx = state.goals.findIndex(g => g.id === id);
      if (idx >= 0) state.goals[idx] = updated;
      renderGoalsTable();
      await loadAnalytics();
      toast("Goal marked complete");
    }
  );
}

// ─── Tasks CRUD ───────────────────────────────────────────────
function renderGoalSelector() {
  const sel = document.getElementById("goal-selector");
  if (!sel) return;
  sel.innerHTML = "";
  if (!state.goals.length) {
    sel.innerHTML = '<div class="text-muted">No goals found.</div>';
    return;
  }
  state.goals.forEach(g => {
    const item = el("div", "goal-selector-item" + (g.id === state.selectedGoalId ? " selected" : ""));
    item.textContent = g.title;
    item.addEventListener("click", () => selectGoal(g.id));
    sel.appendChild(item);
  });

  // Auto-select first if none selected
  if (!state.selectedGoalId && state.goals.length) selectGoal(state.goals[0].id);
}

async function selectGoal(goalId) {
  state.selectedGoalId = goalId;

  // Update selector highlight
  document.querySelectorAll(".goal-selector-item").forEach((item, i) => {
    item.classList.toggle("selected", state.goals[i]?.id === goalId);
  });

  const g = state.goals.find(x => x.id === goalId);
  if (g) setText("tasks-goal-title", g.title);

  document.getElementById("add-task-btn").style.display = "inline-flex";
  await renderTaskList(goalId);
}

async function renderTaskList(goalId) {
  const tasks = await api(`/api/goals/${goalId}/tasks`);
  const list  = document.getElementById("task-list");
  list.innerHTML = "";

  if (!tasks.length) {
    list.innerHTML = '<div class="text-muted">No tasks yet. Click "+ Add Task" to add one.</div>';
    return;
  }

  tasks.forEach(t => {
    const row = el("div", "task-row" + (t.status === "completed" ? " task-done" : ""));
    row.dataset.taskId = t.id;

    const check = el("div", "task-check" + (t.status === "completed" ? " checked" : ""));
    check.innerHTML = t.status === "completed" ? "&#10003;" : "";
    check.title = "Toggle complete";
    check.addEventListener("click", () => toggleTask(goalId, t.id, row, check));

    const textSpan = el("div", "task-text");
    textSpan.textContent = t.task;

    const actions = el("div", "action-row");

    const editBtn = el("button", "btn btn-ghost btn-sm btn-icon");
    editBtn.title = "Edit";
    editBtn.innerHTML = "&#9998;";
    editBtn.addEventListener("click", () => startEditTask(goalId, t.id, textSpan, editBtn));

    const delBtn = el("button", "btn btn-danger btn-sm btn-icon");
    delBtn.title = "Delete";
    delBtn.innerHTML = "&#128465;";
    delBtn.addEventListener("click", () => deleteTaskUI(goalId, t.id, row));

    actions.append(editBtn, delBtn);
    row.append(check, textSpan, actions);
    list.appendChild(row);
  });
}

async function toggleTask(goalId, taskId, rowEl, checkEl) {
  const res = await api(`/api/goals/${goalId}/tasks/${taskId}/toggle`, "POST");
  if (res.error) return toast(res.error, "err");
  const done = res.status === "completed";
  rowEl.classList.toggle("task-done", done);
  checkEl.classList.toggle("checked", done);
  checkEl.innerHTML = done ? "&#10003;" : "";
  rowEl.querySelector(".task-text").style.textDecoration = done ? "line-through" : "";
  // Update goal progress in state
  await refreshGoalInState(goalId);
  await loadAnalytics();
}

async function deleteTaskUI(goalId, taskId, rowEl) {
  const res = await api(`/api/goals/${goalId}/tasks/${taskId}`, "DELETE");
  if (res.error) return toast(res.error, "err");
  rowEl.remove();
  await refreshGoalInState(goalId);
  await loadAnalytics();
  toast("Task deleted");
}

function startEditTask(goalId, taskId, textEl, editBtn) {
  const orig = textEl.textContent;
  const input = el("input", "task-edit-input");
  input.value = orig;
  textEl.replaceWith(input);
  input.focus();

  const save = async () => {
    const newText = input.value.trim();
    if (!newText) { input.replaceWith(textEl); return; }
    const res = await api(`/api/goals/${goalId}/tasks/${taskId}`, "PUT", { task: newText });
    textEl.textContent = res.task || newText;
    input.replaceWith(textEl);
  };

  input.addEventListener("blur", save);
  input.addEventListener("keydown", e => { if (e.key === "Enter") save(); if (e.key === "Escape") { input.replaceWith(textEl); } });
}

function showAddTask() {
  const form = document.getElementById("add-task-form");
  form.style.display = "flex";
  document.getElementById("new-task-input").focus();
}

function hideAddTask() {
  document.getElementById("add-task-form").style.display = "none";
  document.getElementById("new-task-input").value = "";
}

async function submitAddTask() {
  const text = document.getElementById("new-task-input").value.trim();
  if (!text) return toast("Enter task text", "err");
  const res = await api(`/api/goals/${state.selectedGoalId}/tasks`, "POST", { task: text });
  if (res.error) return toast(res.error, "err");
  hideAddTask();
  await renderTaskList(state.selectedGoalId);
  await refreshGoalInState(state.selectedGoalId);
  await loadAnalytics();
  toast("Task added");
}

async function refreshGoalInState(goalId) {
  const updated = await api("/api/goals");
  state.goals = updated;
}

// ─── Analytics ────────────────────────────────────────────────
function renderAnalyticsPage() {
  const a = state.analytics;
  if (!a) return;

  setText("a-total-hours", a.total_hours + "h");
  setText("a-most-urgent",  a.most_urgent || "None");
  setText("a-mood",         a.mood || "—");

  renderBarChart("analytics-bar-chart", a.log_chart || []);

  // Goal breakdown table
  const container = document.getElementById("analytics-goals-table");
  if (!container) return;
  container.innerHTML = "";

  if (!a.goals || !a.goals.length) {
    container.innerHTML = '<div class="text-muted">No goals found.</div>';
    return;
  }

  a.goals.forEach(g => {
    const row = el("div", "goal-analytics-row");
    row.innerHTML = `
      <div>
        <div style="font-weight:700;font-size:0.875rem">${esc(g.title)}</div>
        <div style="font-size:0.75rem;color:var(--ink-muted);margin-top:2px">Deadline: ${g.deadline}</div>
      </div>
      <span class="badge badge-${g.priority}">${g.priority}</span>
      <div style="min-width:140px">
        <div style="font-size:0.7rem;color:var(--ink-muted);margin-bottom:4px">${g.progress}% complete &nbsp;(${g.tasks_done}/${g.total_tasks} tasks)</div>
        <div class="progress-bar"><div class="progress-fill" style="width:${g.progress}%"></div></div>
      </div>
      <div style="font-size:0.82rem;font-weight:700;color:${g.days_left < 0 ? "var(--warn)" : "var(--ink-muted)"}">
        ${g.days_left < 0 ? "Overdue" : g.days_left + "d left"}
      </div>`;
    container.appendChild(row);
  });
}

// ─── Chat ─────────────────────────────────────────────────────
function bindChat() {
  const input = document.getElementById("chat-input");
  const btn   = document.getElementById("chat-send");
  if (!input || !btn) return;

  btn.addEventListener("click", sendChat);
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });
  input.addEventListener("input", function () {
    this.style.height = "40px";
    this.style.height = Math.min(this.scrollHeight, 100) + "px";
  });

  // Welcome message
  setTimeout(() => addMessage(
    "PLAN: Initialize AI Second Brain agent.\n" +
    "REASON: User has opened the chat interface.\n" +
    "ACTION: Provide a concise orientation.\n" +
    "FINAL ANSWER:\n\n" +
    "Welcome. I am your AI productivity agent.\n\n" +
    "You can ask me to:\n" +
    "  — Generate a study plan or weekly schedule\n" +
    "  — Create a knowledge quiz for any goal\n" +
    "  — Tell you what to focus on today\n" +
    "  — Reflect on your week\n" +
    "  — Log study hours or update your mood\n\n" +
    "Type a message or use the quick prompts on the right.",
    "agent"
  ), 400);
}

async function sendChat() {
  const input = document.getElementById("chat-input");
  const text  = input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";
  input.style.height = "40px";
  setChatLoading(true);

  try {
    const res = await api("/api/chat", "POST", { message: text });
    addMessage(res.response || "No response.", "agent");

    // Refresh data after side-effectful intents
    const refreshIntents = ["log_hours", "update_mood", "add_task", "add_goal"];
    if (refreshIntents.includes(res.intent)) {
      await loadAll();
      toast("Data updated");
    }
  } catch (e) {
    addMessage("Network error. Is the Flask server running on port 5000?", "agent");
  }

  setChatLoading(false);
}

function sendPrompt(text) {
  navigate("chat");
  setTimeout(() => {
    document.getElementById("chat-input").value = text;
    sendChat();
  }, 50);
}

function addMessage(content, role) {
  const indicator = document.getElementById("typing-indicator");
  indicator.classList.add("hidden");

  const area = document.getElementById("messages-area");
  const div  = el("div", "message " + role);

  const avatar = el("div", "msg-avatar");
  avatar.textContent = role === "user" ? "U" : "AI";

  const bubble = el("div", "msg-bubble");
  bubble.innerHTML = formatResponse(content);

  div.append(avatar, bubble);

  // Insert before typing indicator
  area.insertBefore(div, indicator);
  area.scrollTop = area.scrollHeight;
}

function formatResponse(text) {
  return esc(text)
    .replace(/^PLAN:/gm,         '<span class="rsp-plan">PLAN</span><span class="rsp-sep"></span>')
    .replace(/^REASON:/gm,       '<span class="rsp-reason">REASON</span><span class="rsp-sep"></span>')
    .replace(/^ACTION:/gm,       '<span class="rsp-action">ACTION</span><span class="rsp-sep"></span>')
    .replace(/^FINAL ANSWER:/gm, '<span class="rsp-answer">FINAL ANSWER</span><span class="rsp-sep"></span>');
}

function setChatLoading(on) {
  const indicator = document.getElementById("typing-indicator");
  const btn       = document.getElementById("chat-send");
  const input     = document.getElementById("chat-input");
  indicator.classList.toggle("hidden", !on);
  btn.disabled   = on;
  input.disabled = on;
  if (on) {
    const area = document.getElementById("messages-area");
    area.scrollTop = area.scrollHeight;
  }
}

// ─── Modal ────────────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.add("open");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

function showConfirm(title, body, onOk) {
  document.getElementById("confirm-title").textContent = title;
  document.getElementById("confirm-body").textContent  = body;
  const btn = document.getElementById("confirm-ok-btn");
  btn.onclick = () => { closeModal("confirm-modal"); onOk(); };
  openModal("confirm-modal");
}

// Close modal on overlay click
document.addEventListener("click", e => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("open");
  }
});

// ─── Toast ────────────────────────────────────────────────────
let _toastTimer = null;
function toast(msg, type = "ok") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className   = "toast show toast-" + type;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
}

// ─── Utilities ────────────────────────────────────────────────
function el(tag, cls = "") {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

function setText(id, val) {
  const e = document.getElementById(id);
  if (e) e.textContent = val;
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
