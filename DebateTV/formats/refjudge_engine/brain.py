"""REF-judge engine, step 1 (runs on the Mac): a full debate video -> self-contained render jobs.

  python3 brain.py <youtube url> [--max 12]

For each clash the picker finds in the transcript:
  jobs/<videoid>_<start>/job.json  (lines, speakers, word timings, REF verdict, why the moment holds a viewer)
  jobs/<videoid>_<start>/src.mp4   (only that section of the video)
Workers (render.py, Docker) need nothing else, so they never touch YouTube.
The verdict is the production REF: debatetvbackend /judge with no roomId (no DB writes).

The picker (10/7, ask a158: "Clips are picked as real debates for retention, not scraped at random for volume"):
Codex first whenever it answers; while it is out of usage (~/.render-farm/codex_out.json holds the time it gave),
`claude -p` on a Claude login with room (ARENA chat/accounts.py pick, Opus 5.5 for the pick, Haiku 4.5 for bulk
passes). Same prompt, same schema, same exchanges.json either way. It first rules on the video itself (two people
arguing opposite sides, or nothing is cut), returns only exchanges where both sides make their case, and writes
beside each one the reason a viewer stays. check() then throws out anything the transcript does not back.
  python3 brain.py <url> --dry     # the picks and their reasons, nothing judged, downloaded or filed
"""
import argparse, datetime, fcntl, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, urllib.request

HERE = pathlib.Path(__file__).parent
JOBS = HERE / "jobs"
LEDGER = HERE / "ledger.json"
JUDGE = "https://debatetvbackend-production.up.railway.app/judge"
PAD = 0.6  # seconds of source kept either side of the exchange
# the Codex config default can be a model a ChatGPT login cannot use ("gpt-6.1-sol", 9/30): name it explicitly
MODEL = os.environ.get("BRAIN_MODEL", "gpt-5.5")
# the picker when Codex is out. "pick" reads a whole transcript and judges what holds a viewer; "bulk" sorts titles.
CLAUDE_MODELS = {"pick": os.environ.get("BRAIN_CLAUDE_MODEL", "claude-opus-5-5"),
                 "bulk": os.environ.get("BRAIN_CLAUDE_BULK", "claude-haiku-4-5-20251001")}
CLAUDE = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")  # launchd's PATH has no ~/.local/bin
ACCOUNTS = os.path.expanduser("~/Documents/ARENA/chat/accounts.py")
CODEX_OUT = pathlib.Path(os.path.expanduser("~/.render-farm/codex_out.json"))
AIR = os.environ.get("BRAIN_AIR", "air")  # ssh host of the render farm: the second route for section downloads
PICKER = os.environ.get("BRAIN_PICKER", "auto")  # auto = Codex first, Claude when it is out; or codex / claude

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["debate", "exchanges"],
    "properties": {
        "debate": {"type": "object", "additionalProperties": False, "required": ["two_sided", "why"],
                   "properties": {"two_sided": {"type": "boolean"}, "why": {"type": "string"}}},
        "exchanges": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["start", "end", "motion", "matchup", "a_name", "b_name", "a_side", "b_side", "hook_topic",
                         "kill_phrase", "retention", "lines"],
            "properties": {
                "start": {"type": "number"}, "end": {"type": "number"},
                "motion": {"type": "string"}, "matchup": {"type": "string"},
                "a_name": {"type": "string"}, "b_name": {"type": "string"},
                "a_side": {"type": "string"}, "b_side": {"type": "string"},
                "hook_topic": {"type": "string"}, "kill_phrase": {"type": "string"},
                "retention": {"type": "string"},
                "lines": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["speaker", "start", "text"],
                    "properties": {"speaker": {"type": "string", "enum": ["A", "B"]}, "start": {"type": "number"},
                                   "text": {"type": "string"}}}},
            }}}},
}

