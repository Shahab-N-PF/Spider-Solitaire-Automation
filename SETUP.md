# Setting this up on a new Mac

Start-to-finish instructions for someone who has just cloned this repo and has
nothing else installed. Follow the steps in order — step 1 can stop the whole
process, so do it first.

If you only want to know *what this project is*, read [README.md](README.md).

**Roughly how long:** 30–60 minutes, most of it waiting for Xcode to install.

---

## 1. Check your iPhone is supported — do this first

WebDriverAgent (the thing that actually drives the phone) ships **pre-built and
pre-signed** in this repo at [`wda/`](wda/). That is what saves you a day of setup.
The catch: a signed build only installs on the devices that were listed when it was
signed. **9 devices.** Anything else is refused by iOS, no matter what you do.

Find your device's UDID. **Use Finder for this** — you have not installed anything
yet, so the command-line tools are not available to you until step 4:

> Plug the iPhone in and unlock it → open **Finder** → click the iPhone in the
> sidebar → under the device name, **click the line of text** (the one showing
> capacity or the model) — it cycles through serial number, UDID and phone number.
> Copy the **UDID**. Right-click it to copy.

Once the tools are installed (steps 3–4) you can also use:

```bash
idevice_id -l                      # USB-connected devices only
./.venv/bin/python -m tidevice list  # also shows WiFi-paired devices (ConnType column)
```

Now check it against the list in [`wda/README.md`](wda/README.md). The four phones the
test sets were built for are:

| UDID | Device |
|---|---|
| `00008030-001C51DA0E80A02E` | iPhone 11 — the default device |
| `385e82401ffb88ee946698f951ae9b991beba9da` | iPhone 7 |
| `00008120-0001485A1E60201E` | iPhone 14 Pro Max |
| `00008140-0009492E1444801C` | iPhone 16 Pro |

