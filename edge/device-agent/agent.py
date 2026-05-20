from __future__ import annotations

import json
import urllib.request


API = "http://localhost:8080"


def post(path: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        print(res.read().decode("utf-8"))


def main() -> None:
    print("Yiban device-agent simulator")
    print("Commands: p=toggle presence, m=toggle mic, q=quit")
    presence = False
    mic_muted = False
    while True:
        command = input("> ").strip().lower()
        if command == "q":
            return
        if command == "p":
            presence = not presence
            post("/api/device/presence", {"presence": presence})
        elif command == "m":
            mic_muted = not mic_muted
            post("/api/device/mic-muted", {"micMuted": mic_muted})
        else:
            print("Unknown command")


if __name__ == "__main__":
    main()

