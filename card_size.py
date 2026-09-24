"""Card-size check for the Play screen.

The pixel diff masks the tableau because the deal is random, so a card that is
drawn larger — the frame, the rank, and the suit — never shows up there. This
measures those three sizes instead and compares them to the Obj-C baseline.

Sizes are fractions, so a 768-wide capture and a 1620-wide baseline compare
directly. A screen fails when Unity is more than LARGER_THAN (3%) bigger.
"""
import cv2
import numpy as np

# Unity may be this much larger than Obj-C before the Play screen fails.
LARGER_THAN = 0.03


def _white(img):
    return img.min(axis=2) > 190


def _ink(img):
    b, g, r = [c.astype(np.int16) for c in cv2.split(img)]
    black = (b < 110) & (g < 110) & (r < 110)
    red = (r > 130) & (r > g + 40) & (r > b + 40)
    return black | red


def _runs(row, lo, hi):
    runs = []
    i = 0
    n = len(row)
    while i < n:
        if row[i]:
            j = i + 1
            while j < n and row[j]:
                j += 1
            w = j - i
            if lo < w < hi:
                runs.append((i, j, w))
            i = j
        else:
            i += 1
    return runs


def _card_span(white, x0, x1, y_hit, y0, y1, min_frac=0.22):
    """Vertical span of the white face that crosses y_hit.

    Card-back slivers above the face are separated from it by rows that are
    mostly red, so a white-fraction gap ends the face instead of swallowing
    the whole stack.
    """
    sl = white[y0:y1, x0:x1]
    if sl.size == 0:
        return None
    frac = sl.mean(axis=1)
    rel = y_hit - y0
    if rel < 0 or rel >= len(frac):
        return None
    if frac[rel] <= min_frac:
        on = np.where(frac > min_frac)[0]
        if len(on) == 0:
            return None
        rel = int(on[np.argmin(np.abs(on - rel))])
    a = rel
    while a > 0 and frac[a - 1] > min_frac:
        a -= 1
    b = rel
    while b + 1 < len(frac) and frac[b + 1] > min_frac:
        b += 1
    return y0 + a, y0 + b + 1


def _blobs(mask):
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area >= 20:
            out.append((int(y), int(h), int(x), int(w), int(area)))
    return out


def measure(img, band):
    """Measure one Play screenshot.

    `band` is (x0, y0, x1, y1) of the tableau, the same rect the pixel diff
    ignores. Returns a dict with stock and face frame sizes (fractions of
    screen width) plus rank and suit heights (fractions of card height), and
    the pixel boxes to draw. Empty fields are None when a part is not found.
    """
    H, W = img.shape[:2]
    _, y0, _, y1 = band
    y0, y1 = max(0, y0), min(H, y1)
    white = _white(img)
    lo, hi = int(W * 0.055), int(W * 0.18)
    best = []
    best_w = 0
    for y in range(y0, y1, 2):
        runs = _runs(white[y], lo, hi)
        # the full face is wider than the card-back slivers stacked above it,
        # so the row to trust is the widest one that still holds a full line
        if len(runs) >= 6:
            med = float(np.median([w for *_, w in runs]))
            if med > best_w:
                best_w = med
                best = [(y, a, b, w) for a, b, w in runs]
    out = {
        "card_w": None, "card_h": None, "stock_w": None, "stock_h": None,
        "rank_h": None, "suit_h": None,
        "stock_box": None, "face_box": None, "rank_box": None, "suit_box": None,
        "cards": [],
    }
    if len(best) < 4:
        return out

    widths = [w for _, _, _, w in best]
    card_w = float(np.median(widths))
    # One scanline misses a face whose pip breaks the white run, and the
    # rightmost card often sits a little higher than the others. Collect every
    # card-width run, one column at a time, and keep that column's tallest face.
    hits = []
    for y in range(y0, y1, 2):
        for a, b, w in _runs(white[y], card_w * 0.85, card_w * 1.15):
            hits.append((y, a, b))
    hits.sort(key=lambda t: t[1])
    columns = []
    for y, a, b in hits:
        if not columns or a - columns[-1][0][1] > card_w * 0.45:
            columns.append([(y, a, b)])
        else:
            columns[-1].append((y, a, b))
    spans = []
    for col in columns:
        best_span = None
        for y, a, b in col[::2]:
            span = _card_span(white, a, b, y, y0, y1)
            if span is None:
                continue
            top, bot = span
            h = bot - top
            if not (card_w * 1.05 < h < card_w * 1.8):
                continue
            if best_span is None or h > best_span[4]:
                best_span = (a, top, b, bot, h)
        if best_span is not None:
            spans.append(best_span)
    if not spans:
        return out
    # the stock and the completed-suit pile sit above the tableau; the face
    # row is the lower band that holds the most cards
    spans.sort(key=lambda s: s[1])
    bands, group = [], [spans[0]]
    for s in spans[1:]:
        if s[1] - group[-1][1] > card_w * 0.6:
            bands.append(group)
            group = [s]
        else:
            group.append(s)
    bands.append(group)
    spans = max(bands, key=lambda g: (len(g), g[0][1]))
    card_h = float(np.median([h for *_, h in spans]))
    spans = [s for s in spans if abs(s[4] - card_h) < card_h * 0.15]
    out["card_w"] = card_w / W
    out["card_h"] = card_h / W

    # Every face keeps its own rank patch. compare() then pairs cards that
    # show the same number instead of averaging a 9 with a 2.
    ink = _ink(img)
    spans.sort(key=lambda s: s[0])
    for x0, top, x1, bot, h in spans:
        if x0 < 4:
            continue
        cw = x1 - x0
        region = ink[top:bot, x0:x1]
        blobs = _blobs(region)
        if not blobs:
            continue
        blobs.sort()
        ry, rh, rx, rw, _ = blobs[0]
        if rh < h * 0.08 or rh > h * 0.45:
            continue
        rank_box = (x0 + rx, top + ry, x0 + rx + rw, top + ry + rh)
        patch = _rank_patch(region, (ry, rh, rx, rw))
        if patch is None:
            continue
        suit_h = suit_box = None
        pips = [b for b in blobs[1:] if b[2] > cw * 0.15 and cw * 0.2 < b[3] < cw * 0.65
                and h * 0.2 < b[1] < h * 0.7]
        if pips:
            pips.sort(key=lambda b: b[4], reverse=True)
            sy, sh, sx, sw, _ = pips[0]
            suit_h = sh / h
            suit_box = (x0 + sx, top + sy, x0 + sx + sw, top + sy + sh)
        out["cards"].append({
            "x": x0, "box": (x0, top, x1, bot),
            "card_w": cw / W, "rank_h": rh / h, "suit_h": suit_h,
            "rank_box": rank_box, "suit_box": suit_box, "patch": patch,
        })

    # stock sits above the tableau. The tableau starts at the first row
    # that holds a whole line of cards; everything above that is foundation
    # and stock.
    tableau_y = y1
    for y in range(y0, y1, 2):
        if len(_runs(white[y], card_w * 0.7, card_w * 1.3)) >= 6:
            tableau_y = y
            break
    stock = _stock(img, white, y0, tableau_y, card_w)
    if stock is not None:
        sx0, sy0, sx1, sy1 = stock
        out["stock_box"] = stock
        out["stock_w"] = (sx1 - sx0) / W
        out["stock_h"] = (sy1 - sy0) / W
    return out