PROMPT = """You pick the moments of a long video that get cut into short vertical clips for DebateTV, an app where an AI
referee scores an argument. Every clip is titled "<A> vs <B> <on what>. Who won?", plays the exchange, then shows the
referee's scorecard. A clip that is not a real two sided argument, or that a stranger scrolls past, is worth nothing,
so pick few and pick well. Zero picks is a correct answer.

The transcript below is the auto-caption transcript of a video titled "{title}" (channel: {channel}).
Each line starts with its time in seconds. Captions carry no speaker labels: work out who is speaking from the words.

STEP 1, rule on the video (the "debate" field). two_sided is true only when two people (or two camps) on camera argue
opposite sides of a question against each other. It is false for a news broadcast, a lecture or sermon, a friendly
interview or podcast where the guests agree, a press conference, a monologue or commentary over clips, a reaction
video, a game or challenge. Say why in one sentence. If it is false, return no exchanges.

STEP 2, find up to {n} exchanges, best first. Each one must pass every test:
1. Two sides. A and B hold opposite positions on ONE clear question and each says at least one full sentence for
   their own side inside the exchange. Not one person talking while the other says "right" or "okay", not a host
   teeing up a guest, not two people agreeing, not a question that gets a speech for an answer.
2. Opens on the hook. The very first words are the question, the claim or the challenge itself, strong enough that
   a stranger with no context wants to hear the answer. No "so", no setup, no leftover half sentence.
3. Stays open. The viewer cannot tell who is winning until the payoff. The turns are short and they escalate:
   pushback inside the first 6 seconds, then a turn about every 5 seconds or faster. No stretch where one person
   talks for more than about 10 seconds.
4. Pays off. It ends on the sharpest line (a comeback, a trap closing, a concession, a number that settles it),
   and that line is the last thing said. The opening question, one reply from each side and the payoff must fit
   inside 19 seconds around the kill phrase, because the clip is trimmed to that.
5. Stands alone. Someone who has never seen the video understands the question and both answers.
6. About the take, never the person. Skip insults with no argument, pile-ons, anyone who looks or sounds like a
   minor, sexually explicit talk, and anything that only works if you know an earlier part of the video.
Aim for 12 to 30 seconds from first word to last; never over 45. No overlapping exchanges. Prefer moments with a
person a 19 year old would recognise, but never invent who is speaking.

For each exchange give:
- start / end in seconds (start at the first word of the hook, end right after the last word of the payoff)
- motion: the question they are arguing, as a short yes/no question
- a_name / b_name: A = the person who speaks first. Use real names only when the title or transcript makes them certain (e.g. the famous host named in the title). Otherwise use a short description like "Harris voter" or "Student".
- a_side / b_side: the position each one argues, in ten words or fewer
- matchup: short, like "Ben Shapiro vs a Harris voter"
- hook_topic: what they clash about as two to five plain words starting with "on", like "on the right to offend". It finishes the title "<matchup> <hook_topic>. Who won?", so it must be literally true of these lines, must not hint who wins, and has no dashes or punctuation.
- lines: every sentence in order, speaker A or B, its start time, and the text copied from the transcript (you may fix obvious caption typos, never add words that were not said)
- kill_phrase: the 2-6 exact words that land the hardest
- retention: why a viewer stays to the end, in one or two plain sentences with no dashes: quote the opening words that stop the scroll, name what is still unsettled in the middle, and say what the last line pays off.

Only return the JSON.

TRANSCRIPT
{transcript}"""

TRIAGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["videos"],
    "properties": {"videos": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "debate", "figure", "why"],
        "properties": {"id": {"type": "string"}, "debate": {"type": "boolean"}, "figure": {"type": "string"},
                       "why": {"type": "string"}},
    }}},
}

TRIAGE = """Each line below is one YouTube video: id | title | channel | minutes. We cut short clips of real debates from
long videos. For every line decide from the title and channel:
- debate: true when the video is most likely two people or two camps arguing opposite sides of a question against
  each other on camera (formal debates, Jubilee Surrounded and Middle Ground, campus "prove me wrong" tables, 1 vs
  20s, a hostile interview where the host argues back, a debate on a podcast or a stream). false for news
  broadcasts, press conferences, lectures, speeches or addresses even with a Q&A, sermons, friendly interviews,
  sports or team talk, commentary and reaction videos, compilations, guessing games and challenges, music, comedy
  sets, and anything not in English.
- figure: the name of a person in it a 19 year old in the US would recognise at once, or an empty string.
- why: five to twelve plain words.
Return every id exactly once. Only return the JSON.

{rows}"""


