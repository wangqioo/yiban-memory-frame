const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${path} failed`);
  return res.json();
}

function values(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function load() {
  const state = await api("/api/state");
  renderSummaries(state.summaries || []);
  renderConversations(state.conversations || []);
}

function renderSummaries(items) {
  $("summaries").innerHTML = items.length
    ? items
        .map(
          (item) => `
        <article class="card">
          <strong>${escapeHtml(item.title)}</strong>
          <div>${escapeHtml(item.body)}</div>
          <div class="meta">${escapeHtml(item.createdAt)}</div>
        </article>`
        )
        .join("")
    : `<div class="card">还没有摘要。可以先在老人端模拟一段对话。</div>`;
}

function renderConversations(items) {
  $("conversations").innerHTML = items.length
    ? [...items]
        .reverse()
        .slice(0, 12)
        .map(
          (item) => `
        <article class="card">
          <strong>${item.speaker === "elder" ? "老人" : "忆伴"}</strong>
          <div>${escapeHtml(item.text)}</div>
          <div class="meta">${escapeHtml(item.createdAt)}</div>
        </article>`
        )
        .join("")
    : `<div class="card">暂无对话。</div>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

$("messageForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/messages", { method: "POST", body: JSON.stringify(values(event.target)) });
  event.target.content.value = "";
  await load();
});

$("photoForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/photos", { method: "POST", body: JSON.stringify(values(event.target)) });
  event.target.reset();
  await load();
});

$("summaryBtn").addEventListener("click", async () => {
  await api("/api/summaries/generate", { method: "POST", body: "{}" });
  await load();
});

setInterval(load, 5000);
load();

