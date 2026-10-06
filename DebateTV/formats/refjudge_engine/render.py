"""REF-judge engine, step 2 (the worker; runs anywhere, incl. Docker): job folder -> post-ready MP4.

  python3 render.py jobs/<key> [jobs/<key> ...]     ->  out/<key>/<key>.mp4 + post.txt

Per job: the active speaker is found per camera shot and per turn (YuNet faces + mouth motion), and the crop keeps
that face whole and centred in the footage window (split screens never leak the other panel; other faces are kept
fully in or fully out). Every word sits inside the union of the IG Reels / TikTok / Shorts safe zones.
Since 10/6 (the daily content read) every render opens with its title on frame 0, plays 19 s or less of the judged
exchange (pick_window: whole sentences around the payoff line) before the REF's scorecard, and ends on 41_whowon's
"Get your own argument scored" card with the app's screens and the App Store badge. The master is
1080x1920 H.264 ~10 Mbps, -14 LUFS / -1 dBTP, and must pass reel_qa.py (sampled frames: no cut or covered face,
nothing under platform UI) or it is marked REJECTED and never filed. No network needed except fonts/GSAP CDNs.
"""
import html, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time

import cv2

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"
W, H = 1920, 1080          # source frame the crop math assumes (scaled first if different)
# Built for IG Reels + TikTok + YouTube Shorts at once: every word and face sits inside the union of their safe zones
# (reel_qa.SAFE["all"]: top 220, bottom 440, right rail x>910 from y 800). Footage plays in this window only.
# 10/6 content read: the 1080x750 letterbox under a title bar is gone. Footage fills the width on whoever is talking
# in the 41_whowon window (the same footage, blurred, above and below it), the title is on frame 0, the clip runs
# MAX_CLIP seconds or less to the scorecard where the exchange allows, and the piece ends on the whowon end card.
WIN = (0, 330, 1080, 1260)  # x, y, w, h on the 1080x1920 canvas
WIN_AR = WIN[2] / WIN[3]
BAND = (60, 1266, 840, 176)  # caption band, the one capsync.py measures
MAX_CLIP = 19.0            # seconds to the scorecard (11 of the 15 reference winners on 10/6 ran 6 to 19 s)
MIN_CLIP = 7.0
LEAD, TAIL = 0.12, 0.30    # air before the first word and after the last one of the kept window
BEAT = 14 / 30             # the chain sound's beat (ARENA render-farm/audio/sfx_map.py): the ask lands 8 beats after the drop
CTA = 3.5                  # the end card's hold (41_whowon cta_secs)
CATS = [("logicalConsistency", "LOGIC"), ("factualAccuracy", "FACTS"), ("rhetoricalSkill", "RHETORIC"),
        ("rebuttalQuality", "REBUTTAL"), ("fallacyAvoidance", "CLEAN PLAY")]
BANNER = 110               # source rows hidden: the burned-in top strip (Jubilee's question + logo)
FACE_FRAC = 0.25           # speaker face height / crop height (a chest-up single in the tall window)
FACE_Y = 0.36              # face centre sits this far down the crop (headroom above, chin clear of the band)
MIN_CROP_H = 420           # never zoom past this (source px), or the upscale goes soft
CROPS_VERSION = 6          # bump when the reframing logic changes so cached crop plans are redone
# One-change hook experiment: REF_VARIANT=xwho renders the same clip with an open-loop hook into out/<key>-xwho/
VARIANT = os.environ.get("REF_VARIANT", "")
SUFFIX = f"-{VARIANT}" if VARIANT else ""
# parallel `npx --yes hyperframes` installs race in ~/.npm/_npx (ENOTEMPTY/ENOENT); use one fixed install when present
_HF = pathlib.Path(os.environ.get("HF_BIN", "~/.local/hyperframes/node_modules/.bin/hyperframes")).expanduser()
HF = [str(_HF)] if _HF.exists() else ["npx", "--yes", "hyperframes"]
YUNET = os.path.expanduser(os.environ.get("YUNET_MODEL", "~/.local/share/reel_qa/face_detection_yunet_2023mar.onnx"))
# the QA gate lives with the queue (every format goes through it); a render that fails it is never filed
QA_DIRS = [os.path.expanduser(d) for d in (os.environ.get("REEL_QA_DIR", ""), "~/DebateTV2-content-queue/tools/content_queue",
                                              "~/DebateTV2/tools/content_queue") if d]


class Rejected(Exception):
    """Clip is fine to skip (e.g. the source burned in its own graphics); logged, not retried."""


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} exit {r.returncode}: {(r.stderr or r.stdout).strip()[-600:]}")
    return r