class PickerDown(RuntimeError):
    """No picker can answer right now (both out of usage, or not logged in): the host's problem, not the video's."""


def codex_out():
    try:
        return json.loads(CODEX_OUT.read_text()).get("until", 0) > time.time()
    except (OSError, ValueError):
        return False


def mark_codex_out(text):
    """Codex says when it is back ("try again at Nov 3rd, 2026 3:54 PM"); hold off until then, else for an hour."""
    until, m = time.time() + 3600, re.search(r"try again at (\w+) (\d+)\w*, (\d{4}) (\d+):(\d+) ([AP]M)", text)
    for fmt in ("%b %d %Y %I %M %p", "%B %d %Y %I %M %p") if m else ():
        try:
            until = datetime.datetime.strptime(" ".join(m.groups()), fmt).timestamp()
        except ValueError:
            pass
    CODEX_OUT.parent.mkdir(parents=True, exist_ok=True)
    CODEX_OUT.write_text(json.dumps({"until": until, "why": text.strip()[-300:], "at": time.strftime("%F %T")}))
    print(f"codex out until {datetime.datetime.fromtimestamp(until):%m/%d %H:%M}", file=sys.stderr)


def ask_codex(prompt, schema, timeout):
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        (work / "schema.json").write_text(json.dumps(schema))
        out = work / "out.json"
        r = subprocess.run(["codex", "exec", "-m", MODEL, "--skip-git-repo-check", "--sandbox", "read-only", "-C", tmp,
                            "--output-schema", str(work / "schema.json"), "-o", str(out), "-"],
                           input=prompt, capture_output=True, text=True, timeout=timeout)
        try:
            return json.loads(out.read_text())
        except (OSError, ValueError):
            # a usage limit exits 0 with nothing written (10/4 to 10/7: 954 sources were marked failed this way)
            raise RuntimeError((r.stderr or r.stdout).strip()[-400:] or f"codex exit {r.returncode}, no answer")


def claude_login():
    """The config dir of a Claude login with room for background work (the Max plan first), by ARENA's own rule."""
    if os.environ.get("BRAIN_CLAUDE_DIR"):
        return os.path.expanduser(os.environ["BRAIN_CLAUDE_DIR"])
    r = subprocess.run([sys.executable, ACCOUNTS, "pick", "--for", "task"], capture_output=True, text=True, timeout=120)
    if r.returncode or not r.stdout.strip():
        raise PickerDown("usage limit: no Claude login has room for the picker right now")
    return r.stdout.split()[0]


def ask_claude(prompt, schema, kind, timeout):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=claude_login())
    r = subprocess.run([CLAUDE, "-p", "--model", CLAUDE_MODELS[kind], "--effort", "medium" if kind == "pick" else "low",
                        "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence",
                        "--output-format", "json", "--json-schema", json.dumps(schema)],
                       input=prompt, capture_output=True, text=True, timeout=timeout, env=env, cwd=tempfile.gettempdir())
    try:
        res = json.loads(r.stdout)
    except ValueError:
        res = {}
    if isinstance(res.get("structured_output"), dict):
        return res["structured_output"]
    msg = f"{res.get('result') or ''} {r.stderr}".strip()[-400:] or f"claude exit {r.returncode}, no answer"
    if re.search(r"usage limit|limit reached|rate limit|Not logged in|/login|authentication|overloaded|\b(401|429|529)\b", msg, re.I):
        raise PickerDown(f"usage limit or login on the Claude picker: {msg}")
    raise RuntimeError(f"claude picker: {msg}")


