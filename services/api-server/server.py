from __future__ import annotations

import json
import mimetypes
import os
import posixpath
import re
import sys
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(
    os.environ.get(
        "YIBAN_DATA_DIR",
        str(Path.home() / ".yiban-memory-frame" / "data"),
    )
)
STATIC_DIRS = {
    "/device": ROOT / "apps" / "device-ui",
    "/family": ROOT / "apps" / "family-web",
}
STATE_PATH = DATA_DIR / "state.json"


DEFAULT_STATE = {
    "family": {
        "id": "family-demo",
        "elderName": "妈妈",
        "deviceName": "忆伴",
    },
    "device": {
        "presence": False,
        "micMuted": False,
        "mode": "idle_album",
        "lastSeenAt": None,
    },
    "photos": [
        {
            "id": "photo-demo-1",
            "title": "公园里的小宝",
            "description": "小宝在公园放风筝，看起来很开心。",
            "imageUrl": "/assets/sample-park.svg",
            "people": ["小宝"],
            "sceneTags": ["公园", "放风筝", "春天"],
            "memoryPrompts": [
                "你还记得小宝第一次放风筝是什么时候吗？",
                "这张照片让你想到谁小时候？",
            ],
            "createdAt": "2026-05-20T10:00:00+08:00",
        },
        {
            "id": "photo-demo-2",
            "title": "过年的全家福",
            "description": "一家人坐在饭桌前，像是春节团圆时拍的照片。",
            "imageUrl": "/assets/sample-family.svg",
            "people": ["妈妈", "女儿", "小宝"],
            "sceneTags": ["春节", "团圆", "家里"],
            "memoryPrompts": [
                "那年过年家里最热闹的事情是什么？",
                "这张照片里你最想跟孩子们说什么？",
            ],
            "createdAt": "2026-05-20T10:05:00+08:00",
        },
    ],
    "messages": [
        {
            "id": "msg-demo-1",
            "from": "女儿",
            "to": "elder",
            "type": "text",
            "content": "妈，今天小宝去公园放风筝了，给你看看。",
            "photoId": "photo-demo-1",
            "createdAt": "2026-05-20T10:10:00+08:00",
            "played": False,
        }
    ],
    "conversations": [],
    "memories": [],
    "summaries": [],
}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def ensure_state() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        save_state(DEFAULT_STATE)


def load_state() -> dict:
    ensure_state()
    with STATE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    temp.replace(STATE_PATH)


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def infer_photo_context(photo: dict | None) -> str:
    if not photo:
        return "这段对话没有绑定具体照片。"
    tags = "、".join(photo.get("sceneTags", [])) or "家庭照片"
    people = "、".join(photo.get("people", [])) or "家人"
    return f"当前照片是《{photo.get('title', '未命名照片')}》，画面里有{people}，场景线索包括{tags}。"


def simple_ai_reply(text: str, photo: dict | None) -> str:
    clean = text.strip()
    if not clean:
        return "我在这里。你想看看这张照片，还是听听孩子们的留言？"
    if any(word in clean for word in ["别发", "别告诉", "不告诉", "不要发"]):
        return "好，这段我只留在相册里，不发给孩子。"
    if any(word in clean for word in ["发给", "告诉", "回一句", "帮我说"]):
        return "好，我可以帮你整理成一句清楚的话，发送前会再问你一遍。"
    if photo:
        prompts = photo.get("memoryPrompts") or []
        prompt = prompts[0] if prompts else "这张照片让你想起了什么？"
        return f"{photo.get('description', '这是一张很有回忆的照片')}。{prompt}"
    return "听起来这是很重要的一段回忆。你愿意多讲一点吗？"


def build_summary(state: dict) -> dict:
    conversations = state.get("conversations", [])[-8:]
    elder_turns = [c for c in conversations if c.get("speaker") == "elder"]
    if not elder_turns:
        body = "今天还没有新的回忆内容。可以给老人发一张照片或一句留言，作为下一次交流的开头。"
        title = "今天还没有新的亲情摘要"
        source_ids = []
    else:
        latest = elder_turns[-1]
        photo = next((p for p in state.get("photos", []) if p.get("id") == latest.get("photoId")), None)
        context = infer_photo_context(photo)
        body = (
            f"{state['family']['elderName']}今天围绕相册说到："
            f"“{latest.get('text', '')}”。{context}"
            "这段内容适合作为一次轻量回应的开头，可以发一条语音接着聊。"
        )
        title = f"{state['family']['elderName']}今天有一段值得回应的回忆"
        source_ids = [latest["id"]]
    summary = {
        "id": make_id("summary"),
        "title": title,
        "body": body,
        "suggestedReplies": [
            "妈，我看到你说的这件事了，晚上我们再聊聊。",
            "这张照片我也很喜欢，你再给我讲讲那时候的事。",
        ],
        "sourceConversationIds": source_ids,
        "createdAt": now_iso(),
    }
    state.setdefault("summaries", []).insert(0, summary)
    return summary