- **Your device is listed** → carry on to step 2.
- **Your device is not listed** → you must rebuild WDA, which needs membership of the
  Apple Developer team. Jump to [Rebuilding WebDriverAgent](#rebuilding-webdriveragent),
  then come back here.

> **Also check the date.** This signed build stops working around **2 July 2027**
> (the signing certificate expires before the profile does). After that everyone needs
> a rebuild. Details in [`wda/README.md`](wda/README.md).

---

## 2. Access you need

| What | Why | If you don't have it |
|---|---|---|
| This GitHub repo | the code, baselines and the signed WDA | ask the repo owner |
| **TestFlight** invite for Spider (`com.fingerarts.Spider`) | there is no app to test otherwise | ask whoever manages the FingerArts builds |
| Apple Developer team **`4528523FZZ`** (USERWISE SERVICES LLC) | **only** if your device is not in the list above | ask the team admin |

Most people need the first two and not the third.

---

## 3. Install the Mac tooling

**Xcode 26.5** with the iOS platform, from the App Store or Apple's developer
downloads. Then:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcodebuild -version                    # expect 26.5
```

Open Xcode once and let it finish installing components before continuing.

**libimobiledevice** — gives you `iproxy` (port forwarding) and `idevice_id`:

```bash
brew install libimobiledevice
which iproxy idevice_id          # both must print a path
```

(`iproxy` actually comes from `libusbmuxd`, which Homebrew installs automatically as a
dependency — you do not need to ask for it separately.)

**Python 3.9+** — macOS already ships `python3` (this project was built on 3.9.6).

```bash
python3 --version
```

---

## 4. Clone and build the Python environment

```bash
git clone git@github.com:Shahab-N-PF/Spider-Solitaire-Automation.git
cd Spider-Solitaire-Automation
./scripts/setup.sh
```

If that clone fails with a permission error you have no SSH key on GitHub. Either
[add one](https://github.com/settings/keys), or clone over HTTPS instead and sign in
when prompted:

```bash
git clone https://github.com/Shahab-N-PF/Spider-Solitaire-Automation.git
```

That creates `.venv/` and installs airtest, poco and tidevice. **Always run things with
`./.venv/bin/python`**, never a system `python3` — the plain one has none of these.

**This needs about 800 MB of disk** — roughly 420 MB of working files plus 380 MB of
git history, nearly all of it screenshots. Measured on a real clone. Downloading it
takes a few minutes.

---

## 5. Prepare the phone

1. **Plug it in over USB** and unlock it. Tap **Trust** if asked.
2. **Keep it unlocked.** WDA cannot install to a locked phone, and the screen locking
   mid-run will break a test.
3. **Remove any other WebDriverAgent.** If the phone has been used with someone else's
   automation, iOS will refuse to replace their copy — the signature is from a
   different team. Remove it first:

   ```bash
   xcrun devicectl device uninstall app --device <YOUR-UDID> \
       com.facebook.WebDriverAgentRunner.xctrunner
   ```

   Harmless if there was nothing to remove.
4. **Trust the developer certificate.** The first time WDA runs, iOS blocks it until you
   approve. On the phone: **Settings → General → VPN & Device Management** → tap the
   USERWISE SERVICES LLC profile → **Trust**. Once per device.

---

## 6. Install Spider from TestFlight

Install TestFlight on the phone, accept the invite, install **Spider**.

Two things to expect, and they matter for the tests:

- **Every TestFlight install is a fresh install.** So the App Tracking Transparency
  prompt appears on first launch, and the Terms & Conditions on the next one. The suite
  handles both, but do not be surprised by them.
- **The home-screen promo icon strip will be missing** until at least one game has been
  completed. That is how the app behaves, not a bug. Never report it from a
  fresh install.

The Unity and Obj-C builds share one bundle id, so only one can be installed at a time.
Swapping means reinstalling through TestFlight.

---

## 7. Start WDA and check it works

Two terminals. **First terminal** — start WDA and leave it running:

```bash
./scripts/wda.sh <YOUR-UDID>
```

It should print `signed build [in-repo (wda/)]`, then `WDA is UP`. If it prints
`fallback: ...` instead, your `wda/` folder did not come through — re-clone.

**Second terminal** — point the Python side at the *same* phone, then smoke-test:

```bash
export DEVICE_UDID=<YOUR-UDID>
curl http://127.0.0.1:8100/status                    # WDA answers
./.venv/bin/python tests/connect_check.py            # connect + screenshot
./.venv/bin/python tests/launch_and_shoot.py         # open Spider + screenshot
```

> **Always set `DEVICE_UDID`.** Without it, Airtest grabs the first device it can see —
> which includes WiFi-paired phones that are not even plugged in. A run aimed at one
> phone silently driving another is a genuinely confusing failure.

Screenshots land in `log/`.

---

## 8. Run the functional suite

Does the Unity build **work**?

```bash
./.venv/bin/python tests/run_all.py
```

**Put the phone in Airplane Mode first — but only after WDA is already up.** Online,
cross-promo ads interrupt screen transitions and make the run flaky. And WDA cannot be
*restarted* while offline, because iOS re-checks the developer certificate over the
network, so the order matters: start WDA, then go offline.

`run_all.py` checks itself before starting and names anything missing.

Several tests need the network and are all deliberately kept out of `run_all.py` —
run them on their own, online: `tests/verifyAds.py` (it brings the device online
itself), `tests/verifyAdFreeVersion.py` and
`tests/visitLastScore.py` (which also needs a signed-in Apple account).
`tests/submitFeedback.py` is standalone too, but for a different reason: it needs a
**Mail account** configured on the device. It never sends, and deletes the draft.

---

## 9. Capturing the Unity screenshots

Does the Unity build **look** like the Obj-C original? This is the pixel comparison, and
it needs one thing the repo cannot give you.

**The Obj-C baselines ship with this repo.** They are the reference — the original
build's appearance, captured once, committed, and **never re-shot**. Overwriting them
with Unity captures would destroy the very thing the comparison measures.

**The Unity captures do not ship.** They come off the build on your phone and land in
`log/`, which is git-ignored. So on a fresh clone you must shoot them yourself before a
comparison means anything. Run the tool with nothing captured and it now tells you so
and exits non-zero, rather than printing a clean-looking summary of nothing.

| Device | Command | Unity captures go to |
|---|---|---|
| **iPhone 11** | `./.venv/bin/python tests/compare_unity.py --report` | `log/` — **captures and compares in one go, nothing manual** |
| **iPhone 7** portrait | `DEVICE=iphone7/portrait ./.venv/bin/python tests/compare_unity_ip7.py --report` | `log/ip7_unity/` — shoot by hand first |
| **iPhone 7** landscape | `DEVICE=iphone7/landscape ./.venv/bin/python tests/compare_unity_ip7_landscape.py --report` | `log/ip7_landscape_unity/` — by hand, phone rotated |
| **iPhone 14 Pro Max** | `DEVICE=iphone14 ./.venv/bin/python tests/compare_unity_ip14.py --report` | `log/ip14_unity/` — shoot by hand first |
| **iPad** | `./.venv/bin/python tests/compare_unity_ipad.py --report` | `ipad/unity/` — **already committed, works immediately** |

**To learn which files a device expects, just run its tool.** It prints every screen it
wanted and marks the missing ones `[no-capture]`. Those names are the filenames to save —
they must match exactly.

### Shooting them by hand

Only the iPhone 11 automates this. For the others, walk the app to each screen and save a
full-resolution screenshot under the right name. The screenshot method differs by device,
and this is not a preference — the other methods genuinely fail:

- **iPhone 7 (iOS 15):** use `tidevice` (`launch` + `screenshot`). WDA does not run on this
  phone at all under Xcode 26.5. Plug in **only** the iPhone 7 so nothing else is picked up.
- **iPhone 14 Pro Max (iOS 26):** use WDA + Airtest, as the iPhone 11 does. `tidevice
  screenshot` fails here — the Developer Disk Image will not mount on iOS 26.
- **iPad (iOS 26):** same reason, WDA + Airtest. Its captures are already committed, so you
  only need this when re-shooting for a new build.

Nothing in the repo scripts these walks yet. Set aside real time for it.

---

## 10. Adding a device that isn't covered

The four phones and the iPad above have complete sets. A **new** device needs more than a
WDA rebuild, because the comparison has nothing to compare against:

1. Register the device and rebuild WDA — see below.
2. Crop a template set at that resolution (`scripts/crop_unity_assets.py`,
   gated by `scripts/verify_unity_assets.py`). A 19.5:9 phone may need none at all: the
   `assets_unity/` set is rescaled at match time and already covers that whole family.
3. **Capture Obj-C baselines** — and this is the hard part.

> **Warning about step 3.** The baselines must come from the **Obj-C build, 7.42.5**. That
> build is old and may not install on current iOS at all (already flagged in
> `reports/CHANGELOG.md`). If it will not run on your device, that device **cannot** have a
> pixel comparison — only functional tests. Find this out before promising the work.

---

## Rebuilding WebDriverAgent

Only needed when your device is not in the signed profile, or after the ~2 July 2027
expiry. You need a signing certificate in Apple Developer team **`4528523FZZ`**.

The WebDriverAgent project does not live in any repo here — it comes from Appium:

1. Install Node, then Appium and its XCUITest driver. That puts
   `WebDriverAgent.xcodeproj` under `~/.appium/node_modules/appium-webdriveragent/`.
2. Build and sign it for your device. The two flags that matter are
   `-allowProvisioningUpdates` and `-allowProvisioningDeviceRegistration` — the second is
   what adds a new phone to the profile:

   ```bash
   xcodebuild -project "$HOME/.appium/node_modules/appium-webdriveragent/WebDriverAgent.xcodeproj" \
     -scheme WebDriverAgentRunner -destination "id=<YOUR-UDID>" \
     -derivedDataPath /tmp/wda-build \
     DEVELOPMENT_TEAM=4528523FZZ "CODE_SIGN_IDENTITY=Apple Development" \
     CODE_SIGNING_REQUIRED=YES CODE_SIGNING_ALLOWED=YES \
     -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
     build-for-testing
   ```

3. Replace `wda/` with the new `Build/Products/`, keeping the layout identical, and commit
   it so the next person does not repeat this:

   ```bash
   rm -rf wda && cp -Rp /tmp/wda-build/Build/Products/ wda/
   codesign --verify --deep --strict wda/Debug-iphoneos/WebDriverAgentRunner-Runner.app
   ```

To use a build without committing it: `WDA_PRODUCTS=/tmp/wda-build/Build/Products ./scripts/wda.sh`.

---

## Troubleshooting

**`wda.sh` says the certificate is not trusted, and it worked yesterday.**
The phone is offline. iOS re-checks the developer certificate over the network whenever
the runner relaunches — trust was simply still cached before. Reconnect, relaunch WDA,
then go back to Airplane Mode.

**The run drove the wrong phone.**
`DEVICE_UDID` was not set, or not the same UDID you gave `wda.sh`. Note that
`idevice_id -l` shows USB devices only, so the WiFi-paired phone that stole the run will
not appear there — use `tidevice list`.

**`wda.sh` says no signed WDA build found.**
Your `wda/` folder is missing. `git checkout -- wda`, or re-clone.

**WDA will not start on the iPhone 7.**
It cannot. That is settled, not a setup mistake — Xcode 26.5 cannot hold an XCTest
session on iOS 15.7.5. Use `tidevice` for that phone.

**A test failed on an advertisement.**
The device was online. Go into Airplane Mode (after WDA is up) and re-run.

**A comparison said `NOTHING WAS COMPARED`.**
Working as intended — you have no Unity captures yet. See
[section 9](#9-capturing-the-unity-screenshots).

**The promo icons are missing from the main menu.**
Complete a game first. The app does not draw that strip until one game has been won.
Not a bug.
