#!/usr/bin/env python3
"""Build the interactive Unity-vs-Obj-C comparison report from the latest captures.

Reads baselines/<name>.png (Obj-C reference) and log/<name>.png (this run's Unity
capture), recomputes the exact-pixel diff % via visual.compare (fresh each run),
and writes a self-contained HTML page: per screen a drag-to-compare wipe/fade
viewer with toggleable alignment rulers and curated per-element callout pins.

The diff percentages are recomputed every run; the callout TEXT below is curated
analysis of the current differences — edit META as the port changes. Baselines
are never modified.

Usage:  ./.venv/bin/python scripts/gen_compare_report.py [out.html]
   or:  ./.venv/bin/python tests/compare_unity.py --report
"""
import base64
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import visual  # noqa: E402
from PIL import Image  # noqa: E402

BASELINES = visual.BASELINES
LOG = config.LOG

# Curated per-screen analysis. diff % is NOT stored here (recomputed each run);
# only the qualitative notes + measured anchors are. kind drives the badge:
# closest | confound | diff. callout kind: measured|layout|content|state|decor.
META = [
    ("SpiderAboutPage", "About", "closest",
     "Closest match. Title glyph and version differ; logo/links re-spaced. No red header bar in either build.",
     [(1, 50, 46, "Title", "&ldquo;Spider &#9655; Solitaire&rdquo; &rarr; &ldquo;Spider Solitaire&rdquo; — the &#9655; glyph is dropped", "content"),
      (2, 50, 53, "Version line", "7.42.5 &rarr; 8.0.0 (expected build bump; masked when gating)", "content"),
      (3, 38, 30, "Logo + link block", "Vertical spacing changed; whole block re-positioned lower", "layout"),
      (4, 22, 10, "Header bar", "No red header bar in either build (felt to the top)", "content")]),
    ("Play", "Play — game table", "diff",
     "Fresh Easy game vs Easy baseline (tableau cards are masked). Same systemic shift: table higher, controls lower.",
     [(1, 50, 36, "Tableau row", "Sits higher in Unity — the top of the stacks escapes the masked card region", "layout"),
      (2, 50, 80, "Bottom controls", "&ldquo;tap to undo / lower / hints&rdquo; + score row shifted lower &amp; re-spaced", "layout"),
      (3, 50, 10, "Top bar", "back / new / menu shifted up", "layout"),
      (4, 50, 73, "Difficulty label", "Same &ldquo;easy level&rdquo; text, repositioned (tableau cards are masked out)", "content")]),
    ("StatsPage", "Statistics", "diff",
     "Top global-stats block still lines up (&asymp;&minus;16 px); decorations dropped and per-difficulty rows tighten and drift.",
     [(1, 84, 8, "&ldquo;Game Center&rdquo; control", "Text label dropped — Unity shows the icon only", "decor"),
      (2, 50, 37, "Difficulty headers", "&ldquo;Easy / Medium / Hard…&rdquo; lose the &#10059; flower flourish", "decor"),
      (3, 32, 24, "Global stats block", "Top block still aligns — header bar Δ&asymp;&minus;16 px", "measured"),
      (4, 46, 52, "Per-difficulty rows", "Tighter line-height &rarr; labels drift progressively down-screen", "layout")]),
    ("MainMenu", "Main Menu", "confound",
     "Background is state-confounded (#6), but the buttons match as templates on both builds — the arc fans out, each item progressively lower.",
     [(1, 76, 46, "Play", "&minus;12 px (sits slightly higher in Unity)", "measured"),
      (2, 76, 55, "Stats", "+28 px lower", "measured"),
      (3, 76, 62, "Options", "+36 px lower", "measured"),
      (4, 76, 69, "Help", "+56 px lower", "measured"),
      (5, 76, 78, "About", "+89 px lower", "measured"),
      (6, 34, 26, "Menu background", "Obj-C baseline has a paused resume-game ghost + promo-icon column + a red &ldquo;1&rdquo; badge; clean Unity launch has none (state, not a render diff)", "state")]),
    ("more_games_icons", "Home promo icons", "diff",
     "The home-screen promo-icon strip does not render in Unity — the headline gap here; the menu itself shares the Main-Menu fan-out.",
     [(1, 9, 32, "Promo-icon strip", "5 game icons (Solitaire / Sudoku 2 / Card Games / FreeCell / Spiderette) present in Obj-C — <b>absent in Unity</b>", "content"),
      (2, 76, 52, "Menu buttons", "Same fan-out as Main Menu (Play &minus;12 &rarr; About +89 px)", "measured"),
      (3, 14, 68, "More Games badge", "Red &ldquo;1&rdquo; badge present in Obj-C, absent in Unity", "state"),
      (4, 33, 52, "Resume-game ghost", "Paused game ghosts through in Obj-C baseline; clean in Unity", "state")]),
    ("OptionsPage", "Options", "diff",
     "Title/content start ~80 px higher on a shorter header bar; a wrap changes; rows drift further out of alignment downward.",
     [(1, 50, 8, "Title / header bar", "Bar bottom &minus;80 px — &ldquo;Options&rdquo; and everything below start ~80 px higher", "measured"),
      (2, 42, 52, "&ldquo;Maintain Card Spacing&rdquo;", "Wraps to 2 lines in Obj-C, 1 line in Unity", "content"),
      (3, 28, 20, "Row spacing", "Tighter line-height throughout the list", "layout"),
      (4, 44, 90, "List length", "Unity fits Card Lowering / Show Status Bar / Show Card Messages on-screen; Obj-C pushes them below the fold", "layout")]),
    ("choose_look_cards", "Choose Look · Cards", "diff",
     "Whole modal shifted down; the six card-back designs match but re-position; the preview card differs.",
     [(1, 50, 30, "Modal position", "Whole modal shifted down vs Obj-C", "layout"),
      (2, 35, 45, "Card-back designs", "6 options — designs match, but re-positioned", "content"),
      (3, 24, 68, "Preview card", "Q&hearts; (Obj-C) &rarr; Q&spades; (Unity)", "content"),
      (4, 50, 18, "Surface / Cards tabs", "Present in both; sit lower", "layout")]),
    ("choose_look_surface", "Choose Look · Surface", "diff",
     "Same modal, shifted down; the nine surface swatches render identically but their frames re-space.",
     [(1, 50, 30, "Modal position", "Whole modal shifted down vs Obj-C", "layout"),
      (2, 40, 45, "Surface swatches", "9 swatches — images match; frames re-spaced", "content"),
      (3, 20, 66, "&ldquo;Simulate Depth&rdquo; toggle", "Present in both; shifted lower", "layout"),
      (4, 50, 18, "Surface / Cards tabs", "Present in both; sit lower", "layout")]),
    ("HelpPage", "Help", "diff",
     "Largest sub-screen divergence: card strip much more compact and body copy smaller/lighter, so an extra section fits.",
     [(1, 50, 7, "FOUNDATIONS / SOURCE / TABLEAUX strip", "Strip bottom &minus;148 px — markedly more compact &amp; higher; smaller cards", "measured"),
      (2, 45, 30, "Body copy", "Rendered smaller and lighter-weight than Obj-C", "content"),
      (3, 38, 19, "Section headers", "&ldquo;Introduction / Rules&rdquo; set smaller", "content"),
      (4, 42, 90, "&ldquo;Interaction&rdquo; section", "Fits on-screen in Unity; off the bottom in Obj-C", "layout")]),
    ("MoreGames", "More Games", "diff",
     "The biggest single difference in the suite: the dark theatre-stage backdrop is replaced by plain green felt.",
     [(1, 50, 30, "Backdrop", "<b>Dark theatre-stage (Obj-C) &rarr; green felt (Unity)</b> — the largest single render difference", "layout"),
      (2, 50, 40, "Game promos", "Solitaire / Sudoku 2 / Card Games / FreeCell in both; lit differently against the new backdrop", "content"),
      (3, 50, 15, "&ldquo;Signed in as…&rdquo; toast", "Transient Game Center banner in the Unity capture (state)", "state"),
      (4, 12, 12, "&ldquo;back&rdquo; / &ldquo;Tap any game…&rdquo;", "Same labels; positions hold", "content")]),
]

