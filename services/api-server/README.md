# API Server

Zero-dependency MVP backend for Yiban Memory Frame.

Run from the repository root:

```bash
python services/api-server/server.py
```

Default URL:

```text
http://localhost:8080
```

Routes:

- `GET /api/state`
- `POST /api/photos`
- `POST /api/messages`
- `POST /api/conversations`
- `POST /api/summaries/generate`
- `POST /api/device/presence`
- `POST /api/device/mic-muted`