def _stock(img, white, y0, face_top, card_w):
    """Front card of the stock pile, above the face row and right of centre.

    The back is red with a white border, so the top edge is a white run of
    about one card width and the body is whatever is not green felt.
    """
    if face_top - y0 < card_w * 0.5:
        return None
    H, W = white.shape
    b, g, r = [c.astype(np.int16) for c in cv2.split(img)]
    felt = (r < 80) & (g > 100) & (g > b)
    body = ~felt
    found = []
    for y in range(y0, face_top, 2):
        runs = _runs(white[y], card_w * 0.75, card_w * 1.25)
        right = [t for t in runs if t[0] > W * 0.45]
        if right:
            found.append((y, right[-1]))
    if not found:
        return None
    # the front card's top edge is the run closest to the face width
    y, (x0, x1, _) = min(found, key=lambda t: abs(t[1][2] - card_w))
    col = body[y0:face_top, x0:x1].mean(axis=1) > 0.4
    rel = y - y0
    if rel < 0 or rel >= len(col) or not col[rel]:
        return None
    a = rel
    while a > 0 and col[a - 1]:
        a -= 1
    b = rel
    while b + 1 < len(col) and col[b + 1]:
        b += 1
    return (x0, y0 + a, x1, y0 + b + 1)


def _rank_patch(region, blob):
    """Fixed-size ink image of the corner rank, so two cards can be correlated."""
    ry, rh, rx, rw, = blob[0], blob[1], blob[2], blob[3]
    pad = 2
    y0, x0 = max(0, ry - pad), max(0, rx - pad)
    y1 = min(region.shape[0], ry + rh + pad)
    x1 = min(region.shape[1], rx + rw + pad)
    crop = region[y0:y1, x0:x1]
    if crop.size == 0 or int(crop.sum()) < 15:
        return None
    return cv2.resize(crop.astype(np.float32), (24, 40), interpolation=cv2.INTER_AREA)


def _corr(a, b):
    if a is None or b is None:
        return -1.0
    av, bv = a.ravel(), b.ravel()
    av = av - av.mean()
    bv = bv - bv.mean()
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    if denom == 0:
        return -1.0
    return float(av @ bv / denom)


# Same digit correlates well above this; a 9 against a 2 does not.
_RANK_MATCH = 0.55


def _match_cards(base, cur):
    """Rightmost pair whose rank ink is the same number. None when nothing matches."""
    cands = []
    for b in base.get("cards") or []:
        for c in cur.get("cards") or []:
            score = _corr(b["patch"], c["patch"])
            if score < _RANK_MATCH:
                continue
            # how many card-widths from the left edge; the shared rightmost
            # card (the 5 on both screens) has the highest of these
            bw = max(b["box"][2] - b["box"][0], 1)
            cw = max(c["box"][2] - c["box"][0], 1)
            right = min(b["x"] / bw, c["x"] / cw)
            cands.append((right, score, b, c))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return cands[0][2], cands[0][3]


