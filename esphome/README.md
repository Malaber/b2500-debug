# ESPHome B2500 Recovery Gateways

These configs are meant to be copied into:

```text
/srv/docker-ansible/homeassistant/esphome/config/
```

They follow the existing local package style:

- `common/base.yaml` keeps OTA, native API, captive portal, logger, and web UI.
- `common/hw_esp32_s3_devkitc.yaml` targets ESP32-S3 DevKitC-1.
- `common/b2500_gateway_base.yaml` loads `tomquist/esphome-b2500` and BLE.
- `common/b2500_v2_storage.yaml` is a reusable package for one B2500.
- `b2500-attic-1.yaml` is the first two-device gateway.

The WiFi package is intentionally referenced as `common/wifinordkorea.yaml` and
not stored here with a real password.

After flashing, use Home Assistant to check the `Last Response`, output power,
WiFi/MQTT status, adaptive mode, smart meter connection/reading, and reboot
buttons. Use the reboot buttons as recovery only; normal power control should
stay with AstraMeter/CT002.

## CT-follow recovery loop

When AstraMeter logs show a B2500 polling in inspection mode:

```text
phase='0'
consumers ...@0:0
```

use the ESPHome entities for that battery:

1. Press `B2500 n Enable CT Follow`.
2. Watch AstraMeter logs for 60 seconds.
3. If it still reports `phase='0'`, press `B2500 n Force CT Follow Reboot`.
4. After reconnect, the target state is `phase='D'` for whole-home/combined
   three-phase control.

The force button sends the known upstream BLE command
`b2500.set_adaptive_mode_enabled: true`, waits briefly, then reboots the B2500.
It does not write unknown configuration bytes.

The current upstream component exposes B2500-side smart meter state as
`Smart Meter Connected`, `Smart Meter Reading`, and `Adaptive Mode`. It does
not expose the CT device MAC/ID assignment directly, so verify the assignment
by checking that the B2500 smart meter reading matches the AstraMeter/fake
Shelly value and that AstraMeter sees `phase='D'` instead of `phase='0'`.

Fully replacing the Marstek app for CT assignment needs one more reverse-
engineering step: capture the app's write when it assigns a B2500 to a CT and
phase. Once the BLE or cloud/MQTT command payload is known, add it as a proper
ESPHome action instead of using raw/guessed writes.

Initial flashing still needs USB or ESPHome Web Installer. After the first
flash, the shared `common/base.yaml` enables ESPHome OTA and the port-80 web UI,
so later updates are WiFi flashable from the ESPHome dashboard.

If your ESPHome add-on rejects the repeated `!include ... vars:` package syntax
in `b2500-attic-1.yaml`, flatten the two `common/b2500_v2_storage.yaml`
instances into the main YAML. The schema keys in the package file are the part
that matters.