def ask(prompt, schema, kind="pick", timeout=1800):
    """One structured answer from whichever picker is up -> (answer, "codex" | "claude:<model>")."""
    if PICKER == "codex" or (PICKER == "auto" and not codex_out()):
        try:
            return ask_codex(prompt, schema, timeout), f"codex:{MODEL}"
        except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"codex picker failed: {str(e)[-300:]}", file=sys.stderr)
            if PICKER == "codex":
                raise PickerDown(f"usage limit or login on Codex: {e}")
            mark_codex_out(str(e))
    return ask_claude(prompt, schema, kind, timeout), CLAUDE_MODELS[kind]


def triage(rows):
    """Bulk pass over source titles: [(id, title, channel, seconds)] -> {id: {"debate", "figure", "why"}."""
    text = "\n".join(f"{i} | {(t or '').replace('|', ' ')[:140]} | {(c or '')[:50]} | {round((d or 0) / 60)}" for i, t, c, d in rows)
    got, by = ask(TRIAGE.format(rows=text), TRIAGE_SCHEMA, kind="bulk", timeout=600)
    want = {r[0] for r in rows}
    return {v["id"]: {"debate": v["debate"], "figure": v["figure"].strip(), "why": v["why"].strip(), "by": by}
            for v in got["videos"] if v["id"] in want}


def check(ex, words):
    """What the picker claims, held against the transcript. -> "" when it stands, else why it is thrown out."""
    said = {}
    for l in ex["lines"]:
        said[l["speaker"]] = said.get(l["speaker"], 0) + len([w for w in l["text"].split() if norm(w)])
    if len(said) < 2:
        return "one speaker"
    if min(said.values()) < 6:
        return f"one side says {min(said.values())} words: not two sides"
    turns = sum(a["speaker"] != b["speaker"] for a, b in zip(ex["lines"], ex["lines"][1:]))
    if turns < 2:
        return "no back and forth (the speaker changes once)"
    heard = {norm(w) for t, w in words if ex["start"] - 3 <= t <= ex["end"] + 3}
    mine = [norm(w) for l in ex["lines"] for w in l["text"].split() if norm(w)]
    if not mine or sum(w in heard for w in mine) / len(mine) < 0.7:
        return "lines are not what the transcript says at that time"
    if not ex["retention"].strip():
        return "no reason given"
    return ""


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


def transcript_words(vid):
    """Fallback when YouTube 429s yt-dlp's caption URL (every host here, 9/30): the transcript panel endpoint
    (youtube-transcript-api) still answers. It times phrases, not words, so each word gets an even share of its
    phrase; render.py re-aligns caption words to these times anyway."""
    from youtube_transcript_api import YouTubeTranscriptApi
    words = []
    sns = sorted(YouTubeTranscriptApi().fetch(vid, languages=["en", "en-US", "en-GB"]), key=lambda sn: sn.start)
    for k, sn in enumerate(sns):
        toks = re.sub(r"\[[^\]]*\]", " ", sn.text).split()
        # a phrase stays on screen while the next one is said, so its listed duration runs past the next start.
        # Its words end where the next phrase begins. (Until 10/7 they were spread over 90% of the listed duration:
        # two phrases' words interleaved and the picker read "you think I God was think hyperbolizing scri I is".)
        end = min(sn.start + sn.duration, sns[k + 1].start) if k + 1 < len(sns) else sn.start + sn.duration
        span = max(0.0, end - sn.start)
        for j, w in enumerate(toks):
            words.append((sn.start + span * j / max(1, len(toks)), w))
    return words