def detect_faces(src, t_from, t_to, fps_s=6):
    """Sample at ~6 fps. Returns (samples, shot starts). A sample = {t, shot, faces: [{box, mouth}]} with boxes in
    1920x1080 px; mouth = a small grey patch of the mouth (from YuNet's landmarks) used to tell who is talking."""
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    det = cv2.FaceDetectorYN.create(YUNET, "", (960, 540), 0.7, 0.3, 50)
    step = max(1, int(round(fps / fps_s)))
    samples, starts, prev_hist, prev_thumb, i = [], [], None, None, 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(t_from * fps) - 1))
    i = max(0, int(t_from * fps) - 1)
    while True:
        if not cap.grab():
            break
        t = i / fps
        i += 1
        if t > t_to:
            break
        if (i - 1) % step or t < t_from:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            break
        frame = cv2.resize(frame, (W, H))
        small = cv2.resize(frame, (320, 180))
        hist = cv2.calcHist([cv2.cvtColor(small, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        thumb = cv2.cvtColor(cv2.resize(frame, (64, 36)), cv2.COLOR_BGR2GRAY).astype("float32")
        # a hard cut: the colours change (histogram) or the layout does (same set, new angle: pixel difference)
        if prev_hist is None or cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA) > 0.35 \
                or float(abs(thumb - prev_thumb).mean()) > 28:
            starts.append(t)
        prev_hist, prev_thumb = hist, thumb
        half = cv2.resize(frame, (960, 540))
        _, found = det.detect(half)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = []
        for r in (found if found is not None else []):
            x, y, w, h = (float(v) * 2 for v in r[:4])
            if h < 40 or y + h / 2 < BANNER:
                continue
            (rmx, rmy), (lmx, lmy), (nx, ny) = (r[10] * 2, r[11] * 2), (r[12] * 2, r[13] * 2), (r[8] * 2, r[9] * 2)
            mx0, mx1 = int(min(rmx, lmx) - 0.1 * w), int(max(rmx, lmx) + 0.1 * w)
            my0, my1 = int(ny + 0.05 * h), int(max(rmy, lmy) + 0.2 * h)
            patch = gray[max(0, my0):max(my0 + 1, my1), max(0, mx0):max(mx0 + 1, mx1)]
            mouth = cv2.resize(patch, (24, 12)).astype("float32") if patch.size else None
            marks = [(float(r[k]) * 2, float(r[k + 1]) * 2) for k in range(4, 14, 2)]  # eyes, nose, mouth corners
            faces.append({"box": (x, y, w, h), "mouth": mouth, "marks": marks})
        samples.append({"t": t, "shot": len(starts) - 1, "faces": faces})
    cap.release()
    return samples, starts


def tracks_of(samples):
    """Greedy per-shot face tracks: a face joins the track whose last box centre is within 0.6 face widths."""
    tracks = []
    for s in samples:
        live = [tr for tr in tracks if tr["shot"] == s["shot"]]
        for f in s["faces"]:
            x, y, w, h = f["box"]
            cx, cy = x + w / 2, y + h / 2
            best = min(live, key=lambda tr: abs(tr["cx"] - cx) + abs(tr["cy"] - cy), default=None)
            if best is None or abs(best["cx"] - cx) + abs(best["cy"] - cy) > 0.6 * w or best["last_t"] == s["t"]:
                best = {"shot": s["shot"], "pts": [], "cx": cx, "cy": cy, "last_t": None, "prev": None}
                tracks.append(best)
                live.append(best)
            act = 0.0
            if f["mouth"] is not None and best["prev"] is not None:
                act = float(abs(f["mouth"] - best["prev"]).mean())
            best["pts"].append({"t": s["t"], "box": f["box"], "act": act})
            best["prev"] = f["mouth"]
            best["cx"], best["cy"], best["last_t"] = cx, cy, s["t"]
    for tr in tracks:
        bs = sorted(p["box"][3] for p in tr["pts"])
        tr["h"] = bs[len(bs) // 2]
    return tracks


def med_box(pts):
    xs = lambda k: sorted(p["box"][k] for p in pts)[len(pts) // 2]
    return xs(0), xs(1), xs(2), xs(3)


def span_box(pts):
    """Where the face goes over the whole turn (10th-90th percentile of its edges): the crop must hold all of it,
    so a speaker who leans stays whole instead of drifting out of a crop fixed on the median."""
    q = lambda v, f: sorted(v)[min(len(v) - 1, int(f * len(v)))]
    x0 = q([p["box"][0] for p in pts], 0.1)
    y0 = q([p["box"][1] for p in pts], 0.1)
    x1 = q([p["box"][0] + p["box"][2] for p in pts], 0.9)
    y1 = q([p["box"][1] + p["box"][3] for p in pts], 0.9)
    return x0, y0, x1 - x0, y1 - y0


def panel_bounds(src, a, b, cx):
    """Split-screen shots (two cameras side by side with a divider) must not leak the other panel into the crop.
    Finds a full-height straight vertical edge in the middle third; returns the x-range of the panel holding cx."""
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cols = None
    for t in (a + (b - a) * k / 4 for k in (1, 2, 3)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(cv2.resize(fr, (W, H)), cv2.COLOR_BGR2GRAY)[BANNER:, :].astype("float32")
        gx = abs(g[:, 1:] - g[:, :-1])
        # a divider is an edge on (almost) every row of the same column
        c = (gx > 18).mean(axis=0)
        cols = c if cols is None else cols + c
    cap.release()
    if cols is None:
        return 0, W
    cols = cols / 3
    mid = range(W // 3, 2 * W // 3)
    x = max(mid, key=lambda k: cols[k])
    if cols[x] < 0.6:
        return 0, W
    return (0, x - 14) if cx < x else (x + 16, W)  # the divider line itself stays out too


def frame_on(box, others, lo, hi, min_ch=MIN_CROP_H, span=None):
    """Crop rect (x0, y0, cw, ch) in source px: box's face at FACE_FRAC of the height, centred, inside [lo, hi] x
    [BANNER, H]. Any other face is kept either fully in or fully out: shift first, zoom in if shifting can't."""
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    face_h = h
    if span:
        # centre on the whole movement and make the crop wide/tall enough to hold it with a margin
        x, y, w, h = span
        cx, cy = x + w / 2, y + h / 2
        min_ch = max(min_ch, (w + 0.3 * face_h) / WIN_AR, h + 0.4 * face_h)
    ch = min(max(face_h / FACE_FRAC, min_ch), H - BANNER, (hi - lo) / WIN_AR)
    for _ in range(12):
        cw = ch * WIN_AR
        x0 = min(max(cx - cw / 2, lo), hi - cw)
        y0 = min(max(cy - FACE_Y * ch, BANNER), H - ch)
        clash = [o for o in others if 0 < max(0, min(x0 + cw, o[0] + o[2]) - max(x0, o[0])) < o[2] * 0.97]
        if not clash:
            return x0, y0, cw, ch
        # try sliding so each clashing face is fully out (or fully in) while our face keeps a margin
        for o in clash:
            for nx in (o[0] + o[2] + 2, o[0] - cw - 2, o[0] - 4, o[0] + o[2] - cw + 4):
                nx = min(max(nx, lo), hi - cw)
                if nx + 0.08 * w <= x and x + w + 0.08 * w <= nx + cw and \
                        not [p for p in others if 0 < max(0, min(nx + cw, p[0] + p[2]) - max(nx, p[0])) < p[2] * 0.97]:
                    return nx, y0, cw, ch
        if face_h / ch > 0.55 or ch <= MIN_CROP_H or (span and ch * WIN_AR < span[2] + 0.2 * face_h):
            return x0, y0, cw, ch      # the speaker stays whole; a background face may be clipped
        ch = max(MIN_CROP_H, ch * 0.88)
    return x0, y0, ch * WIN_AR, ch


def plan_crops(src, a, b):
    """Per camera shot, and per speaker turn inside a shot, the crop that keeps the active speaker whole and
    centred. Active speaker = the big face whose mouth moves most (smoothed over ~1.5 s). Wide shots with no
    usable face keep the widest crop that fits the window."""
    samples, starts = detect_faces(src, a, b)
    tracks = tracks_of(samples)
    segs = []
    for si, s0 in enumerate(starts):
        s1 = starts[si + 1] if si + 1 < len(starts) else b
        mine = [tr for tr in tracks if tr["shot"] == si and len(tr["pts"]) >= 2]
        if not mine:
            cx = segs[-1]["cx"] if segs else W / 2
            ch = H - BANNER
            cw = min(W, ch * WIN_AR)
            segs.append({"start": s0, "end": s1, "rect": (min(max(cx - cw / 2, 0), W - cw), BANNER, cw, cw / WIN_AR),
                         "cx": cx, "faces": 0, "lo": 0, "hi": W})
            continue
        top = max(tr["h"] for tr in mine)
        if top < 0.075 * H:
            # a wide/establishing shot (the whole circle): stay wide, centred on the people, instead of blowing up a
            # 40 px face into mush
            xs = sorted(p["box"][0] + p["box"][2] / 2 for tr in mine for p in tr["pts"])
            cx = xs[len(xs) // 2]
            ch = H - BANNER
            cw = min(W, ch * WIN_AR)
            segs.append({"start": s0, "end": s1, "rect": (min(max(cx - cw / 2, 0), W - cw), BANNER, cw, cw / WIN_AR),
                         "cx": cx, "faces": 0, "lo": 0, "hi": W})
            continue
        major = [tr for tr in mine if tr["h"] >= 0.5 * top]
        # who talks when: per sample, the major face with the most mouth motion; majority over a 1.5 s window
        ts = sorted({p["t"] for tr in major for p in tr["pts"]})
        raw = []
        for t in ts:
            here = [(p["act"], k) for k, tr in enumerate(major) for p in tr["pts"] if p["t"] == t]
            raw.append(max(here)[1] if here else None)
        who = []
        for k, t in enumerate(ts):
            win = [raw[j] for j in range(len(ts)) if abs(ts[j] - t) <= 0.75 and raw[j] is not None]
            who.append(max(set(win), key=win.count) if win else None)
        turns = []
        for t, k in zip(ts, who):
            if turns and (turns[-1][1] == k or k is None):
                continue
            turns.append([t, k])
        if not turns:
            turns = [[s0, 0]]
        turns[0][0] = s0
        # a turn shorter than 1.2 s is noise: fold it into the one before
        clean = []
        for k, (t, idx) in enumerate(turns):
            t_end = turns[k + 1][0] if k + 1 < len(turns) else s1
            if clean and t_end - t < 1.2:
                continue
            if clean and clean[-1][1] == idx:
                continue
            clean.append([t, idx])
        for k, (t, idx) in enumerate(clean):
            t_end = clean[k + 1][0] if k + 1 < len(clean) else s1
            tr = major[idx]
            pts = [p for p in tr["pts"] if t - 0.2 <= p["t"] <= t_end + 0.2] or tr["pts"]
            box = med_box(pts)
            others = [med_box(o["pts"]) for o in mine if o is not tr]
            lo, hi = panel_bounds(src, t, t_end, box[0] + box[2] / 2)
            # a table/medium-wide shot of several small faces stays medium-wide: mouth motion on a 150 px face is
            # too noisy to bet a tight crop on it, and the viewer needs to see who is talking to whom
            min_ch = 0.85 * (H - BANNER) if len(major) >= 2 and top < 0.2 * H else MIN_CROP_H
            segs.append({"start": t, "end": t_end, "rect": frame_on(box, others, lo, hi, min_ch, span_box(pts)),
                         "cx": box[0] + box[2] / 2, "faces": len(major), "lo": lo, "hi": hi,
                         "speaker": [round(v, 1) for v in box]})
    return [repair(sg, samples) for sg in segs]


# ---- crop audit: the finished reel is judged by reel_qa (faces cut off, faces under the right button rail, no face
# for too long). Those rules only depend on where each face lands in the footage window, so every planned crop is
# checked against the tracked faces of its own time span, in source pixels, before anything renders. A crop that
# would fail is replaced by the nearest one (shift, then zoom out, or in on a wide shot) that passes.
QA_MIN_FACE = 80           # reel_qa ignores faces under 80 px on the canvas and counts those frames as face-less
QA_RAIL = (910, 800)       # union of the apps' right button rails on the 1080x1920 canvas: x > 910 from y 800


def audit(rect, samples):
    """(violations, faceless) for one crop over its samples, mirroring reel_qa.check's face rules."""
    x0, y0, cw, ch = rect
    sx, sy = WIN[2] / cw, WIN[3] / ch
    bad = faceless = 0
    for smp in samples:
        vis = []
        for f in smp["faces"]:
            x, y, w, h = f["box"]
            ov = max(0, min(x + w, x0 + cw) - max(x, x0)) * max(0, min(y + h, y0 + ch) - max(y, y0))
            if ov > 0.3 * w * h and h * sy >= QA_MIN_FACE:
                vis.append(f)
        if not vis:
            faceless += 1
            continue
        big = max(f["box"][3] for f in vis)
        hit = False
        for f in vis:
            x, y, w, h = f["box"]
            if h < 0.6 * big:
                continue
            m = 0.08 * w  # QA's 4% plus a margin: detection on the upscaled render lands a few px off the source's
            marks = f.get("marks") or [(x + w / 2, y + h / 2)]
            if any(px < x0 + m or px > x0 + cw - m or py < y0 + m or py > y0 + ch - m for px, py in marks):
                hit = True
            elif max(x0 - x, x + w - (x0 + cw)) / w > 0.1 or max(y0 - y, y + h - (y0 + ch)) / h > 0.1:
                hit = True
            elif any((px - x0) * sx > QA_RAIL[0] - 40 and WIN[1] + (py - y0) * sy > QA_RAIL[1] - 40 for px, py in marks):
                hit = True
        bad += hit
    return bad, faceless


def repair(seg, samples):
    """Keep the planned crop when it passes the audit; otherwise search nearby crops (same zoom shifted, zoomed out,
    face placed higher to clear the rail; zoomed in when faces are too small to count) and take the one with the
    fewest failing samples, then the fewest face-less ones, then the least change from the plan."""
    mine = [p for p in samples if seg["start"] - 0.05 <= p["t"] <= seg["end"] + 0.05]
    if not mine:
        return seg
    x0, y0, cw, ch = seg["rect"]
    bad, fl = audit(seg["rect"], mine)
    if not bad and fl <= 0.1 * len(mine):
        return seg
    lo, hi = seg.get("lo", 0), seg.get("hi", W)
    max_ch = min(H - BANNER, (hi - lo) / WIN_AR)
    sp = seg.get("speaker")
    fcx, fcy = (sp[0] + sp[2] / 2, sp[1] + sp[3] / 2) if sp else (x0 + cw / 2, y0 + 0.4 * ch)
    inside = lambda r: r[0] <= fcx <= r[0] + r[2] and r[1] <= fcy <= r[1] + r[3]
    best = (bad * 10 + fl * 6, 0.0, seg["rect"])
    # tighter zooms first matter for wide shots, where every face is ~65 px and reads as no face at all on the reel
    for f in (1.0, 1.12, 0.85, 1.25, 0.7, 1.4, 0.6, 1.6, 0.5, 1.85, 0.43, 2.2, 9):
        c_h = min(max(ch * f, MIN_CROP_H), max_ch)
        c_w = c_h * WIN_AR
        xs = {min(max(x, lo), hi - c_w) for x in [fcx - c_w * k for k in (0.5, 0.42, 0.35, 0.58)] +
              [lo + (hi - lo - c_w) * k / 16 for k in range(17)]}
        # rows above BANNER (where Jubilee burns in its question) only when a head reaches up into them: the
        # overlay OCR still rejects a clip whose crop then shows that text
        ys = {min(max(fcy - c_h * k, floor), H - c_h) for k in (0.4, 0.33, 0.27, 0.47, 0.55) for floor in (BANNER, 0)}
        for nx in xs:
            for ny in ys:
                r = (nx, ny, c_w, c_h)
                if sp and not inside(r):
                    continue  # the fix never drops the speaker to save a background face
                b, fl2 = audit(r, mine)
                # tie-breaks: stay close to the plan's zoom, keep the speaker near the centre
                change = abs(c_h / ch - 1) + abs((fcx - nx) / c_w - 0.5) + (1 if ny < BANNER else 0)
                score = (b * 10 + fl2 * 6, change)
                if score < best[:2]:
                    best = (score[0], change, r)
        if best[0] == 0:
            break
    if best[2] != seg["rect"]:
        seg = dict(seg, rect=tuple(best[2]), repaired=[bad, fl, best[0]])
    return seg


def overlay_seconds(src, segs, a, b):
    """Seconds where edited-in text (fact checks, lower-thirds, lists) sits inside the visible crop.
    OCRs exactly what the viewer will see, 2 frames a second.
    A word needs 3+ letters at 75+ confidence; a frame counts at 4+ words (T-shirt print and set props stay under that)."""
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    hits = []
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "f.png")
        times = [a + 0.5 * k for k in range(int((b - a) / 0.5) + 1)] + [b - 0.05]  # always the final (freeze) frame
        for t in times:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.resize(frame, (W, H))
            x0, y0, cw, ch = next((s["rect"] for s in reversed(segs) if s["start"] <= t), segs[0]["rect"])
            cv2.imwrite(png, frame[int(y0):int(y0 + ch), int(x0):int(x0 + cw)])
            tsv = subprocess.run(["tesseract", png, "stdout", "--psm", "11", "tsv"], capture_output=True, text=True, errors="replace").stdout
            # confident words only: a patterned shirt or a brick wall reads as "who ERE sod" at low confidence
            words = [c[11] for c in (l.split("\t") for l in tsv.splitlines()[1:])
                     if len(c) == 12 and re.fullmatch(r"[A-Za-z]{3,}[!?.,:]?", c[11].strip() or "-") and float(c[10]) >= 75]
            if len(words) >= 4:
                hits.append(round(t - a, 1))
    cap.release()
    return hits


def cut_video(job, src, dst):
    t0 = job["source"]["t0"]
    # the video stream can end before the audio (a yt-dlp section download cut short): trim to the shorter one, or
    # ffmpeg's trim hands concat an empty segment and dies with "sending frames to consumers: Invalid argument"
    probe = sh(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration:format=duration", "-of", "json",
                str(src)]).stdout
    meta = json.loads(probe)
    ends = [float(st["duration"]) for st in meta.get("streams", []) if st.get("duration") not in (None, "N/A")]
    end = min(ends + [float(meta["format"]["duration"])])
    a, b = job["start"] - t0, min(job["end"] - t0 + 0.35, end - 0.1)
    if b - a < 0.75 * (job["end"] - job["start"]):
        raise Rejected(f"source section is cut short ({end:.1f}s of video for a {job['end'] - job['start']:.0f}s exchange)")
    # the crop plan is the slow part (face tracking at 6 fps); both hook variants of a job share it
    cache = pathlib.Path(src).parent / "crops.json"
    stamp = [CROPS_VERSION, a, b, os.path.getmtime(src)]
    segs = json.loads(cache.read_text()).get("segs") if cache.exists() and json.loads(cache.read_text()).get("stamp") == stamp else None
    if segs is None:
        segs = plan_crops(src, a, b)
        cache.write_text(json.dumps({"stamp": stamp, "segs": segs}))
    hits = overlay_seconds(src, segs, a, b)
    if len(hits) >= 2:
        raise Rejected(f"edited-in text on screen at {hits[:8]}s")
    bounds = [max(a, s["start"]) for s in segs] + [b]
    bounds[0] = a
    vf, labels = [], []
    for i, s in enumerate(segs):
        s0, s1 = bounds[i], bounds[i + 1]
        if s1 - s0 < 0.05:
            continue
        x0, y0, cw, ch = (int(round(v)) for v in s["rect"])
        cw -= cw % 2
        ch -= ch % 2
        vf.append(f"[0:v]trim={s0:.3f}:{s1:.3f},setpts=PTS-STARTPTS,scale={W}:{H},crop={cw}:{ch}:{x0}:{y0},"
                  f"scale={WIN[2]}:{WIN[3]}:flags=lanczos,unsharp=5:5:0.5,fps=30,setsar=1[v{i}]")
        labels.append(f"[v{i}]")
    graph = ";".join(vf) + f";{''.join(labels)}concat=n={len(labels)}:v=1:a=0[v];" \
            f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,loudnorm=I=-14:TP=-1.5[a]"
    sh(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(dst)])
    return round(b - a, 2), len(labels)


def finish(raw, dst):
    """Platform master: H.264 High 1080x1920 30 fps ~10 Mbps (encoded by HyperFrames), audio two-pass
    loudnorm to -14 LUFS / -1 dBTP (what IG, TikTok and Shorts normalise toward), AAC 48 kHz, faststart."""
    m = sh(["ffmpeg", "-hide_banner", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-2:LRA=11:print_format=json",
            "-f", "null", "-"]).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    # loudnorm alone left 6 of 45 10/3 masters at -0.9 to 0.0 dBTP after AAC (spec -1); a 4x-oversampled limiter at
    # -3 dBFS brings all under -1.5 dBTP and moves loudness by <= 0.2 LU (tested on the Air 10/3, account-safety audit)
    ln = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,"
          "aresample=192000,alimiter=limit=0.7:attack=1:release=50:level=0,aresample=48000")
    sh(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af", ln,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(dst)])


def qa(mp4):
    """The shared reel QA gate (reel_qa.py), against the union of IG/TikTok/Shorts safe zones."""
    d = next((d for d in QA_DIRS if os.path.exists(os.path.join(d, "reel_qa.py"))), None)
    if not d:
        raise RuntimeError("reel_qa.py not found; refusing to file an unchecked render")
    sys.path.insert(0, d)
    import reel_qa
    return reel_qa.check(str(mp4), "all")


def name_of(job, side):
    return job["a_name"] if side == "A" else job["b_name"]


def verdict_bits(job):
    j = job["judge_response"]["judgment"]
    avg = job["judge_response"]["averageScores"]
    a, b = avg["participantA"], avg["participantB"]
    win = "A" if a >= b else "B"
    sub = lambda s: s.replace("Debater A", job["a_name"]).replace("Debater B", job["b_name"])
    reason = sub(j["reasoning"])
    first = re.split(r"(?<=[.!?])\s+", reason)[0]
    if len(first) > 190:  # keep it a real quote: cut at a clause boundary and mark the cut
        cut = max(first.rfind(", ", 0, 185), first.rfind("—", 0, 185), first.rfind(" — ", 0, 185))
        first = first[: cut if cut > 80 else 185].rstrip(" ,—") + "…"
    return {"win": win, "w": name_of(job, win), "l": name_of(job, "B" if win == "A" else "A"),
            "ws": max(a, b), "ls": min(a, b), "quote": f"“{first}”"}


def gold_side(job):
    """The named person keeps gold in every clip (Ben is always gold); a described opponent is white."""
    named = lambda n: len(n.split()) >= 2 and all(w[:1].isupper() for w in n.split())
    a, b = named(job["a_name"]), named(job["b_name"])
    return "a" if a and not b else "b"


CAPSYNC_PY = [os.path.expanduser(p) for p in (os.environ.get("CAPSYNC_PY", ""), "~/render/capsync/venv/bin/python",
                                                "~/.arena/capsync/venv/bin/python") if p]


def capsync_dir():
    d = next((d for d in QA_DIRS if os.path.exists(os.path.join(d, "capsync.py"))), None)
    py = next((p for p in CAPSYNC_PY if os.path.exists(p)), None)
    if not d or not py:
        raise RuntimeError("capsync.py / its venv not found; refusing to caption from YouTube timings")
    return d, py


def spoken_words(job, cut):
    """Every word as spoken in the clip's own audio (cut.mp4, t=0 = job start): faster-whisper words re-timed by
    wav2vec2 forced alignment (capsync.py). 10/1: YouTube caption / transcript timings put captions seconds off."""
    d, py = capsync_dir()
    # no initial prompt: on crosstalk a names prompt made whisper drop one speaker's words (2S-WJN3L5eo_1532, 10/1),
    # and the QA gate transcribes the same way, so render and gate hear the clip alike
    r = sh([py, os.path.join(d, "capsync.py"), "words", str(cut)], timeout=900)
    return json.loads(r.stdout.strip().splitlines()[-1])


def aligned_words(job, spoken):
    """Caption words = the words actually spoken, at their aligned times. Codex's line text only lends the speaker
    and its spelling (e.g. "Kamala" where whisper hears "Camela"); a Codex word nobody said is dropped."""
    d, _ = capsync_dir()
    sys.path.insert(0, d)
    import capsync
    norm = capsync.norm
    mine = [(w, l["speaker"]) for l in job["lines"] for w in l["text"].split() if norm(w)]
    pairs = capsync.align_seq([norm(w) for w, _ in mine], [norm(w["w"]) for w in spoken])
    back = {j: i for i, j in pairs.items()}
    line_of = [k for k, l in enumerate(job["lines"]) for w in l["text"].split() if norm(w)]
    out, spk, ln = [], None, 0
    for j, w in enumerate(spoken):
        if not norm(w["w"]):
            continue
        i = back.get(j)
        if i is not None:
            spk, ln = mine[i][1], line_of[i]
        elif spk is None:  # before the first matched word: whoever owns the next matched one
            spk = next((mine[back[k]][1] for k in range(j, len(spoken)) if k in back), job["lines"][0]["speaker"])
        text = mine[i][0] if i is not None and norm(mine[i][0]) == norm(w["w"]) else w["w"]
        out.append({"t": w["t"] + job["start"], "e": w["e"] + job["start"], "w": text, "s": spk, "l": ln})
    return out


def frame(t):
    """The first frame that shows an event set at t, rounded DOWN at 3 places (sfx_map.frame: 12.666, never 12.667)."""
    import math
    return math.floor(math.ceil(t * 30 - 1e-4) / 30 * 1e3 + 1e-6) / 1e3


def kill_span(words, kill, lines=None):
    """(first, last) index of the payoff: the kill phrase where it is said as a phrase; else the closest run of
    spoken words (whisper hears "not going to be a part" where the transcript had "not be a part"); else, with
    `lines`, every word of the transcript line that holds the phrase. None when it is not in these words."""
    import difflib
    norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    kp = [norm(k) for k in (kill or "").split() if norm(k)]
    if not kp or not words:
        return None
    toks = [norm(w["w"]) for w in words]
    for i in range(len(toks) - len(kp) + 1):
        if toks[i:i + len(kp)] == kp:
            return i, i + len(kp) - 1
    best = (0.0, None)
    for n in (len(kp), len(kp) + 1, len(kp) + 2, len(kp) - 1):
        for i in range(max(0, len(toks) - n + 1)):
            if n < 2:
                continue
            r = difflib.SequenceMatcher(None, " ".join(toks[i:i + n]), " ".join(kp)).ratio()
            if r > best[0]:
                best = (r, (i, i + n - 1))
    if best[0] >= 0.8:
        return best[1]
    if lines is not None:
        flat = lambda t: " ".join(norm(w) for w in t.split() if norm(w))
        ln = next((k for k, l in enumerate(lines) if " ".join(kp) in flat(l["text"])), None)
        idx = [i for i, w in enumerate(words) if w.get("l") == ln]
        if ln is not None and idx:
            return idx[0], idx[-1]
    return None


def pick_window(words, kill, dur, limit=MAX_CLIP, lines=None):
    """The stretch of the judged exchange that plays before the scorecard: (a, b) in the cut's own seconds.
    It opens and ends on a finished sentence, holds the payoff line (the kill phrase) and both voices where it can,
    and runs `limit` seconds or less where the exchange allows; an exchange already inside the limit plays whole.
    Sentence edges come from the words as spoken (capsync times), never from YouTube caption times."""
    if not words or dur <= limit:
        return 0.0, dur, 0, len(words) - 1
    # a sentence ends where the spoken word carries its full stop (whisper's or the transcript's punctuation); a
    # speaker or line change alone is not an edge: words at a hand-over are often tagged to the wrong side
    ends = [k for k, w in enumerate(words) if k == len(words) - 1 or re.search(r"[.?!][\"')\]]*$", w["w"])]
    starts = [0] + [k + 1 for k in ends[:-1]]
    ks = kill_span(words, kill, lines)
    length = lambda i, j: (words[j]["e"] + TAIL) - max(0.0, words[i]["t"] - LEAD)
    best = None
    for i in starts:
        for j in ends:
            if j <= i:
                continue
            n = length(i, j)
            has_kill = bool(ks and i <= ks[0] and ks[1] <= j)
            both = len({w["s"] for w in words[i:j + 1]}) > 1
            score = 100 * has_kill + 40 * both + min(n, 14.0)
            if has_kill:
                unit_end = next(e for e in ends if e >= ks[1])
                nxt = next((e for e in ends if e > unit_end), None)
                # best ending: the reply right after the payoff, when it is the other voice and short
                if nxt == j and words[j]["s"] != words[ks[1]]["s"] and words[j]["e"] - words[unit_end]["e"] <= 3.5:
                    score += 20
                elif j == unit_end:
                    score += 12
                if words[i]["s"] != words[ks[0]]["s"]:
                    score += 8     # the other side sets it up, then the payoff
            if n > limit:
                score -= 1000 + 10 * (n - limit)   # only when nothing fits: the shortest overrun that keeps the payoff
            elif n < MIN_CLIP:
                score -= 60
            if best is None or score > best[0]:
                best = (score, i, j)
    _, i, j = best
    # never into a neighbour's word: the cut sits in the gap when the next voice comes in at once
    a = max(0.0, words[i]["t"] - LEAD, (words[i - 1]["e"] + 0.02) if i else 0.0)
    b = min(dur, words[j]["e"] + TAIL, (words[j + 1]["t"] - 0.03) if j + 1 < len(words) else dur)
    return min(a, words[i]["t"]), max(b, words[j]["e"]), i, j


def trim_cut(cut, dst, a, b):
    sh(["ffmpeg", "-v", "error", "-y", "-i", str(cut), "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-c:v", "libx264", "-crf", "15",
        "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(dst)])
    return float(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of",
                     "csv=p=0", str(dst)]).stdout.strip())


def captions(job, dur, words):
    """Captions in the measured band from the kept words (cut seconds): up to three words, on screen from the first
    word's onset until the next caption or 0.35 s after the last word; the kill phrase is gold where it is said."""
    norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    ws = [w for w in words if norm(w["w"]) not in ("uh", "um", "") and 0 <= w["t"] < dur]
    ks = kill_span(ws, job["kill_phrase"])
    kill_idx = set(range(ks[0], ks[1] + 1)) if ks else set()
    chunks, cur = [], []
    for i, w in enumerate(ws):
        # words crammed together (crosstalk) stay in one caption up to 5 words rather than flashing 3 captions a second
        crammed = cur and w["t"] - cur[0][1]["t"] < 0.25 and len(cur) < 5
        if cur and not crammed and (len(cur) >= 3 or w["s"] != cur[-1][1]["s"] or w["t"] - cur[-1][1]["t"] > 0.9
                                    or re.search(r"[.?!]$", cur[-1][1]["w"])):
            chunks.append(cur); cur = []
        cur.append((i, w))
    if cur:
        chunks.append(cur)
    caps, tl = [], []
    end = max((w["e"] for w in ws), default=0)
    for n, ch in enumerate(chunks):
        a = ch[0][1]["t"]
        nxt = chunks[n + 1][0][1]["t"] if n + 1 < len(chunks) else end + 0.5
        if n == 0 and a < 0.35:      # the pill never sits empty on the first frames
            a = 0.0
        b = min(nxt, max(ch[-1][1]["e"] + 0.35, a + 0.3), a + 2.5)
        if nxt - b < 0.8 and nxt - a <= 3.0:     # a short pause keeps the last words up: no empty pill between lines
            b = nxt
        b = min(b, dur - 0.02)                   # nothing of the clip stays up under the scorecard
        if b <= a:
            continue
        text = " ".join(f"<b>{html.escape(w['w'])}</b>" if i in kill_idx else html.escape(w["w"]) for i, w in ch)
        size = 84 if sum(len(w["w"]) + 1 for _, w in ch) <= 17 else 68
        caps.append(f'<div class="cap" id="c{n}" style="font-size:{size}px"><span>{text}</span></div>')
        tl.append(f'["#c{n}", {a:.3f}, {b:.3f}]')
    return caps, tl


def fit(text, big, small, limit):
    return big if len(text) <= limit else small


def title_of(job):
    """The promise in words, at full strength on frame 0. Base: "AI ref scored <who> <on what>"; the xwho arm asks
    "<who> <on what>. Who won?" (41_whowon's title). `hook_topic` in job.json is a short hand-written "on ..." that is
    literally true of the kept clip; without it the title is the matchup alone. -> (html, font px)"""
    who = re.sub(r"\s+vs\.?\s+", " vs ", job["matchup"].strip())
    who = who[:1].upper() + who[1:]
    topic = (job.get("hook_topic") or "").strip().rstrip(".?!")
    for tp in (topic, ""):
        mid = f"{who} {tp}".strip()
        plain = f"{mid}. Who won?" if VARIANT == "xwho" else f"AI ref scored {mid}"
        if len(plain) <= 80 or not tp:
            break
    # a name never breaks across the two lines, and "Who won?" stays together
    # <u>, not <span>: the pill is styled by "#title > span" and a nested span must not become a pill of its own
    nb = lambda t: f'<u>{html.escape(t)}</u>'   # nowrap: also holds a hyphenated name together
    sides = [nb(x) for x in who.split(" vs ")]
    em = "<em>" + " vs ".join(sides) + "</em>" + (f" {html.escape(tp)}" if tp else "")
    text = f"{em}. Who&nbsp;won?" if VARIANT == "xwho" else f"AI&nbsp;ref scored {em}"
    return text, (54 if len(plain) <= 50 else 48 if len(plain) <= 60 else 42)


def build(job, dur, d, words):
    v = verdict_bits(job)
    caps, tl = captions(job, dur, words)
    f_card = frame(dur)
    f_ask = frame(f_card + math_floor3(8 * BEAT))
    total = round(f_ask + CTA, 2)
    hook, hook_px = title_of(job)
    sc = job["judge_response"]["judgment"]["scores"]
    avg = job["judge_response"]["averageScores"]
    side = {"A": ("participantA", job["a_name"]), "B": ("participantB", job["b_name"])}
    tie = v["ws"] == v["ls"]    # equal averages: the card says so and crowns nobody (10/6 review: 58 to 58 "wins")
    cell = lambda s_: (f'<div class="p{" w" if s_ == v["win"] and not tie else ""}"><span>{html.escape(side[s_][1])}</span>'
                       f'<div class="big">{avg[side[s_][0]]}</div></div>')
    rows = "".join(
        f'<div class="r"><span>{sc["participantA"][k]}</span><div class="t l"><s class="ref1-a" data-v="{sc["participantA"][k] / 100:.2f}"></s></div>'
        f'<u>{lab}</u><div class="t rr"><s class="ref1-b" data-v="{sc["participantB"][k] / 100:.2f}"></s></div>'
        f'<span class="n2">{sc["participantB"][k]}</span></div>' for k, lab in CATS)
    s = (HERE / "tpl/template.html").read_text()
    rep = {"{{CAPS}}": "\n      ".join(caps), "{{CAPTL}}": ",\n        ".join(tl),
           "{{VIDEO_DUR}}": f"{dur:.3f}", "{{TOTAL}}": f"{total:.2f}", "{{TAIL_DUR}}": f"{total - dur:.3f}",
           "{{F_CARD}}": f"{f_card:.3f}", "{{F_ASK}}": f"{f_ask:.3f}", "{{BED_DUR}}": f"{total - f_card:.3f}",
           "{{BOOM_AT}}": f"{max(0.0, f_card - 0.012):.3f}", "{{CLICK_AT}}": f"{f_ask - 0.0015:.4f}",
           "{{HOOK_HTML}}": hook, "{{HOOK_PX}}": str(hook_px), "{{MOTION}}": html.escape(job["motion"]),
           "{{CELL_A}}": cell("A"), "{{CELL_B}}": cell("B"), "{{ROWS}}": rows,
           "{{CALL}}": "Too close to call" if tie else f'{html.escape(v["w"])} wins',
           "{{CALL_PX}}": str(min(96, int(1640 / (len("Too close to call" if tie else v["w"] + " wins") + 0))))}
    for k, val in rep.items():
        s = s.replace(k, val)
    assert "{{" not in s, re.findall(r"{{\w+}}", s)
    (d / "index.html").write_text(s)
    return v, {"card": f_card, "ask": f_ask, "total": total, "title": html.unescape(re.sub(r"<[^>]+>", "", hook)).replace("\xa0", " ")}


def math_floor3(x):
    import math
    return math.floor(x * 1e3 + 1e-6) / 1e3


def post_txt(job, v):
    # caption gate (ARENA render-farm/caption_gate.py, on the Air in ~/render/farm): never name the winner, the REF's
    # call is the payoff at the end; hashtags = famous names + one topic tag + #debate (Reagan 10/3)
    sys.path[:0] = [str(p) for p in (pathlib.Path.home() / "Documents/ARENA/render-farm",
                                     pathlib.Path.home() / "render/farm") if p.is_dir()]
    from caption_gate import OPEN_LINE, hashtags, problems
    tags = hashtags([job["a_name"], job["b_name"]], job.get("motion"), job.get("matchup"))
    cap = f"{OPEN_LINE} (🎥 {job['source'].get('channel') or 'source'}) {tags}"
    bad = problems(cap, winner=v["w"], loser=v["l"])
    assert not bad, f"caption gate: {bad}: {cap}"
    return (f"MATCHUP: {job['matchup']}\nMOTION: {job['motion']}\n"
            f"REF: {v['w']} {v['ws']} vs {v['l']} {v['ls']}\n"
            f"CAPTION: {cap}\n"
            f"PINNED COMMENT: we built an AI ref that scores debates. you can debate anyone on it, it's called debatetv\n"
            f"SOURCE: {job['source']['title']} ({job['source']['url']}) {job['start']:.0f}s to {job['end']:.0f}s\n")


def wait_for_calm(limit=float(os.environ.get("LOAD_LIMIT", 40)), max_wait=4 * 3600):
    """Other sessions (simulators, builds) can push this Mac's load past 500; a render started then just times out
    (Chrome start, frame extraction). Wait until the 5-minute load average is back under the limit."""
    waited = 0
    while os.getloadavg()[1] > limit and waited < max_wait:
        time.sleep(60)
        waited += 60


def render(jobdir):
    wait_for_calm()
    job = json.loads((jobdir / "job.json").read_text())
    key = job["key"] + SUFFIX
    dst = OUT / key
    dst.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp)
        shutil.copytree(HERE / "assets", p / "assets")
        for f in ("hyperframes.json", "package.json"):
            shutil.copy(HERE / "tpl" / f, p / f)
        full, nshots = cut_video(job, jobdir / "src.mp4", p / "full.mp4")
        spoken = spoken_words(job, p / "full.mp4")
        (dst / "spoken.json").write_text(json.dumps(spoken))
        # every word in the cut's own seconds, with its speaker and line; then the stretch that plays before the card
        words = [dict(w, t=w["t"] - job["start"], e=w["e"] - job["start"]) for w in aligned_words(job, spoken)]
        a, b, i, j = pick_window(words, job["kill_phrase"], full, lines=job["lines"])
        lines = job["lines"]
        if a > 0.01 or b < full - 0.01:
            dur = trim_cut(p / "full.mp4", p / "assets/cut.mp4", a, b)
            # caption times come from the audio that plays: the gate transcribes the short cut, and on crosstalk
            # whisper hears a short cut differently from the long one (10/6: 2 of 14 renders drifted 165 to 247 ms)
            lines = job["lines"][min(w["l"] for w in words[i:j + 1]):max(w["l"] for w in words[i:j + 1]) + 1]
            heard = aligned_words(dict(job, lines=lines), spoken_words(job, p / "assets/cut.mp4"))
            words = [dict(w, t=max(0.0, w["t"] - job["start"]), e=w["e"] - job["start"]) for w in heard]
        else:
            shutil.move(p / "full.mp4", p / "assets/cut.mp4")
            dur = full
            words = [dict(w, t=max(0.0, w["t"] - a), e=w["e"] - a) for w in words[i:j + 1]]
        dur = math_floor3(int(dur * 30 + 1e-6) / 30)    # whole frames: the scorecard lands on the frame the clip ends
        sh(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.2", "-i", str(p / "assets/cut.mp4"), "-frames:v", "1", "-q:v", "2", str(p / "assets/freeze.jpg")])
        v, marks = build(job, dur, p, words)
        # 1 Chrome worker: with 2, HyperFrames 0.8.85 drops the bottom ~90 px of a <video> layer (the blurred plate)
        for attempt in range(4):  # under heavy load headless Chrome can time out just starting; that is not the clip's fault
            try:
                sh([*HF, "render", "-o", str(p / "raw.mp4"), "--video-bitrate", "10M", "--workers", "1", "--quiet"], cwd=p, timeout=1800)
                break
            except RuntimeError as e:
                if "Chrome cannot start" not in str(e) or attempt == 3:
                    raise
                time.sleep(90)
        final = dst / f"{key}.mp4"
        finish(p / "raw.mp4", final)
    (dst / f"{key}.layout.json").write_text(json.dumps({"window": list(WIN), "clip_end": dur, "captions": list(BAND)}))
    (dst / "cut.json").write_text(json.dumps({"exchange_s": full, "kept": [round(a, 2), round(b, 2)], "clip_s": dur, **marks,
                                              "both_voices": len({w["s"] for w in words}) > 1,
                                              "payoff_in": bool(kill_span(words, job["kill_phrase"], lines))}))
    (dst / "post.txt").write_text(post_txt(job, v))
    r = qa(final)
    (dst / "qa.json").write_text(json.dumps(r, indent=1))
    if not r["ok"]:
        final.rename(final.with_name(f"{key}.qa-fail.mp4"))  # kept for a look, never staged (REJECTED.txt)
        raise Rejected("QA: " + "; ".join(r["fails"]))
    # HyperFrames' extract cache grows ~100 MB per render; the Mac has no disk to spare
    for c in pathlib.Path(os.environ.get("TMPDIR", "/tmp")).glob("hyperframes-extract-cache-*"):
        shutil.rmtree(c, ignore_errors=True)
    print(f"{key}: {dur}s of {full}s, {nshots} crops, {v['w']} {v['ws']}–{v['ls']}, QA pass {r['stats']}", file=sys.stderr)


def claim_all():
    """Queue mode for many workers sharing jobs/ + out/: a job is claimed by atomically creating
    out/<key>/ (mkdir fails if another worker got it first), so nothing renders twice."""
    for jobdir in sorted((HERE / "jobs").iterdir()):
        if not (jobdir / "job.json").exists():
            continue
        try:
            (OUT / (jobdir.name + SUFFIX)).mkdir(parents=True)
        except FileExistsError:
            continue
        yield str(jobdir)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for arg in (claim_all() if sys.argv[1:] == ["--queue"] else sys.argv[1:]):
        try:
            render(pathlib.Path(arg))
        except Rejected as e:
            key = pathlib.Path(arg).name + SUFFIX
            (OUT / key).mkdir(parents=True, exist_ok=True)
            (OUT / key / "REJECTED.txt").write_text(str(e) + "\n")
            print(f"REJECTED {key}: {e}", file=sys.stderr)
        except Exception as e:  # one bad job must not stop the batch
            print(f"FAILED {arg}: {e}", file=sys.stderr)
