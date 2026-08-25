#!/usr/bin/env python3
"""Build a STANDALONE, single-build fidelity report for a chosen subset of screens.

Where `gen_versioned_report.py` produces the full per-device page (build switcher +
verdict + tiles + findings-triage + every screen), this produces just the
**comparisons**: one build, one screen list, no summary furniture.

Device/build/screen config is reused from `gen_versioned_report.DEVICES`, so a
build only has to be wired up once.

Run:  ./.venv/bin/python scripts/gen_standalone_report.py ip7 343 \
          --screens "Difficulty Picker,Main Menu,Menu · Promo Icons,In-Game Menu,Game Table"
Out:  reports/<Device>_Build<label>_Screens.html   (override with --out)
"""
import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from gen_versioned_report import DEVICES, LABELS, uri, sev_of  # noqa: E402

# A handful of screens per page, so embed noticeably bigger than the full report
# (which has to fit 4 builds x 17 screens under the 16MB artifact cap).
CARD_W, CARD_Q = 900, 88
DIFF_W, DIFF_Q = 1200, 84


def resolve(names, order):
    """Map user-supplied screen names onto capture filenames.

    Accepts the filename (`Play.png`), the stem (`Play`), or the human label
    (`Game Table`, `menu promo icons`) — matched loosely, so the caller doesn't
    have to know the internal naming.
    """
    def norm(s):
        return "".join(c for c in s.lower() if c.isalnum())

    by_key = {}
    for n in order:
        by_key.setdefault(norm(n), n)
        by_key.setdefault(norm(os.path.splitext(n)[0]), n)
        by_key.setdefault(norm(LABELS.get(n, "")), n)

    out, missing = [], []
    for want in names:
        hit = by_key.get(norm(want))
        if hit is None:                       # fall back to a contains-match
            cands = [v for k, v in by_key.items() if norm(want) and norm(want) in k]
            hit = cands[0] if len(set(cands)) == 1 else None
        (out.append(hit) if hit else missing.append(want))
    if missing:
        known = ", ".join(sorted({LABELS.get(n, n) for n in order}))
        raise SystemExit(f"unknown screen(s): {missing}\navailable: {known}")
    return out


def build(dev, version, screens, out_path):
    C = dev["module"]
    C.UNITY_DIR = version["unity_dir"]
    zoom = bool(dev.get("zoom"))
    cw, cq = dev.get("card_w") or CARD_W, dev.get("card_q", CARD_Q)
    dw, dq = dev.get("diff_w") or DIFF_W, dev.get("diff_q", DIFF_Q)

    cards = ""
    for n in screens:
        r = C.compare_one(n, C.SPECS[n]["ignore"], C.SPECS[n].get("common"))
        if r["status"] != "ok":
            raise SystemExit(f"{n}: {r['status']} (looked in {version['unity_dir']})")
        pct, sev = r["diff_pct"], sev_of(r["diff_pct"])
        b = uri(os.path.join(C.BASE_DIR, n), cw, cq)
        u = uri(os.path.join(version["unity_dir"], n), cw, cq)
        d = uri(os.path.join(REPO, "log", dev["diff_prefix"] + n), dw, dq)
        note = version["notes"].get(n, "")
        cards += f"""
  <article class="card s-{sev}">
    <div class="ch"><h3>{LABELS.get(n, n)}</h3><span class="pill s-{sev}">{pct:.1f}%</span></div>
    <div class="cmp" data-mode="wipe">
      <div class="wipe">
        <img class="b" src="{b}" alt="Obj-C baseline">
        <img class="t" src="{u}" alt="Unity {version['label']}">
        <span class="hdl"></span>
        <input type="range" min="0" max="100" value="50" aria-label="wipe">
        <span class="lab l">Obj-C</span><span class="lab r">Unity</span>
      </div>
      <img class="diffimg" src="{d}" alt="changed pixels">
    </div>
    <div class="foot">
      <div class="segrow">
        <div class="seg"><button class="on" data-m="wipe">Wipe</button><button data-m="diff">Diff</button></div>
        {'<button class="zoombtn" type="button">⤢ Enlarge</button>' if zoom else ''}
      </div>
      <p class="note">{note}</p>
    </div>
  </article>"""

    html = (_PAGE.replace("__TITLE__", dev["title"])
                 .replace("__RES__", dev["res"])
                 .replace("__ASPECT__", dev["aspect"])
                 .replace("__BUILD__", version["label"])
                 .replace("__DATE__", version["date"])
                 .replace("__COUNT__", str(len(screens)))
                 .replace("__ZOOM__", "true" if zoom else "false")
                 .replace("__WRAP__", str(dev.get("wrap", 1120)))
                 .replace("__CARDMIN__", str(dev.get("card_min", 320)))
                 .replace("__CARDS__", cards))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)
    print(f"wrote {out_path}  ({os.path.getsize(out_path)/1024:.0f} KB, "
          f"{len(screens)} screens, build {version['label']})")