def video_info(url):
    """id, title, channel. This Mac first (45 s); when YouTube stalls it, the Air's yt-dlp answers."""
    try:
        return json.loads(run(["yt-dlp", "--no-warnings", "-J", "--skip-download", url], timeout=45).stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        r = run(["ssh", "-o", "ConnectTimeout=15", AIR, "export PYTHONPATH=$HOME/render/tools/ytdlp; perl -e 'alarm 100; exec @ARGV' "
                 "$HOME/render/py/bin/python -m yt_dlp --no-warnings --skip-download --print '%(.{id,title,channel})j' "
                 f"'{url}'"], timeout=150)
        return json.loads(r.stdout.strip().splitlines()[-1])


def fetch(url, work):
    info = video_info(url)
    # one try, 60 s: on 10/7 this call hung for 12 minutes on three videos at once instead of answering 429
    try:
        run(["yt-dlp", "--no-warnings", "-q", "--skip-download", "--write-auto-subs", "--sub-langs", "en",
             "--sub-format", "vtt", "-o", str(work / "subs"), url], timeout=60)
        return info, vtt_words(next(work.glob("subs*.vtt")))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, StopIteration):
        return info, transcript_words(info["id"])


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


def whole(path, want):
    """Sound AND a video stream that runs the whole section: yt-dlp has handed back 15 s of video under 33 s of
    audio (WV29R1M25n8_1328), which later breaks the render."""
    if not has_audio(path):
        return False
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip()) >= want - 1.5
    except ValueError:
        return False


def bounded(cmd, secs):
    """Run and wait at most `secs`; yt-dlp's ffmpeg child is killed with it. -> True when it ran to the end."""
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        p.wait(timeout=secs)
        return True
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, 9)
        p.wait()
        return False


AIR_DL = r"""cd ~/render && mkdir -p tmp/brain && export PYTHONPATH=$HOME/render/tools/ytdlp PATH=$HOME/render/bin:$PATH && \
perl -e 'alarm 240; exec @ARGV' nice -n 19 py/bin/python -m yt_dlp --no-warnings -q -f '{fmt}' \
--download-sections '*{t0:.2f}-{t1:.2f}' --force-keyframes-at-cuts --downloader-args 'ffmpeg_o:-threads 2' \
--merge-output-format mp4 -o tmp/brain/{name}.mp4 '{url}'"""


