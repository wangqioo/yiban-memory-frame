# Device Agent

RK3576 local agent placeholder.

The MVP web server can already simulate presence and microphone state. This agent is the future hardware bridge for:

- GPIO / UART presence sensor
- physical microphone mute key
- status LED
- Chromium kiosk startup
- local watchdog

Run the simulator:

```bash
python edge/device-agent/agent.py
```