_PAGE = """<title>__TITLE__ · Unity build __BUILD__ — screen comparison</title>
<style>
:root{ --felt:#0d1512; --panel:#151f1a; --panel2:#1b2721; --line:#27342d; --ink:#e9f0ea;
  --muted:#8fa89a; --gold:#e3b64a; --bad:#f0616a; --warn:#e6a13c; --info:#5bb6c9; --ok:#4cba86;
  --disp:"Rockwell","Roboto Slab",Georgia,serif; --body:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace; }
@media (prefers-color-scheme: light){ :root{ --felt:#f4f1e9; --panel:#fffefb; --panel2:#efece2; --line:#e2ddce;
  --ink:#1b2620; --muted:#5d6f66; --gold:#9c6f13; --bad:#c1373f; --warn:#a86c15; --info:#2c7889; --ok:#2c855a; } }
:root[data-theme="dark"]{ --felt:#0d1512; --panel:#151f1a; --panel2:#1b2721; --line:#27342d; --ink:#e9f0ea;
  --muted:#8fa89a; --gold:#e3b64a; --bad:#f0616a; --warn:#e6a13c; --info:#5bb6c9; --ok:#4cba86; }
:root[data-theme="light"]{ --felt:#f4f1e9; --panel:#fffefb; --panel2:#efece2; --line:#e2ddce; --ink:#1b2620;
  --muted:#5d6f66; --gold:#9c6f13; --bad:#c1373f; --warn:#a86c15; --info:#2c7889; --ok:#2c855a; }
*{box-sizing:border-box}
body{margin:0;background:var(--felt);color:var(--ink);font-family:var(--body);line-height:1.5;-webkit-font-smoothing:antialiased;
  background-image:radial-gradient(120% 60% at 50% -10%, color-mix(in srgb,var(--gold) 7%, transparent), transparent 60%);}
.wrap{max-width:__WRAP__px;margin:0 auto;padding:34px 22px 80px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin:0 0 10px}
h1{font-family:var(--disp);font-weight:700;font-size:clamp(26px,4.4vw,42px);line-height:1.05;margin:0;text-wrap:balance}
.sub{color:var(--muted);margin:10px 0 0;font-size:15px;font-family:var(--mono)}
.hint{color:var(--muted);font-size:13px;margin:18px 0 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(__CARDMIN__px,1fr));gap:20px;margin-top:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
.card.s-hi{border-color:color-mix(in srgb,var(--bad) 42%,var(--line))}
.ch{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:13px 15px;background:var(--panel2);border-bottom:1px solid var(--line)}
.ch h3{margin:0;font-family:var(--disp);font-size:16px;font-weight:700}
.pill{font-family:var(--mono);font-weight:700;font-size:13px;font-variant-numeric:tabular-nums;padding:3px 9px;border-radius:20px;color:var(--ok);background:color-mix(in srgb,var(--ok) 14%,transparent)}
.pill.s-md{color:var(--warn);background:color-mix(in srgb,var(--warn) 14%,transparent)}
.pill.s-hi{color:var(--bad);background:color-mix(in srgb,var(--bad) 16%,transparent)}
.cmp{position:relative;background:#000}
.wipe{position:relative;width:100%;aspect-ratio:__ASPECT__;overflow:hidden;touch-action:none}
.wipe img{position:absolute;inset:0;width:100%;height:100%;display:block;object-fit:cover}
.wipe .t{clip-path:inset(0 0 0 50%)}
.hdl{position:absolute;top:0;bottom:0;left:50%;width:2px;background:var(--gold);transform:translateX(-1px);pointer-events:none}
.hdl::after{content:"";position:absolute;top:50%;left:50%;width:26px;height:26px;transform:translate(-50%,-50%);border-radius:50%;background:var(--gold);box-shadow:0 1px 6px rgba(0,0,0,.5)}
.wipe input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:ew-resize}
.lab{position:absolute;top:9px;font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:#fff;background:rgba(0,0,0,.55);padding:3px 8px;border-radius:20px;pointer-events:none}
.lab.l{left:9px}.lab.r{right:9px}
.diffimg{display:none;width:100%;height:auto}
.cmp[data-mode="diff"] .wipe{display:none}.cmp[data-mode="diff"] .diffimg{display:block}
.foot{padding:12px 15px 14px;display:flex;flex-direction:column;gap:9px;flex:1}
.seg{display:inline-flex;align-self:flex-start;border:1px solid var(--line);border-radius:9px;overflow:hidden}
.seg button{font-family:var(--mono);font-size:11.5px;color:var(--muted);background:transparent;border:0;padding:5px 12px;cursor:pointer}
.seg button.on{background:var(--gold);color:#1a130a;font-weight:700}
.note{margin:0;color:var(--muted);font-size:13px}
.segrow{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.zoombtn{font-family:var(--mono);font-size:11.5px;color:var(--muted);background:transparent;border:1px solid var(--line);border-radius:9px;padding:5px 12px;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.zoombtn:hover{color:var(--ink);border-color:var(--gold)}
.lb{position:fixed;inset:0;z-index:100;background:rgba(3,7,5,.95);display:flex;align-items:center;justify-content:center;padding:26px}
.lb[hidden]{display:none}
.lbwrap{display:flex;gap:18px;max-width:100%;max-height:100%;overflow:auto;align-items:flex-start}
.lbwrap figure{margin:0;display:flex;flex-direction:column;align-items:center;gap:9px}
.lbwrap img{max-height:85vh;width:auto;border-radius:10px;box-shadow:0 6px 44px rgba(0,0,0,.6);background:#000}
.lbwrap figcaption{font-family:var(--mono);font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--gold)}
.lbtitle{position:fixed;top:18px;left:0;right:0;text-align:center;font-family:var(--disp);font-size:17px;color:var(--ink);pointer-events:none}
.lbx{position:fixed;top:14px;right:18px;z-index:101;width:42px;height:42px;border-radius:50%;border:0;background:rgba(255,255,255,.15);color:#fff;font-size:20px;cursor:pointer}
.lbx:hover{background:rgba(255,255,255,.26)}
.lbhint{position:fixed;bottom:16px;left:0;right:0;text-align:center;font-family:var(--mono);font-size:11px;color:var(--muted);pointer-events:none}
@media(max-width:760px){.lbwrap{flex-direction:column;align-items:center}.lbwrap img{max-height:none;max-width:92vw}}
footer{color:var(--muted);font-size:12px;font-family:var(--mono);margin-top:40px;text-align:center}
</style>
<div class="wrap">
  <p class="eyebrow">Spider Solitaire · Objective-C → Unity port</p>
  <h1>__TITLE__ — Unity build __BUILD__</h1>
  <p class="sub">Obj-C 7.42.5 baseline · __RES__ · __COUNT__ screens · captured __DATE__</p>
  <p class="hint">Drag to wipe between the Obj-C baseline and Unity __BUILD__, or switch to <b>Diff</b> for the
     changed pixels in red. The percentage is the share of compared pixels that differ; status bar, ad banner,
     dealt cards and score values are masked out of the comparison.</p>
  <div class="grid" id="grid">__CARDS__
  </div>
  <footer>Standalone screen comparison · regenerate with scripts/gen_standalone_report.py</footer>
</div>
<div class="lb" id="lb" hidden>
  <div class="lbtitle" id="lbtitle"></div>
  <button class="lbx" id="lbx" type="button" aria-label="Close">✕</button>
  <div class="lbwrap">
    <figure><img id="lbb" alt="Obj-C baseline"><figcaption>Obj-C 7.42.5</figcaption></figure>
    <figure><img id="lbt" alt="Unity capture"><figcaption>Unity build __BUILD__</figcaption></figure>
  </div>
  <div class="lbhint">Click the backdrop or press Esc to close</div>
</div>
<script>
const ZOOM = __ZOOM__;
const lb = document.getElementById('lb');
function closeLB(){ lb.hidden = true; document.getElementById('lbb').src = ''; document.getElementById('lbt').src = ''; }
document.querySelectorAll('.card').forEach(c => {
  const t = c.querySelector('.t'), h = c.querySelector('.hdl'), r = c.querySelector('input');
  const set = v => { t.style.clipPath = 'inset(0 0 0 ' + v + '%)'; h.style.left = v + '%'; };
  r.addEventListener('input', e => set(e.target.value)); set(50);
  const cmp = c.querySelector('.cmp');
  c.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
    cmp.dataset.mode = b.dataset.m;
    c.querySelectorAll('.seg button').forEach(x => x.classList.toggle('on', x === b));
  }));
  const z = c.querySelector('.zoombtn');
  if (z) z.addEventListener('click', () => {
    document.getElementById('lbb').src = c.querySelector('.b').src;
    document.getElementById('lbt').src = t.src;
    document.getElementById('lbtitle').textContent = c.querySelector('h3').textContent;
    lb.hidden = false;
  });
});
if (ZOOM) {
  lb.addEventListener('click', e => { if (!e.target.closest('.lbwrap') || e.target.id === 'lbx') closeLB(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !lb.hidden) closeLB(); });
}
</script>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("device", nargs="?", default="ip7", choices=sorted(DEVICES))
    ap.add_argument("build", nargs="?", default=None, help="build label, e.g. 343 (default: newest)")
    ap.add_argument("--screens", default=None,
                    help="comma-separated screen names or labels (default: all)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    dev = DEVICES[a.device]
    vers = dev["versions"]
    v = vers[0] if a.build is None else next(
        (x for x in vers if x["label"] == a.build), None)
    if v is None:
        raise SystemExit(f"no build {a.build} for {a.device}; have: "
                         + ", ".join(x["label"] for x in vers))

    order = dev["module"].ORDER
    screens = resolve([s.strip() for s in a.screens.split(",")], order) if a.screens else list(order)
    out = a.out or os.path.join(
        REPO, "reports",
        os.path.basename(dev["out"]).replace("_Unity_Report.html", "")
                                    .replace("_unity_report.html", "")
        + f"_Build{v['label']}_Screens.html")
    build(dev, v, screens, out)