def air_section(url, t0, t1, dst):
    """The same section fetched by the Air's own yt-dlp (~/render/tools/ytdlp, about 15 s) and copied back. One at
    a time across every brain on this Mac, nice 19, two ffmpeg threads: the Air's cores belong to the fleet."""
    name = f"{dst.parent.name}-{os.getpid()}"
    lock = open(os.path.expanduser("~/.render-farm/air_dl.lock"), "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        for fmt in ("bv*[height<=1080][ext=mp4]+ba[ext=m4a]", "bv*[height<=1080]+ba"):
            dst.unlink(missing_ok=True)
            subprocess.run(["ssh", "-o", "ConnectTimeout=15", AIR, AIR_DL.format(fmt=fmt, t0=t0, t1=t1, name=name, url=url)],
                           capture_output=True, text=True, timeout=300)
            subprocess.run(["scp", "-q", "-o", "ConnectTimeout=15", f"{AIR}:render/tmp/brain/{name}.mp4", str(dst)],
                           capture_output=True, text=True, timeout=300)
            subprocess.run(["ssh", "-o", "ConnectTimeout=15", AIR, f"rm -f ~/render/tmp/brain/{name}.mp4*"],
                           capture_output=True, text=True, timeout=60)
            if dst.exists() and whole(dst, t1 - t0):
                return True
    except (subprocess.TimeoutExpired, OSError):
        pass
    finally:
        lock.close()
    return False


STALLED = pathlib.Path(os.path.expanduser("~/.render-farm/yt_stalled"))  # this Mac's downloads stall: go to the Air first


def download_section(url, t0, t1, dst):
    """yt-dlp sometimes returns a section with the audio missing; try formats until it has sound. YouTube also
    stalls this Mac's downloads for hours at a time (10/7: 2 MB, then nothing for 15 minutes, while the Air took
    13 s for the same section), so a local try gets 150 s and the Air is the other route. Whichever route worked
    last goes first for the next 2 hours."""
    air_first = STALLED.exists() and time.time() - STALLED.stat().st_mtime < 2 * 3600
    if air_first and air_section(url, t0, t1, dst):
        return
    for fmt in ("bv*[height<=1080][ext=mp4]+ba[ext=m4a]", "bv*[height<=1080]+ba", "b"):
        dst.unlink(missing_ok=True)
        ended = bounded(["yt-dlp", "--no-warnings", "-q", "-f", fmt, "--download-sections", f"*{t0:.2f}-{t1:.2f}",
                         "--force-keyframes-at-cuts", "--merge-output-format", "mp4", "-o", str(dst), url], 150)
        if dst.exists() and whole(dst, t1 - t0):
            STALLED.unlink(missing_ok=True)
            return
        if not ended:
            break  # stalled, not a bad format: the other formats would stall the same way
    for part in dst.parent.glob(dst.name + ".part*"):
        part.unlink(missing_ok=True)
    if not air_first and air_section(url, t0, t1, dst):
        STALLED.touch()
        return
    raise RuntimeError(f"no whole section with audio for {url} {t0}-{t1}")


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
    ap.add_argument("--dry", action="store_true", help="print the picks and their reasons; judge, download and file nothing")
    a = ap.parse_args()
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}

    with tempfile.TemporaryDirectory() as tmp:
        info, words = fetch(a.url, pathlib.Path(tmp))
    vid, title, channel = info["id"], info.get("title", ""), info.get("channel", "")
    print(f"{vid}: {title} — {len(words)} caption words", file=sys.stderr)
    try:
        got, by = ask(PROMPT.format(title=title, channel=channel, n=a.max, transcript=transcript_text(words)), SCHEMA)
    except PickerDown as e:
        sys.exit(f"picker down, {e}")  # the feeder reads "usage limit" here and backs off instead of failing the source
    verdict_on_video, exchanges = got["debate"], got["exchanges"]
    print(f"picker {by}: {'two sided' if verdict_on_video['two_sided'] else 'not a debate'}: {verdict_on_video['why']}", file=sys.stderr)
    if not verdict_on_video["two_sided"]:
        exchanges = []
    if a.dry:
        for ex in exchanges:
            ex["thrown_out"] = check(ex, words)
        print(json.dumps({"video": {"id": vid, "title": title, "channel": channel}, "picker": by, "debate": verdict_on_video,
                          "exchanges": exchanges}, indent=1))
        return

    made = 0
    for rank, ex in enumerate(exchanges, 1):  # the picker returns its best first
        key = f"{vid}_{int(ex['start'])}"
        why_not = "" if key not in ledger and 12 <= ex["end"] - ex["start"] <= 60 else "in the ledger or the wrong length"
        why_not = why_not or check(ex, words)
        if why_not:
            print(f"skip {key}: {why_not}", file=sys.stderr); continue
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
        try:
            download_section(a.url, t0, ex["end"] + PAD, d / "src.mp4")
        except RuntimeError as e:
            print(f"skip {key}: {e}", file=sys.stderr)
            shutil.rmtree(d, ignore_errors=True)
            continue
        ex["hook_topic"] = re.sub(r"[^\w' ]+", " ", ex["hook_topic"]).strip()  # on screen: no dashes, no punctuation
        job = {"key": key, "source": {"url": a.url, "id": vid, "title": title, "channel": channel, "t0": round(t0, 2)},
               **ex, "picker": {"by": by, "at": time.strftime("%F %T"), "rank": rank, "video": verdict_on_video["why"]},
               "words": cap, "judge_request": req, "judge_response": verdict}
        (d / "job.json").write_text(json.dumps(job, indent=1))
        # several brains run at once (render-farm feeder): merge with what the others wrote since we started
        ledger = {**(json.loads(LEDGER.read_text()) if LEDGER.exists() else {}), key: {"title": title, "motion": ex["motion"]}}
        tmp = LEDGER.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(ledger, indent=1))
        tmp.replace(LEDGER)
        made += 1
        print(f"job {key}: {ex['matchup']} — {ex['motion']}", file=sys.stderr)
        print(f"  holds because: {ex['retention']}", file=sys.stderr)
    print(f"{made} jobs from {len(exchanges)} exchanges", file=sys.stderr)


if __name__ == "__main__":
    main()
