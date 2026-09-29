"""REF-judge engine, step 1 (runs on the Mac): a full debate video -> self-contained render jobs.

  python3 brain.py <youtube url> [--max 12]

For each clash Codex finds in the transcript:
  jobs/<videoid>_<start>/job.json  (lines, speakers, word timings, REF verdict)
  jobs/<videoid>_<start>/src.mp4   (only that section of the video)
Workers (render.py, Docker) need nothing else, so they never touch YouTube.
The verdict is the production REF: debatetvbackend /judge with no roomId (no DB writes).
"""
import argparse, json, pathlib, re, subprocess, sys, tempfile, time, urllib.request

HERE = pathlib.Path(__file__).parent
JOBS = HERE / "jobs"
LEDGER = HERE / "ledger.json"
JUDGE = "https://debatetvbackend-production.up.railway.app/judge"
PAD = 0.6  # seconds of source kept either side of the exchange

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["exchanges"],
    "properties": {"exchanges": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["start", "end", "motion", "matchup", "a_name", "b_name", "kill_phrase", "lines"],
        "properties": {
            "start": {"type": "number"}, "end": {"type": "number"},
            "motion": {"type": "string"}, "matchup": {"type": "string"},
            "a_name": {"type": "string"}, "b_name": {"type": "string"},
            "kill_phrase": {"type": "string"},
            "lines": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["speaker", "start", "text"],
                "properties": {"speaker": {"type": "string", "enum": ["A", "B"]}, "start": {"type": "number"}, "text": {"type": "string"}}}},
        }}}},
}

PROMPT = """Read transcript.txt. It is the auto-caption transcript of a debate video titled "{title}" (channel: {channel}).
Each line starts with its time in seconds.

Find {n} separate exchanges (fewer only if the video truly runs out) that would work as a 20-45 second viral clip:
two people clash on one clear question, and one of them lands a sharp point, gotcha or comeback.
Each exchange must make sense on its own with no context. No overlapping exchanges.

For each exchange give:
- start / end in seconds (start at the first word of the question, end right after the last word of the payoff)
- motion: the question they are arguing, as a short yes/no question
- a_name / b_name: A = the person who speaks first. Use real names only when the title or transcript makes them certain (e.g. the famous host named in the title). Otherwise use a short description like "Harris voter" or "Student".
- matchup: short, like "Ben Shapiro vs a Harris voter"
- lines: every sentence in order, speaker A or B, its start time, and the text copied from the transcript (you may fix obvious caption typos)
- kill_phrase: the 2-6 exact words that land the hardest

Only return the JSON."""


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def vtt_words(path):
    """YouTube auto-subs carry a timestamp on every word (<00:01:02.345><c> word</c>)."""
    def ts(s):
        h, m, x = s.split(":"); return int(h) * 3600 + int(m) * 60 + float(x)
    words = []
    for blk in path.read_text().split("\n\n"):
        m = re.search(r"(\d\d:\d\d:\d\d\.\d+) -->", blk)
        if not m or "<c>" not in blk:
            continue
        line = [l for l in blk.split("\n") if "<c>" in l][0]
        first = re.match(r"([^<]+)<", line)
        if first and first.group(1).strip():
            words.append((ts(m.group(1)), first.group(1).strip()))
        for t, w in re.findall(r"<(\d\d:\d\d:\d\d\.\d+)><c>\s*([^<]*)</c>", line):
            if w.strip():
                words.append((ts(t), w.strip()))
    return words


def fetch(url, work):
    info = json.loads(run(["yt-dlp", "--no-warnings", "-J", "--skip-download", url]).stdout)
    for attempt in range(5):  # YouTube 429s the caption endpoint when several brains run at once
        try:
            run(["yt-dlp", "--no-warnings", "-q", "--skip-download", "--write-auto-subs", "--sub-langs", "en",
                 "--sub-format", "vtt", "-o", str(work / "subs"), url])
            break
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            time.sleep(45 * (attempt + 1))
    vtt = next(work.glob("subs*.vtt"))
    return info, vtt_words(vtt)