def _apply_card(measured, card):
    """Point the drawn boxes and the size fields at one matched face."""
    if card is None:
        return
    measured["face_box"] = card["box"]
    measured["rank_box"] = card["rank_box"]
    measured["suit_box"] = card["suit_box"]
    measured["card_w"] = card["card_w"]
    measured["rank_h"] = card["rank_h"]
    measured["suit_h"] = card["suit_h"]


def _pct_larger(cur, base):
    if cur is None or base is None or base == 0:
        return None
    return (cur - base) / base


def compare(base_img, cur_img, band):
    """Compare Unity `cur_img` card sizes to the Obj-C `base_img`.

    Returns measured sizes, the fractional growth of each, `larger` (the
    fields that exceed LARGER_THAN), and both sets of boxes.
    """
    base = measure(base_img, band)
    cur = measure(cur_img, band)
    pair = _match_cards(base, cur)
    matched = pair is not None
    if matched:
        _apply_card(base, pair[0])
        _apply_card(cur, pair[1])
    else:
        # do not size a 9 against a 2
        base["card_w"] = cur["card_w"] = None
        base["rank_h"] = cur["rank_h"] = None
        base["suit_h"] = cur["suit_h"] = None
    fields = ("stock_w", "card_w", "rank_h", "suit_h")
    growth = {k: _pct_larger(cur[k], base[k]) for k in fields}
    frame = growth["card_w"]
    larger = []
    if matched:
        if frame is not None and frame > LARGER_THAN:
            larger.append("card width")
        for key, label in (("rank_h", "rank"), ("suit_h", "suit")):
            if growth[key] is not None and growth[key] > LARGER_THAN:
                larger.append(label)
    return {
        "base": base, "cur": cur, "growth": growth, "frame": frame,
        "larger": larger, "fail": bool(larger), "matched": matched,
    }


def line(result):
    """One summary line, e.g. 'card width +4.8%, rank +6.1%, suit +1.2%'."""
    if not result.get("matched"):
        return "no shared rank"
    g = result["growth"]
    frame = result["frame"]
    parts = []
    if frame is not None:
        parts.append(f"card width {frame * 100:+.1f}%")
    for key, label in (("rank_h", "rank"), ("suit_h", "suit")):
        if g[key] is not None:
            parts.append(f"{label} {g[key] * 100:+.1f}%")
    if not parts:
        return "matched rightmost same rank"
    flag = "  <-- larger" if result["fail"] else ""
    return "matched rightmost same rank: " + ", ".join(parts) + flag


def crop_pair(base_img, cur_img, result, scale=3):
    """Enlarged side-by-side of the matched face, so both sides show the same rank."""
    if not result.get("matched"):
        return None
    def zoom(img, box):
        if not box:
            return None
        x0, y0, x1, y1 = box
        pad = 8
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1, y1 = min(img.shape[1], x1 + pad), min(img.shape[0], y1 + pad)
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            return None
        return cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    b = zoom(base_img, result["base"].get("face_box"))
    c = zoom(cur_img, result["cur"].get("face_box"))
    if b is None or c is None:
        return None
    h = max(b.shape[0], c.shape[0])
    def fit(im):
        if im.shape[0] == h:
            return im
        canvas = np.zeros((h, im.shape[1], 3), np.uint8)
        canvas[:im.shape[0]] = im
        return canvas
    return np.hstack([fit(b), fit(c)])


def mark(base_img, overlay_img, raw_cur, band, color=(0, 220, 0)):
    """Draw the matched face on both sides and return its enlarged crop."""
    sized = compare(base_img, raw_cur, band)
    return (
        draw_boxes(base_img, sized["base"], color),
        draw_boxes(overlay_img, sized["cur"], color),
        crop_pair(base_img, raw_cur, sized),
    )


def stack_crop(combo, crop):
    """Put the enlarged matched cards under the side-by-side diff."""
    if crop is None:
        return combo
    if crop.shape[1] < combo.shape[1]:
        pad = np.zeros((crop.shape[0], combo.shape[1] - crop.shape[1], 3), np.uint8)
        crop = np.hstack([crop, pad])
    elif crop.shape[1] > combo.shape[1]:
        crop = cv2.resize(crop, (combo.shape[1], crop.shape[0]), interpolation=cv2.INTER_AREA)
    return np.vstack([combo, crop])


def draw_boxes(img, measured, color):
    """Outline the stock, one face, and its rank and suit. Returns a copy."""
    out = img.copy()
    for key in ("stock_box", "face_box", "rank_box", "suit_box"):
        box = measured.get(key)
        if not box:
            continue
        x0, y0, x1, y1 = box
        cv2.rectangle(out, (x0, y0), (x1, y1), color, 2)
    return out