KIND = {"measured": ("Measured", "k-meas"), "layout": ("Layout", "k-lay"),
        "content": ("Content", "k-con"), "state": ("State", "k-sta"),
        "decor": ("Decoration", "k-dec")}
BADGE = {"diff": ("differs", "b-diff"), "closest": ("closest", "b-close"),
         "confound": ("state-confounded", "b-warn")}


def _durl(path, w=560, q=80):
    im = Image.open(path).convert("RGB")
    if im.width > w:
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def build(out=None):
    out = out or os.path.join(LOG, "unity_compare.html")
    rows = []
    for name, label, kind, summary, calls in META:
        base_p = os.path.join(BASELINES, name + ".png")
        cap_p = os.path.join(LOG, name + ".png")
        if not (os.path.exists(base_p) and os.path.exists(cap_p)):
            continue  # skip screens we couldn't capture this run
        spec = visual.SPECS.get(name + ".png", {"ignore": [], "max_diff": 0.01})
        r = visual.compare(name + ".png", spec["ignore"], spec["max_diff"])
        diff = r["diff_pct"] if r["diff_pct"] is not None else 0.0
        rows.append({"name": name, "label": label, "kind": kind, "summary": summary,
                     "calls": calls, "diff": diff, "base": base_p, "cap": cap_p})
    rows.sort(key=lambda d: d["diff"])  # closest -> most divergent

    sumrows = "".join(
        f'<tr><td>{d["label"]}</td><td class="n">{d["diff"]:.1f}%'
        f'<span class="bar" style="width:{min(d["diff"],82)*1.7:.0f}px"></span></td>'
        f'<td>{BADGE[d["kind"]][0]}</td></tr>' for d in rows)

    cards = []
    for d in rows:
        badge, bclass = BADGE[d["kind"]]
        pins = "".join(
            f'<span class="pin {KIND[k][1]}" style="left:{x}%;top:{y}%">{n}</span>'
            for n, x, y, el, dt, k in d["calls"])
        items = "".join(
            f'<li><span class="cnum {KIND[k][1]}">{n}</span><div>'
            f'<span class="cel">{el}</span><span class="ctag {KIND[k][1]}">{KIND[k][0]}</span>'
            f'<p class="cdt">{dt}</p></div></li>' for n, x, y, el, dt, k in d["calls"])
        cards.append(f"""
    <section class="card">
      <div class="card-head"><div class="card-title"><span class="scr">{d['label']}</span>
        <span class="fn">{d['name']}.png</span></div>
        <div class="metrics"><span class="pct">{d['diff']:.1f}%</span>
        <span class="pill {bclass}">{badge}</span></div></div>
      <p class="desc">{d['summary']}</p>
      <div class="cmp" role="img" aria-label="{d['label']}: Obj-C vs Unity">
        <img class="base" src="{_durl(d['cap'])}" alt="Unity {d['label']}">
        <img class="over" src="{_durl(d['base'])}" alt="Obj-C {d['label']}">
        <div class="guides"></div><div class="pins">{pins}</div>
        <div class="divider"><span class="knob"></span></div>
        <span class="tag tl">Obj-C</span><span class="tag tr">Unity</span></div>
      <ol class="callouts">{items}</ol>
    </section>""")

    html = _TEMPLATE.replace("__SUM__", sumrows).replace("__CARDS__", "".join(cards))
    os.makedirs(LOG, exist_ok=True)
    with open(out, "w") as f:
        f.write(html)
    return out