def transcript_text(words):
    lines, cur, t0 = [], [], None
    for t, w in words:
        if t0 is None:
            t0 = t
        cur.append(w)
        if t - t0 > 8 and w[-1:] in ".?!" or t - t0 > 14:
            lines.append(f"{t0:.1f} {' '.join(cur)}"); cur, t0 = [], None
    if cur:
        lines.append(f"{t0:.1f} {' '.join(cur)}")
    return "\n".join(lines)


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def snap(words, t, text):
    """Move a line start onto the real caption word it begins with (Codex rounds times)."""
    first = [norm(x) for x in text.split()[:2] if norm(x)]
    best = None
    for i, (wt, w) in enumerate(words):
        if abs(wt - t) > 4 or not first or norm(w) != first[0]:
            continue
        if len(first) > 1 and i + 1 < len(words) and norm(words[i + 1][1]) != first[1]:
            continue
        if best is None or abs(wt - t) < abs(best - t):
            best = wt
    return best if best is not None else t


def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return "audio" in r.stdout


def download_section(url, t0, t1, dst):
    """yt-dlp sometimes returns a section with the audio missing; try formats until it has sound."""
    for fmt in ("bv*[height<=1080][ext=mp4]+ba[ext=m4a]", "bv*[height<=1080]+ba", "b"):
        dst.unlink(missing_ok=True)
        subprocess.run(["yt-dlp", "--no-warnings", "-q", "-f", fmt, "--download-sections", f"*{t0:.2f}-{t1:.2f}",
                        "--force-keyframes-at-cuts", "--merge-output-format", "mp4", "-o", str(dst), url],
                       capture_output=True, text=True)
        if dst.exists() and has_audio(dst):
            return
    raise RuntimeError(f"no section with audio for {url} {t0}-{t1}")


def judge(ex):
    body = {"topic": ex["motion"], "category": "debate",
            "creatorStance": ex["a_name"], "opponentStance": ex["b_name"],
            "transcript": [{"speaker": l["speaker"], "text": l["text"]} for l in ex["lines"]]}
    req = urllib.request.Request(JUDGE, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return body, json.load(urllib.request.urlopen(req, timeout=180))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}

    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        info, words = fetch(a.url, work)
        vid, title, channel = info["id"], info.get("title", ""), info.get("channel", "")
        print(f"{vid}: {title} — {len(words)} caption words", file=sys.stderr)
        (work / "transcript.txt").write_text(transcript_text(words))
        (work / "schema.json").write_text(json.dumps(SCHEMA))
        out = work / "exchanges.json"
        subprocess.run(["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(work),
                        "--output-schema", str(work / "schema.json"), "-o", str(out),
                        PROMPT.format(title=title, channel=channel, n=a.max)],
                       check=True, capture_output=True, text=True, timeout=1800)
        exchanges = json.loads(out.read_text())["exchanges"]

    made = 0
    for ex in exchanges:
        key = f"{vid}_{int(ex['start'])}"
        if key in ledger or not (15 <= ex["end"] - ex["start"] <= 60) or len({l["speaker"] for l in ex["lines"]}) < 2:
            print(f"skip {key}", file=sys.stderr); continue
        for l in ex["lines"]:
            l["start"] = snap(words, l["start"], l["text"])
        ex["start"] = ex["lines"][0]["start"]  # open on the question itself, never on leftover words
        # caption words for this exchange, each tagged with whoever's line it falls in
        span = [(t, w) for t, w in words if ex["start"] - 0.05 <= t <= ex["end"] + 0.05]
        starts = [(l["start"], l["speaker"]) for l in ex["lines"]]
        cap = [{"t": round(t, 2), "w": w, "s": max([s for s in starts if s[0] <= t + 0.05] or [starts[0]])[1]} for t, w in span]
        req, verdict = judge(ex)
        if not verdict.get("success"):
            print(f"judge failed {key}", file=sys.stderr); continue
        d = JOBS / key
        d.mkdir(parents=True, exist_ok=True)
        t0 = max(0, ex["start"] - PAD)
        download_section(a.url, t0, ex["end"] + PAD, d / "src.mp4")
        job = {"key": key, "source": {"url": a.url, "id": vid, "title": title, "channel": channel, "t0": round(t0, 2)},
               **ex, "words": cap, "judge_request": req, "judge_response": verdict}
        (d / "job.json").write_text(json.dumps(job, indent=1))
        ledger[key] = {"title": title, "motion": ex["motion"]}
        LEDGER.write_text(json.dumps(ledger, indent=1))
        made += 1
        print(f"job {key}: {ex['matchup']} — {ex['motion']}", file=sys.stderr)
    print(f"{made} jobs from {len(exchanges)} exchanges", file=sys.stderr)


if __name__ == "__main__":
    main()
