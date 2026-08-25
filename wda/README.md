# `wda/` — the signed WebDriverAgent build

This is a **pre-built, pre-signed** WebDriverAgent. It is committed on purpose so
that cloning this repo is enough to drive a device — you do **not** need Xcode to
build WDA, an Appium install, or the `sudoku-automation` repo it used to come from.

`scripts/wda.sh` finds it here automatically. Nothing else reads it.

```
wda/
├── WebDriverAgentRunner_iphoneos26.5-arm64.xctestrun   the test plan xcodebuild runs
└── Debug-iphoneos/
    ├── WebDriverAgentLib.framework/
    └── WebDriverAgentRunner-Runner.app/                the signed app that lands on the phone
```

The `.xctestrun` refers to its products with the relocatable tokens `__TESTROOT__`
and `__TESTHOST__` — never absolute paths — which is why the whole tree can be moved
into a repo and still work. `__TESTROOT__` resolves to the directory holding the
`.xctestrun`, i.e. `wda/` itself. **Do not flatten or rearrange this layout.**

## What it still needs from you

Committing the build removes the *build* step. It does not remove these:

- **Xcode.** `scripts/wda.sh` launches it with `xcodebuild test-without-building`.
  The build was made with **Xcode 26.5** against the **iOS 26.4** SDK.
- **A provisioned device.** See the list below.
- **Trust on the phone.** Settings → General → VPN & Device Management → trust the
  developer certificate, once per device.
- **No rival WebDriverAgent.** iOS refuses to replace a `WebDriverAgentRunner` signed
  by a *different* team. Remove it first:
  `xcrun devicectl device uninstall app --device <UDID> com.facebook.WebDriverAgentRunner.xctrunner`

## It only installs on these 9 devices

The device list is baked into `embedded.mobileprovision` at signing time. A device
that is not in this list **cannot** run this build, no matter what you do on the Mac.

| UDID | Device |
|---|---|
| `00008030-001C51DA0E80A02E` | iPhone 11 — Farooq's iPhone |
| `385e82401ffb88ee946698f951ae9b991beba9da` | iPhone 7 — "Kaala" |
| `00008120-0001485A1E60201E` | iPhone 14 Pro Max |
| `00008140-0009492E1444801C` | iPhone 16 Pro — Hamza's iPhone |
| `00008110-001454DA0E02601E` | (other team device) |
| `00008030-00162C1A0E50202E` | (other team device) |
| `00008122-0009458E1E45801C` | (other team device) |
| `00008130-000578560091401C` | (other team device) |
| `00008120-0006793804A14032` | (other team device) |

Check your own with `idevice_id -l` (USB only) or `tidevice list` (also shows
WiFi-paired devices). Not listed? See **Rebuilding** below.

**The iPhone 7 is a known exception.** `MinimumOSVersion` in this build is 13.0, so on
paper it covers iOS 15.7.5 — but in practice WDA has never launched on that phone under
Xcode 26.5. Use `tidevice` (`launch` + `screenshot`) there instead, as the rest of the
repo already does.

## It expires — around 2 July 2027

Two clocks run, and the earlier one wins:

| | Expires |
|---|---|
| Provisioning profile | **2027-08-12** |
| Signing certificates (Apple Development: Shahab Nadeem) | 2027-07-02, 2027-07-29, 2027-07-31 |

So treat **2027-07-02** as the date this stops working. After that, iOS refuses to
launch it and the only fix is a rebuild.

## Rebuilding (unprovisioned device, or after expiry)

You need membership of Apple Developer team **`4528523FZZ`** (USERWISE SERVICES LLC)
with a signing certificate. The WebDriverAgent Xcode project itself comes from Appium,
not from any repo here:

1. Install Node, then Appium and its XCUITest driver. That puts
   `WebDriverAgent.xcodeproj` under `~/.appium/node_modules/appium-webdriveragent/`.
2. Build and sign it with `DEVELOPMENT_TEAM=4528523FZZ` and
   `-allowProvisioningUpdates -allowProvisioningDeviceRegistration` — the second flag is
   what adds a new phone to the profile. `~/sudoku-automation/scripts/airtest-wda.sh` does
   exactly this if you have that repo.
3. Copy the resulting `Build/Products/` over this directory, replacing it, and commit.
   Keep the layout identical.

Full context and the surrounding setup steps are in [`../SETUP.md`](../SETUP.md) →
*Rebuilding WebDriverAgent*.

## A note on what is committed here

`embedded.mobileprovision` contains the team identifier, the 9 device UDIDs above, and
the team's **public** certificates. It contains **no private key** — you cannot sign
anything with it. This repo is private; the list is recorded here so nobody has to
discover it by accident.