class Handler(BaseHTTPRequestHandler):
    server_version = "YibanMemoryFrame/0.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[%s] %s\n" % (now_iso(), fmt % args))

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.redirect("/device/")
            return
        if parsed.path == "/api/state":
            self.json(load_state())
            return
        if parsed.path.startswith("/assets/"):
            self.serve_asset(parsed.path)
            return
        for prefix, directory in STATIC_DIRS.items():
            if parsed.path == prefix:
                self.redirect(prefix + "/")
                return
            if parsed.path.startswith(prefix + "/"):
                self.serve_static(prefix, directory, parsed.path)
                return
        self.error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self.read_json()
        state = load_state()

        if parsed.path == "/api/photos":
            item = {
                "id": make_id("photo"),
                "title": body.get("title") or "新的家庭照片",
                "description": body.get("description") or "家属新上传了一张照片。",
                "imageUrl": body.get("imageUrl") or "/assets/sample-family.svg",
                "people": split_list(body.get("people", "")),
                "sceneTags": split_list(body.get("sceneTags", "")),
                "memoryPrompts": split_lines(body.get("memoryPrompts", "")),
                "createdAt": now_iso(),
            }
            if not item["memoryPrompts"]:
                item["memoryPrompts"] = ["这张照片让你想起了什么？"]
            state.setdefault("photos", []).insert(0, item)
            save_state(state)
            self.json(item, HTTPStatus.CREATED)
            return

        if parsed.path == "/api/messages":
            item = {
                "id": make_id("msg"),
                "from": body.get("from") or "家人",
                "to": body.get("to") or "elder",
                "type": "text",
                "content": body.get("content") or "",
                "photoId": body.get("photoId") or None,
                "createdAt": now_iso(),
                "played": False,
            }
            state.setdefault("messages", []).insert(0, item)
            save_state(state)
            self.json(item, HTTPStatus.CREATED)
            return

        if parsed.path == "/api/conversations":
            photo_id = body.get("photoId")
            photo = next((p for p in state.get("photos", []) if p.get("id") == photo_id), None)
            elder_turn = {
                "id": make_id("turn"),
                "speaker": "elder",
                "text": body.get("text") or "",
                "photoId": photo_id,
                "sharePolicy": "local_only" if re.search(r"别发|别告诉|不告诉|不要发", body.get("text") or "") else "summary_allowed",
                "createdAt": now_iso(),
            }
            ai_turn = {
                "id": make_id("turn"),
                "speaker": "ai",
                "text": simple_ai_reply(elder_turn["text"], photo),
                "photoId": photo_id,
                "createdAt": now_iso(),
            }
            state.setdefault("conversations", []).extend([elder_turn, ai_turn])
            if elder_turn["sharePolicy"] == "summary_allowed":
                state.setdefault("memories", []).insert(
                    0,
                    {
                        "id": make_id("memory"),
                        "sourceConversationId": elder_turn["id"],
                        "photoId": photo_id,
                        "content": elder_turn["text"],
                        "emotionTags": [],
                        "sharePolicy": elder_turn["sharePolicy"],
                        "createdAt": now_iso(),
                    },
                )
            save_state(state)
            self.json({"elder": elder_turn, "ai": ai_turn}, HTTPStatus.CREATED)
            return

        if parsed.path == "/api/summaries/generate":
            summary = build_summary(state)
            save_state(state)
            self.json(summary, HTTPStatus.CREATED)
            return

        if parsed.path == "/api/device/presence":
            state["device"]["presence"] = bool(body.get("presence"))
            state["device"]["mode"] = "face_to_face_ready" if state["device"]["presence"] else "idle_album"
            state["device"]["lastSeenAt"] = now_iso()
            save_state(state)
            self.json(state["device"])
            return

        if parsed.path == "/api/device/mic-muted":
            state["device"]["micMuted"] = bool(body.get("micMuted"))
            state["device"]["mode"] = "mic_muted" if state["device"]["micMuted"] else "idle_album"
            save_state(state)
            self.json(state["device"])
            return

        self.error(HTTPStatus.NOT_FOUND, "Not found")

    def redirect(self, target: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", target)
        self.end_headers()

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def error(self, status: HTTPStatus, message: str) -> None:
        self.json({"error": message}, status)

    def send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def serve_static(self, prefix: str, directory: Path, request_path: str) -> None:
        rel = request_path[len(prefix) :].lstrip("/")
        if not rel:
            rel = "index.html"
        rel = posixpath.normpath(unquote(rel))
        if rel.startswith("../"):
            self.error(HTTPStatus.BAD_REQUEST, "Invalid path")
            return
        path = directory / rel
        if path.is_dir():
            path = path / "index.html"
        if not path.exists():
            path = directory / "index.html"
        self.send_file(path)

    def serve_asset(self, request_path: str) -> None:
        name = Path(request_path).name
        if name == "sample-park.svg":
            self.svg("公园", "#4c9f70", "#f6d365")
            return
        if name == "sample-family.svg":
            self.svg("团圆", "#7c5c9e", "#f4a261")
            return
        self.error(HTTPStatus.NOT_FOUND, "Asset not found")

    def send_file(self, path: Path) -> None:
        if not path.exists():
            self.error(HTTPStatus.NOT_FOUND, "Not found")
            return
        data = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix in {".html", ".css", ".js"}:
            ctype += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def svg(self, label: str, color_a: str, color_b: str) -> None:
        data = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">
<rect width="1200" height="800" fill="{color_a}"/>
<circle cx="980" cy="170" r="120" fill="{color_b}" opacity=".85"/>
<rect x="110" y="120" width="980" height="560" rx="28" fill="#fff7" stroke="#fff" stroke-width="8"/>
<text x="600" y="405" text-anchor="middle" font-family="Arial,'Microsoft YaHei',sans-serif" font-size="88" fill="#fff">{label}</text>
<text x="600" y="485" text-anchor="middle" font-family="Arial,'Microsoft YaHei',sans-serif" font-size="34" fill="#fff" opacity=".9">Yiban Memory Frame</text>
</svg>""".encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def split_list(value: str | list) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [item.strip() for item in re.split(r"[,，、\s]+", str(value)) if item.strip()]


def split_lines(value: str | list) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def main() -> None:
    ensure_state()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Yiban Memory Frame server running at http://{host}:{port}")
    print("Device UI: http://localhost:8080/device/")
    print("Family UI: http://localhost:8080/family/")
    server.serve_forever()


if __name__ == "__main__":
    main()
