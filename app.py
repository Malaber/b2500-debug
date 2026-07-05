#!/usr/bin/env python3
"""Controllable Shelly Pro 3EM test double for AstraMeter."""

from __future__ import annotations

import argparse
import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_STATE_PATH = Path("state.json")
POWER_MIN = -2500
POWER_MAX = 2500


class MeterState:
    def __init__(self, path: Path, initial_power: int) -> None:
        self.path = path
        self.power = initial_power
        self.updated_at = time.time()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.set_power(int(data.get("power", self.power)), persist=False)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.save()

    def save(self) -> None:
        payload = {"power": self.power, "updated_at": self.updated_at}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def set_power(self, power: int, persist: bool = True) -> None:
        self.power = max(POWER_MIN, min(POWER_MAX, int(power)))
        self.updated_at = time.time()
        if persist:
            self.save()

    def as_dict(self) -> dict[str, object]:
        phase_power = split_three_phases(self.power)
        return {
            "power": self.power,
            "phases": phase_power,
            "updated_at": self.updated_at,
        }


def split_three_phases(total: int) -> list[int]:
    base = int(total / 3)
    phases = [base, base, base]
    remainder = total - sum(phases)
    step = 1 if remainder >= 0 else -1
    for index in range(abs(remainder)):
        phases[index % 3] += step
    return phases


def shelly_em_status(state: MeterState) -> dict[str, object]:
    phases = split_three_phases(state.power)
    now = int(time.time())
    return {
        "id": 0,
        "a_current": abs(phases[0]) / 230,
        "a_voltage": 230,
        "a_act_power": phases[0],
        "b_current": abs(phases[1]) / 230,
        "b_voltage": 230,
        "b_act_power": phases[1],
        "c_current": abs(phases[2]) / 230,
        "c_voltage": 230,
        "c_act_power": phases[2],
        "total_current": sum(abs(phase) for phase in phases) / 230,
        "total_act_power": state.power,
        "total_aprt_power": abs(state.power),
        "total_pf": 1,
        "freq": 50,
        "errors": [],
        "ts": now,
    }


def shelly_get_status(state: MeterState) -> dict[str, object]:
    return {
        "ble": {},
        "cloud": {"connected": False},
        "em:0": shelly_em_status(state),
        "mqtt": {"connected": False},
        "sys": {
            "mac": "A8A8A8TEST3EM",
            "restart_required": False,
            "time": time.strftime("%H:%M", time.localtime()),
            "unixtime": int(time.time()),
            "uptime": int(time.monotonic()),
        },
        "wifi": {"sta_ip": "127.0.0.1", "status": "got ip"},
    }


def legacy_status(state: MeterState) -> dict[str, object]:
    phases = split_three_phases(state.power)
    return {
        "wifi_sta": {"connected": True, "ip": "127.0.0.1"},
        "emeters": [
            {"power": phases[0], "pf": 1, "voltage": 230, "current": abs(phases[0]) / 230},
            {"power": phases[1], "pf": 1, "voltage": 230, "current": abs(phases[1]) / 230},
            {"power": phases[2], "pf": 1, "voltage": 230, "current": abs(phases[2]) / 230},
        ],
        "total_power": state.power,
    }


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fake Shelly 3EM</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f7f9;
      color: #17191f;
    }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
    }
    main {
      width: min(760px, calc(100vw - 32px));
      display: grid;
      gap: 22px;
    }
    .panel {
      background: #ffffff;
      border: 1px solid #dce0e7;
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 18px 50px rgba(24, 33, 52, 0.08);
    }
    h1 {
      margin: 0 0 6px;
      font-size: clamp(28px, 5vw, 46px);
      letter-spacing: 0;
    }
    p {
      margin: 0;
      color: #5d6472;
      line-height: 1.5;
    }
    .meter {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin: 22px 0;
    }
    .value {
      font-size: clamp(46px, 12vw, 86px);
      font-weight: 750;
      letter-spacing: 0;
      line-height: 1;
    }
    .mode {
      font-size: 18px;
      color: #5d6472;
      white-space: nowrap;
    }
    input[type="range"] {
      width: 100%;
      accent-color: #14796f;
    }
    .row {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 18px;
    }
    input[type="number"] {
      width: 140px;
      padding: 10px 12px;
      border: 1px solid #cdd3dd;
      border-radius: 6px;
      font: inherit;
      background: #ffffff;
      color: inherit;
    }
    button {
      border: 1px solid #cdd3dd;
      background: #ffffff;
      color: #17191f;
      border-radius: 6px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
    }
    button.primary {
      border-color: #14796f;
      background: #14796f;
      color: white;
    }
    code {
      display: block;
      overflow-wrap: anywhere;
      background: #eef1f5;
      border-radius: 6px;
      padding: 10px 12px;
      color: #303744;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        background: #101217;
        color: #f4f5f7;
      }
      .panel {
        background: #191d25;
        border-color: #303644;
        box-shadow: none;
      }
      p, .mode {
        color: #a9b1c0;
      }
      input[type="number"], button {
        background: #202632;
        border-color: #3a4353;
        color: #f4f5f7;
      }
      code {
        background: #121720;
        color: #dbe1ec;
      }
    }
  </style>