_TEMPLATE = r"""<meta charset="utf-8">
<title>Spider Solitaire — Unity Port UI Fidelity</title>
<style>
  :root{--bg:#0e1512;--panel:#141d1a;--panel2:#0b110f;--ink:#e8efec;--muted:#93a49d;--line:#22302b;--accent:#12b886;--red:#ff5670;--amber:#f0b429;--warn:#e8863b;--close:#4ec9a8;--violet:#9d8bf0}
  @media (prefers-color-scheme:light){:root{--bg:#eef2f0;--panel:#fff;--panel2:#f4f7f5;--ink:#12201b;--muted:#5a6b64;--line:#dbe5e0;--accent:#0c8f6b}}
  :root[data-theme="dark"]{--bg:#0e1512;--panel:#141d1a;--panel2:#0b110f;--ink:#e8efec;--muted:#93a49d;--line:#22302b}
  :root[data-theme="light"]{--bg:#eef2f0;--panel:#fff;--panel2:#f4f7f5;--ink:#12201b;--muted:#5a6b64;--line:#dbe5e0;--accent:#0c8f6b}
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1100px;margin:0 auto;padding:48px 24px 80px}
  .eyebrow{font-size:12.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700;margin:0 0 12px}
  h1{font-size:clamp(28px,4.4vw,40px);line-height:1.1;margin:0 0 14px;font-weight:800;letter-spacing:-.01em;text-wrap:balance}
  .lede{font-size:17px;color:var(--muted);max-width:70ch;margin:0}
  header.top{border-bottom:1px solid var(--line);padding-bottom:28px}
  .meta{display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:22px;font-size:13.5px;color:var(--muted)}.meta b{color:var(--ink);font-weight:600}
  table.sum{width:100%;border-collapse:collapse;margin:28px 0 6px;font-size:14px}
  table.sum th,table.sum td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}
  table.sum th{font-size:11.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:700}
  table.sum td.n{font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
  .bar{display:inline-block;height:8px;border-radius:5px;background:var(--red);vertical-align:middle;margin-left:10px;opacity:.85}
  .controls{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:22px 0 8px;padding:12px 14px;background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:12px}
  .cgroup{display:flex;gap:2px;background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:3px}
  .controls button{font:600 13px/1 inherit;color:var(--muted);background:transparent;border:0;border-radius:7px;padding:8px 14px;cursor:pointer}
  .controls button.active{background:var(--accent);color:#04120d}
  .controls .lbl{font-size:11.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:700}
  .hint{font-size:13px;color:var(--muted);margin-left:auto}.hint b{color:var(--ink)}
  .legend{display:flex;flex-wrap:wrap;gap:8px 16px;margin:14px 0 0;font-size:12px;color:var(--muted)}
  .legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:11px;height:11px;border-radius:50%;display:inline-block}
  .lg-meas{background:var(--accent)}.lg-lay{background:var(--violet)}.lg-con{background:var(--amber)}.lg-sta{background:var(--warn)}.lg-dec{background:var(--close)}
  .cards{display:flex;flex-direction:column;gap:26px;margin-top:20px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
  .card-head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:18px 22px 6px;flex-wrap:wrap}
  .card-title{display:flex;flex-direction:column;gap:2px}.scr{font-size:19px;font-weight:800;letter-spacing:-.01em}
  .fn{font:12.5px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}
  .metrics{display:flex;align-items:center;gap:12px}.pct{font-variant-numeric:tabular-nums;font-weight:800;font-size:22px}
  .pill{font-size:11.5px;font-weight:700;letter-spacing:.04em;padding:5px 11px;border-radius:999px;text-transform:uppercase}
  .b-diff{background:color-mix(in srgb,var(--red) 18%,transparent);color:var(--red)}
  .b-close{background:color-mix(in srgb,var(--close) 20%,transparent);color:var(--close)}
  .b-warn{background:color-mix(in srgb,var(--warn) 20%,transparent);color:var(--warn)}
  .desc{margin:0;padding:2px 22px 16px;color:var(--muted);font-size:14.5px;max-width:90ch}.desc b{color:var(--ink)}
  .cmp{--x:50%;--f:.5;position:relative;width:100%;max-width:420px;margin:0 auto;aspect-ratio:828/1792;overflow:hidden;background:var(--panel2);border-top:1px solid var(--line);border-bottom:1px solid var(--line);touch-action:pan-y;cursor:ew-resize;user-select:none}
  .cmp img{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block;pointer-events:none}
  body.mode-wipe .cmp .over{clip-path:inset(0 calc(100% - var(--x)) 0 0);opacity:1}
  body.mode-fade .cmp .over{clip-path:none;opacity:calc(1 - var(--f))}
  .cmp .divider{position:absolute;top:0;bottom:0;left:var(--x);width:2px;margin-left:-1px;background:rgba(255,255,255,.9);box-shadow:0 0 0 1px rgba(0,0,0,.35);pointer-events:none}
  .cmp .knob{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:34px;height:34px;border-radius:50%;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.4);background-image:linear-gradient(90deg,transparent 44%,#333 44%,#333 46%,transparent 46%,transparent 54%,#333 54%,#333 56%,transparent 56%)}
  body.mode-fade .cmp .divider{display:none}
  .cmp .tag{position:absolute;top:10px;font-size:11px;font-weight:800;letter-spacing:.04em;padding:4px 9px;border-radius:6px;background:rgba(0,0,0,.6);color:#fff;pointer-events:none}
  .cmp .tag.tl{left:10px}.cmp .tag.tr{right:10px} body.mode-fade .cmp .tag{opacity:.5}
  .cmp .guides{position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .15s;background:repeating-linear-gradient(to bottom,transparent 0,transparent 47px,rgba(255,214,0,.55) 47px,rgba(255,214,0,.55) 48px)}
  body.show-guides .cmp .guides{opacity:1}
  .pins{position:absolute;inset:0;pointer-events:none;opacity:1;transition:opacity .15s} body.hide-pins .pins{opacity:0}
  .pin{position:absolute;transform:translate(-50%,-50%);width:23px;height:23px;border-radius:50%;display:grid;place-items:center;font:800 12px/1 ui-sans-serif,system-ui;color:#04120d;background:var(--accent);border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.5)}
  .pin.k-lay{background:var(--violet)}.pin.k-con{background:var(--amber)}.pin.k-sta{background:var(--warn)}.pin.k-dec{background:var(--close)}
  .callouts{list-style:none;margin:0;padding:16px 22px 22px;display:grid;grid-template-columns:1fr 1fr;gap:12px 26px}
  @media(max-width:640px){.callouts{grid-template-columns:1fr}}
  .callouts li{display:flex;gap:11px;align-items:flex-start}
  .cnum{flex:none;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font:800 12px/1 system-ui;color:#04120d;background:var(--accent);margin-top:1px}
  .cnum.k-lay{background:var(--violet)}.cnum.k-con{background:var(--amber)}.cnum.k-sta{background:var(--warn)}.cnum.k-dec{background:var(--close)}
  .cel{font-weight:700;font-size:14px}
  .ctag{margin-left:8px;font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:2px 7px;border-radius:999px;vertical-align:middle;background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent)}
  .ctag.k-lay{background:color-mix(in srgb,var(--violet) 20%,transparent);color:var(--violet)}
  .ctag.k-con{background:color-mix(in srgb,var(--amber) 20%,transparent);color:var(--amber)}
  .ctag.k-sta{background:color-mix(in srgb,var(--warn) 20%,transparent);color:var(--warn)}
  .ctag.k-dec{background:color-mix(in srgb,var(--close) 20%,transparent);color:var(--close)}
  .cdt{margin:3px 0 0;font-size:13px;color:var(--muted);line-height:1.5}
  footer{margin-top:52px;padding-top:24px;border-top:1px solid var(--line);color:var(--muted);font-size:13px;max-width:84ch}
  footer b{color:var(--ink)} footer p{margin:0 0 12px}
  code{font:12.5px/1 ui-monospace,Menlo,monospace;background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:1px 6px}
</style>
<div class="wrap">
  <header class="top">
    <p class="eyebrow">Objective-C &rarr; Unity port · pixel fidelity</p>
    <h1>Spider Solitaire — Unity build vs Obj-C reference</h1>
    <p class="lede">Each screen of the Unity build against the committed Objective-C baselines, which stay fixed as the source of truth. Drag to compare; numbered pins call out each element's difference.</p>
    <div class="meta"><span><b>Under test</b> com.fingerarts.Spider (Unity)</span><span><b>Baselines</b> Obj-C build (unchanged)</span><span><b>Compare</b> exact-pixel, masked</span></div>
  </header>
  <table class="sum"><thead><tr><th>Screen</th><th>Pixels differing</th><th>Status</th></tr></thead><tbody>__SUM__</tbody></table>
  <div class="controls">
    <span class="lbl">View</span>
    <div class="cgroup"><button data-mode="wipe" class="active">Wipe</button><button data-mode="fade">Fade</button></div>
    <button id="guides">Alignment rulers</button><button id="pins" class="active">Callout pins</button>
    <span class="hint"><b>Drag</b> across a screen; pins map to the numbered notes below each one.</span>
  </div>
  <div class="legend">
    <span><i class="lg-meas"></i>Measured</span><span><i class="lg-lay"></i>Layout / spacing</span>
    <span><i class="lg-con"></i>Content / type</span><span><i class="lg-dec"></i>Decoration</span><span><i class="lg-sta"></i>State (not a render diff)</span>
  </div>
  <div class="cards">__CARDS__</div>
  <footer>
    <p><b>Pin numbers</b> match the notes under each screen; colours mark the kind of difference (key above). Percentages tagged <b>Measured</b> come from template-matched element centres (menu) or the detected red header-bar edge (sub-screens); everything else is qualitative rather than false-precise pixel values.</p>
    <p><b>Notes.</b> <code>Play</code> masks the randomly-dealt tableau, so its diff reflects chrome only. <code>Main Menu</code> / <code>Home promo icons</code> share a state confound (the Obj-C baselines carry a resume-game ghost + promo strip the clean Unity launch lacks). Status bar, ad banner, debug overlay and version field are masked everywhere.</p>
    <p><b>Method.</b> Unity renders to an opaque view with no accessibility tree, so navigation is by fixed screen coordinates, keeping the driver independent of the pixels under test. Baselines were <b>not</b> modified. Exact per-pixel red-diff composites are in <code>log/diff_*.png</code>.</p>
  </footer>
</div>
<script>
  const body=document.body; body.classList.add('mode-wipe');
  document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{body.classList.remove('mode-wipe','mode-fade');body.classList.add('mode-'+b.dataset.mode);document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('active',x===b));}));
  document.getElementById('guides').addEventListener('click',function(){body.classList.toggle('show-guides');this.classList.toggle('active');});
  document.getElementById('pins').addEventListener('click',function(){body.classList.toggle('hide-pins');this.classList.toggle('active');});
  document.querySelectorAll('.cmp').forEach(cmp=>{let drag=false;const set=cx=>{const r=cmp.getBoundingClientRect();let x=(cx-r.left)/r.width*100;x=Math.max(0,Math.min(100,x));cmp.style.setProperty('--x',x+'%');cmp.style.setProperty('--f',x/100);};
    cmp.addEventListener('pointerdown',e=>{drag=true;cmp.setPointerCapture(e.pointerId);set(e.clientX);});
    cmp.addEventListener('pointermove',e=>{if(drag)set(e.clientX);});
    cmp.addEventListener('pointerup',()=>drag=false);cmp.addEventListener('pointercancel',()=>drag=false);});
</script>"""


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else None
    print("wrote", build(dest))
