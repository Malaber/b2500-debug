# Fake Shelly 3EM

Small test double for AstraMeter. It exposes the Shelly Pro 3EM RPC endpoint
that AstraMeter reads and lets you control the reported grid power with a web
slider or API call.

Positive watts mean house import/load. Negative watts mean export/surplus.

## Run directly

```bash
python3 app.py --host 0.0.0.0 --port 18080
```

Open:

```text
http://SERVER_IP:18080/
```

## Run with Docker Compose

```bash
docker compose up -d --build
```

## API

```bash
curl "http://127.0.0.1:18080/set?power=600"
curl "http://127.0.0.1:18080/rpc/EM.GetStatus?id=0"
curl -X POST "http://127.0.0.1:18080/api/state" \
  -H "Content-Type: application/json" \
  -d '{"power":1200}'
```

## AstraMeter config

Because your AstraMeter container uses `network_mode: host`, point its Shelly
source at the fake meter on the host:

```ini
[SHELLY]
TYPE = 3EMPro
IP = 127.0.0.1:18080
USER =
PASS =
METER_INDEX = meter1
POWER_OFFSET = 0
POWER_MULTIPLIER = 1
```

Then restart AstraMeter and move the slider to clear values such as `600 W`,
`1200 W`, `0 W`, and `-500 W`.

Expected first test:

1. Set `+600 W`.
2. AstraMeter logs should show a positive meter value around `600W`.
3. B2500 output should ramp up over several poll cycles.
4. Set `0 W`.
5. B2500 output should ramp down.
6. Set `-500 W`.
7. B2500 should not discharge for that surplus signal.