</head>
<body>
  <main>
    <section class="panel">
      <h1>Fake Shelly 3EM</h1>
      <p>Positive watts simulate house import/load. Negative watts simulate export/surplus.</p>
      <div class="meter">
        <div class="value"><span id="power">0</span> W</div>
        <div class="mode" id="mode">neutral</div>
      </div>
      <input id="slider" type="range" min="-2500" max="2500" step="10" value="0">
      <div class="row">
        <input id="number" type="number" min="-2500" max="2500" step="10" value="0" aria-label="Power in watts">
        <button class="primary" data-power="600">+600 W</button>
        <button data-power="1200">+1200 W</button>
        <button data-power="0">0 W</button>
        <button data-power="-500">-500 W</button>
      </div>
    </section>
    <section class="panel">
      <p>AstraMeter Shelly endpoint</p>
      <code id="endpoint"></code>
    </section>
  </main>
  <script>
    const slider = document.getElementById("slider");
    const number = document.getElementById("number");
    const power = document.getElementById("power");
    const mode = document.getElementById("mode");
    const endpoint = document.getElementById("endpoint");
    let pending;

    endpoint.textContent = `${location.origin}/rpc/EM.GetStatus?id=0`;

    function render(value) {
      slider.value = value;
      number.value = value;
      power.textContent = value;
      mode.textContent = value > 0 ? "import / load" : value < 0 ? "export / surplus" : "neutral";
    }

    async function setPower(value) {
      const clean = Math.max(-2500, Math.min(2500, Number.parseInt(value || 0, 10)));
      render(clean);
      clearTimeout(pending);
      pending = setTimeout(async () => {
        const response = await fetch("/api/state", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({power: clean})
        });
        const data = await response.json();
        render(data.power);
      }, 120);
    }

    slider.addEventListener("input", event => setPower(event.target.value));
    number.addEventListener("change", event => setPower(event.target.value));
    document.querySelectorAll("button[data-power]").forEach(button => {
      button.addEventListener("click", () => setPower(button.dataset.power));
    });

    fetch("/api/state").then(response => response.json()).then(data => render(data.power));
  </script>
</body>
</html>
"""


class FakeShellyHandler(BaseHTTPRequestHandler):
    server_version = "FakeShelly3EM/1.0"

    @property
    def meter_state(self) -> MeterState:
        return self.server.meter_state  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/":
            self.send_html(INDEX_HTML)
            return
        if path == "/api/state":
            self.send_json(self.meter_state.as_dict())
            return
        if path == "/set":
            self.set_power_from_query(query)
            return
        if path == "/rpc/EM.GetStatus":
            self.send_json(shelly_em_status(self.meter_state))
            return
        if path == "/rpc/Shelly.GetStatus":
            self.send_json(shelly_get_status(self.meter_state))
            return
        if path == "/status":
            self.send_json(legacy_status(self.meter_state))
            return
        if path.startswith("/emeter/"):
            self.send_legacy_emeter(path)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") != "/api/state":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body)
            self.meter_state.set_power(int(payload["power"]))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected JSON body like {\"power\": 600}")
            return
        self.send_json(self.meter_state.as_dict())

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {self.client_address[0]} {fmt % args}")

    def set_power_from_query(self, query: dict[str, list[str]]) -> None:
        try:
            power = int(query.get("power", [""])[0])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected /set?power=600")
            return
        self.meter_state.set_power(power)
        self.send_json(self.meter_state.as_dict())

    def send_legacy_emeter(self, path: str) -> None:
        try:
            index = int(path.rsplit("/", 1)[1])
            phase = split_three_phases(self.meter_state.power)[index]
        except (IndexError, ValueError):
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self.send_json({"power": phase, "pf": 1, "voltage": 230, "current": abs(phase) / 230})

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, payload: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Controllable Shelly Pro 3EM test double")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--initial-power", type=int, default=0)
    args = parser.parse_args()

    state = MeterState(args.state, args.initial_power)
    server = ThreadingHTTPServer((args.host, args.port), FakeShellyHandler)
    server.meter_state = state  # type: ignore[attr-defined]
    print(f"Fake Shelly 3EM listening on http://{args.host}:{args.port}")
    print(f"Current test power: {state.power} W")
    server.serve_forever()


if __name__ == "__main__":
    main()
