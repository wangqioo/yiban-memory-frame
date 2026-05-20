const state = {
  data: null,
  photoIndex: 0,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${path} failed`);
  return res.json();
}

async function load() {
  state.data = await api("/api/state");
  render();
}

function currentPhoto() {
  const photos = state.data?.photos || [];
  if (!photos.length) return null;
  return photos[state.photoIndex % photos.length];
}

function renderClock() {
  const now = new Date();
  $("time").textContent = now.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  $("date").textContent = now.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });
}

function render() {
  if (!state.data) return;
  renderClock();
  const photo = currentPhoto();
  if (photo) {
    $("photo").src = photo.imageUrl;
    $("photoTitle").textContent = photo.title;
    $("photoDesc").textContent = photo.description;
  }
  const device = state.data.device;
  $("status").textContent = device.micMuted ? "麦克风已关" : device.presence ? "面对面陪伴" : "相册模式";
  $("presence").textContent = device.presence ? "已进入面对面陪伴，可以直接说话。" : "未检测到面对面。";
  $("presenceBtn").textContent = device.presence ? "离开相册前" : "坐到相册前";
  $("micBtn").textContent = device.micMuted ? "打开麦克风" : "关闭麦克风";
  $("micBtn").classList.toggle("secondary", device.micMuted);
  const msg = (state.data.messages || [])[0];
  $("message").textContent = msg ? `${msg.from}：${msg.content}` : "暂无新留言";
  const lastAi = [...(state.data.conversations || [])].reverse().find((item) => item.speaker === "ai");
  $("aiReply").textContent = lastAi ? lastAi.text : "坐到相册前，可以直接说话。";
}

async function togglePresence() {
  const presence = !state.data.device.presence;
  state.data.device = await api("/api/device/presence", {
    method: "POST",
    body: JSON.stringify({ presence }),
  });
  render();
}

async function toggleMic() {
  const micMuted = !state.data.device.micMuted;
  state.data.device = await api("/api/device/mic-muted", {
    method: "POST",
    body: JSON.stringify({ micMuted }),
  });
  render();
}

async function submitTalk(event) {
  event.preventDefault();
  const input = $("talkInput");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  const photo = currentPhoto();
  const result = await api("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ text, photoId: photo?.id }),
  });
  state.data.conversations.push(result.elder, result.ai);
  render();
}

function rotatePhoto() {
  const photos = state.data?.photos || [];
  if (photos.length > 1 && !state.data.device.presence) {
    state.photoIndex = (state.photoIndex + 1) % photos.length;
    render();
  }
}

$("presenceBtn").addEventListener("click", togglePresence);
$("micBtn").addEventListener("click", toggleMic);
$("talkForm").addEventListener("submit", submitTalk);

setInterval(renderClock, 1000);
setInterval(rotatePhoto, 9000);
setInterval(load, 5000);
load();

