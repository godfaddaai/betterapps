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
import diarize
import argparse, datetime, fcntl, html, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, urllib.request

HERE = pathlib.Path(__file__).parent
JOBS = HERE / "jobs"
LEDGER = HERE / "ledger.json"
JUDGE = "https://debatetvbackend-production.up.railway.app/judge"
PAD = 0.6  # seconds of source kept either side of the exchange
# the Codex config default can be a model a ChatGPT login cannot use ("gpt-6.1-sol", 9/30): name it explicitly
MODEL = os.environ.get("BRAIN_MODEL", "gpt-5.6-sol")  # 11/5: gpt-5.5 and gpt-6-sol are refused on his ChatGPT login
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
                         "take_hook", "kill_phrase", "retention", "lines"],
            "properties": {
                "start": {"type": "number"}, "end": {"type": "number"},
                "motion": {"type": "string"}, "matchup": {"type": "string"},
                "a_name": {"type": "string"}, "b_name": {"type": "string"},
                "a_side": {"type": "string"}, "b_side": {"type": "string"},
                "hook_topic": {"type": "string"}, "take_hook": {"type": "string"},
                "kill_phrase": {"type": "string"},
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
Each line starts with its time in seconds.{voices}

STEP 1, rule on the video (the "debate" field). two_sided is true only when two people (or two camps) on camera argue
opposite sides of a question against each other. It is false for a news broadcast, a lecture or sermon, a friendly
interview or podcast where the guests agree, a press conference, a monologue or commentary over clips, a reaction
video, a game or challenge. Say why in one sentence. If it is false, return no exchanges.

STEP 2, find up to {n} exchanges, best first. Each one must pass every test:
1. Two sides. A and B hold opposite positions on ONE clear question and each says at least one full sentence for
   their own side inside the exchange. Not one person talking while the other says "right" or "okay", not a host
   teeing up a guest, not two people agreeing, not a question that gets a speech for an answer. Each side must
   say at least one full sentence that is a STATEMENT for their own side (not a question, and not "yes", "no",
   "absolutely", "certainly", "okay"), and the two statements must contradict each other. If one side only asks
   questions, skip it, however good the trap.
2. Opens on the hook. The very first words are the question, the claim or the challenge itself, strong enough that
   a stranger with no context wants to hear the answer. No "so", no setup, no leftover half sentence. The first
   sentence names its own subject: no "it", "that", "there", "the key difference" or "to be clear" pointing at
   something said earlier, and not an open invitation like "talk to me about". Every "it", "that", "this",
   "he" or "she" in the first and the last sentence has its noun said inside the pick.
3. Stays open. The viewer cannot tell who is winning until the payoff. The turns are short and they escalate:
   pushback inside the first 6 seconds, then a turn about every 5 seconds or faster. No stretch where one person
   talks for more than 8 seconds. If the question alone takes more than 6 seconds to ask, skip the moment.
4. Pays off. It ends on the sharpest line (a comeback, a trap closing, a concession, a number that settles it),
   and that line is the last thing said. The payoff is a point about the question. Skip the moment when its
   hardest line is about the other person or a group ("you have no idea"), settles nothing ("that's not the
   claim"), or when the question is whether a named person is lying. Read the two sentences after your
   payoff: skip when the payoff is only the start of a reply ("well, first of all"), could be the start of the
   other speaker's next sentence, or argues about what was said earlier ("we just agreed").
5. Stands alone. Someone who has never seen the video understands the question and both answers.
6. About the take, never the person. Skip insults with no argument, pile-ons, anyone who looks or sounds like a
   minor, sexually explicit talk or talk about anyone's sexual past, swearing (the captions print every word),
   and anything that only works if you know an earlier part of the video.
Length, first word to last word: 10 to 18 seconds, never more than 19. Only the last 19 seconds ending on the
payoff are played, so anything earlier is cut and your hook goes with it. A moment that needs more than 19 seconds
is not a pick. No overlapping exchanges. Prefer moments with a person a 19 year old would recognise, but never
invent who is speaking: if the hook or the payoff could be either speaker, skip the exchange.

For each exchange give:
- start / end in seconds. start is the first word of the hook. end is the moment the last word of the payoff finishes, and nothing after it: no "okay", no first words of the reply.
- motion: the question they are arguing, as a short yes/no question, using only nouns said inside the pick
- a_name / b_name: A = the person who speaks first. Use real names only when the title or transcript makes them certain (e.g. the famous host named in the title). Otherwise use a short description like "Harris voter" or "Student": what they say they are, or the side they argue ("a panelist" when unsure). Never a political label they did not use themselves, never their race, never a first name that is not spoken in the pick, never a word about their body or health.
- a_side / b_side: the position each one argues, in ten words or fewer
- matchup: short, like "Ben Shapiro vs a Harris voter"
- hook_topic: what they clash about as two to five plain words starting with "on", like "on the right to offend". It finishes the title "<matchup> <hook_topic>. Who won?", so it must be literally true of these lines, use words said in them, name the thing argued (never one side's claim stated as fact), mean something to a stranger, not hint who wins, and have no dashes or punctuation.
- take_hook: the on-screen hook a stranger reads first (copy rule, 10/14): three to seven words, in plain spoken words a 19 year old would text, that state the take or the stakes of the fight, like "Should women skip *college*?" or "Bill Nye calls Ken Ham *100% wrong*". A yes/no question about the thing argued, or what one person dares say to the other. Mark the one or two words that sting with *stars*. Never the words "AI", "ref", "scored", "vs" or "debate", never a name the stranger would not know (use the role instead), never hint who wins, no dashes.
- lines: every sentence in order, speaker A or B, its start time, and the text copied from the transcript (you may fix obvious caption typos; never add words that were not said, never join two half lines into one, copy crosstalk as it is). Line start times strictly increase.
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


REVIEW_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["picks"],
    "properties": {"picks": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["key", "verdict", "fails", "why"],
        "properties": {"key": {"type": "string"}, "verdict": {"type": "string", "enum": ["KEEP", "WEAK", "PULL"]},
                       "fails": {"type": "array", "items": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6]}},
                       "why": {"type": "string"}},
    }}},
}

REVIEW = """You are the second reader. Be skeptical: your job is to find what is wrong with each pick, not to confirm it.

DebateTV cuts short vertical clips out of long debates. A clip opens with the title "<A> vs <B> <on what>. Who won?",
plays the whole pick (8 to 19 seconds), then shows an AI referee's scorecard. The owner's rule: "Clips are picked as
real debates for retention, not scraped at random for volume." A first reader picked the moments below from the video
"{title}" ({channel}). For each pick you get its title, each side's position, its lines with the speaker the first
reader assigned, the reason it gave, and the RAW captions (word times good to half a second; [S1], [S2] tags, when
there, are a speaker diarizer's voices from the audio, a new tag at each change of voice) for
25 seconds before, during, and 12 seconds after. Judge from the raw captions, never from the first reader's claims.

KEEP only when all of this is true:
1. Two people argue opposite sides of one question and EACH makes a statement for their own side. A chain of
   questions against yes and no answers is a cross examination, not a debate.
2. The lines are what the captions say, and the speaker of the hook and of the payoff is clear from the words.
3. The first sentence stops a stranger with no context and names its own subject (no "it", "that", "he" whose noun
   is only said earlier).
4. The last line is the hardest line, is a whole sentence, is a point about the question (not about the other
   person or a group), and the captions after it do not show it was only the start of a longer reply.
5. It stands alone, and the title is literally true of the lines, in words said in them, with no hint of who wins,
   no name the captions do not support, no label on a private person (race, politics, body).
6. Nothing about a person rather than a take, no pile-on, no one who sounds like a minor, no explicit talk or talk
   about anyone's sexual past, no swearing.
WEAK = a real debate that fails 3, 4 or 5. PULL = fails 1, 2 or 6. Give every pick one verdict, in fails the number
of every rule above it fails (empty for KEEP; list them all, not only the first), and one or two plain sentences with no dashes that quote the caption words deciding it. Most picks should not survive you; KEEP is earned.
Only return the JSON.

{picks}"""


def second_read(vid_title, channel, exchanges, words, edit=None):
    """An independent second pass over the picks that passed check(): {key: (verdict, why, fails)}. The first two human
    ordered reviews (10/7) kept 6 of 21 and 3 of 10 of what one reader picked, so nothing is filed on one reading."""
    g = lambda a, b: tagged(words, a, b)
    blocks = []
    for key, ex in exchanges:
        blocks.append(f"""## PICK {key} ({ex['end'] - ex['start']:.1f} s)
Title: "{ex['matchup']} {ex['hook_topic']}. Who won?"
Motion: {ex['motion']}
A = {ex['a_name']}: {ex['a_side']}
B = {ex['b_name']}: {ex['b_side']}
Kill phrase: {ex['kill_phrase']}
First reader's reason: {ex['retention']}
Lines:
""" + "\n".join(f"  {l['speaker']} [{l['start']:.1f}] {l['text']}" for l in ex["lines"]) + f"""
Raw captions, 25 s BEFORE: {g(ex['start'] - 25, ex['start'])}
Raw captions, THE PICK: {g(ex['start'], ex['end'] + 0.3)}
Raw captions, 12 s AFTER: {g(ex['end'] + 0.3, ex['end'] + 12)}
""")
    got, by = ask(REVIEW.format(title=vid_title, channel=channel, picks="\n".join(blocks)) + (WIRE_REVIEW if WIRE else "")
                  + (EDIT_REVIEW if (EDIT if edit is None else edit) else ""),
                  REVIEW_SCHEMA)
    return {p["key"]: (p["verdict"], p["why"].strip(), sorted(set(p.get("fails") or []))) for p in got["picks"]}, by


# The end recut (11/6, asks a201 and a346 "content 24/7 ... 30 kept clips a day, keep the picker's bar"): in 146 brain
# runs the picker offered 149 exchanges and 3 were kept; 91 of the kills are the second reader saying WEAK, mostly
# because the payoff runs straight on into more of the same reply. When the reader faults the end (WEAK, rule 4 among
# its fails, and its words say the reply runs on), caption_recut() moves the end to where that sentence finishes in
# the caption words and drops opening lines to stay under MAX_PICK. The recut then faces check() and the second
# reader again, once, from scratch: it is filed only on a fresh KEEP. No rule and no prompt is loosened.
RUNS_ON = re.compile(r"runs? (straight |right )?(on )?into|keeps? going|kept going|still going|carries on|carried on|"
                     r"goes on|went on|continues|continued|cut off|cuts off|only the start|mid ?(sentence|thought|reply)|"
                     r"unfinished|not finished|isn.t finished|before .{0,20}finish", re.I)


def end_only(verdict, why, fails):
    """The second reader faults the pick (rule 4 among its fails) for ending while the reply is still going."""
    return verdict == "WEAK" and 4 in fails and bool(RUNS_ON.search(why))


RECUT_LOG = pathlib.Path(os.path.expanduser("~/.render-farm/recut_ledger.jsonl"))


def note_recut(key, outcome, dry, why="", src=None):
    """One line per end recut step (11/6, j704): the gate's real yield per day, read by `brain.py --recut-stats`.
    key is the recut's own key once it has one; src is always the pick it was cut from. Outcomes: failed, no_cut,
    check, weak, pull, read_keep (the second reader kept it) and filed (its job.json is written)."""
    try:
        RECUT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with RECUT_LOG.open("a") as f:
            f.write(json.dumps({"at": time.strftime("%F %T"), "key": key, "src": src or key, "outcome": outcome, "dry": dry,
                                "why": why[:300]}) + "\n")
    except OSError:
        pass   # the ledger is a count, never a reason to drop a pick


def recut_stats():
    """Recuts tried and kept per day from the ledger (live runs; dry reads counted apart)."""
    days = {}
    for line in RECUT_LOG.read_text().splitlines() if RECUT_LOG.exists() else ():
        try:
            r = json.loads(line)
            day, outcome = str(r["at"])[:10], str(r["outcome"])
        except (ValueError, KeyError, TypeError):
            continue   # a bad line never stops the count
        d = days.setdefault((day, "dry" if r.get("dry") else "live"), {})
        d[outcome] = d.get(outcome, 0) + 1
    for (day, kind), c in sorted(days.items()):
        tried = sum(v for k, v in c.items() if k != "filed")
        print(f"{day} {kind}: {tried} tried, {c.get('read_keep', 0)} kept by the second reader, {c.get('filed', 0)} filed  " +
              ", ".join(f"{k} {v}" for k, v in sorted(c.items())))


def caption_recut(ex, words):
    """The end recut from the captions alone (11/6, ask a346): the second reader said the payoff runs straight on into
    more of the same reply, so the end moves to where that speaker's sentence finishes in the caption words (a . ? !
    when the captions are punctuated, else a pause of a second or more), at most 9 s on and never past a ">>" turn
    mark. Two ends are offered when they differ: the first sentence end, and the last one before the turn mark or the
    9 s (the reply's finish). The words heard up to the end join the last line, so the kill phrase stays in it. If a
    cut then runs past MAX_PICK, opening lines drop until it fits (never below two lines). -> ([cuts], why none).
    check() and the second reader rule on each from scratch, unchanged; at most one is filed."""
    tail = [norm(w) for w in ex["lines"][-1]["text"].split() if norm(w)]
    if not tail:
        return [], "empty last line"
    near = [t for t, w in words if norm(w) == tail[-1] and t > ex["lines"][-1]["start"] and abs(t - ex["end"]) <= 4]
    t_last = min(near, key=lambda t: abs(t + 0.5 - ex["end"])) if near else ex["end"] - 0.5
    after = [(t, w) for t, w in words if t > t_last + 0.05]
    punct = any(w[-1:] in ".?!" for t, w in words if t_last - 30 <= t <= t_last + 30)
    ends = []   # (index of the sentence's last word in after, end time)
    # with the diarizer (11/6, j812), the payoff speaker's voice ending is a turn mark too: the last word before
    # another voice takes over is an end, and the cut never runs into the other voice
    # the payoff's own caption word (the voice cache is keyed by (time, word)), else the last word heard by t_last
    said = [(t, w) for t, w in words if t <= t_last + 0.05]
    av = voice_of(said[-1:] + after) if SEGS and said else []
    for k, (t, w) in enumerate(after):
        if t > t_last + 9 or w.startswith(">>") or (av and av[k + 1] and av[0] and av[k + 1] != av[0]):
            break
        nxt = after[k + 1][0] if k + 1 < len(after) else None   # None: the video's last word
        turn = bool(av) and k + 2 < len(av) and av[k + 2] and av[0] and av[k + 2] != av[0]
        if (punct and w[-1:] in ".?!") or (not punct and (nxt is None or nxt - t >= 1.0)) or turn:
            # the reader sees the captions to end + 0.3 and the clip plays to the end: the next word stays out of both
            ends.append((k, t + 0.5 if nxt is None else max(t + 0.3, min(t + 0.5, nxt - 0.35))))   # never before the word ends
    if not ends:
        return [], "the sentence does not finish within 9 s"
    cuts, why = [], ""
    for k, end in dict.fromkeys([ends[0], ends[-1]]):
        lines = [dict(l) for l in ex["lines"]]
        lines[-1]["text"] = lines[-1]["text"].rstrip() + " " + " ".join(w for _, w in after[:k + 1])
        while end - lines[0]["start"] > MAX_PICK and len(lines) > 2:
            lines.pop(0)
            lines[0]["start"] = snap(words, lines[0]["start"], lines[0]["text"])
        if end - lines[0]["start"] > MAX_PICK:
            why = f"{end - lines[0]['start']:.1f} s even without the opening line"; continue
        cuts.append(dict(ex, lines=lines, start=lines[0]["start"], end=round(end, 2)))
    return cuts, why


# The title name fix (11/6, ask a367): 15 of 148 second reader skips 11/5-11/6 were rule 5 because OUR title names a
# person the captions never say ("the name Jay Dyer is never said in the captions", hev8PIXkwRg). That is our label,
# not the clip. Mirroring the end recut: the unsaid name is replaced by the side that person argues ("a Protestant"),
# and the pick goes to the second reader once more, from scratch; it is filed only on a fresh KEEP.
NAME_GONE = re.compile(r"\bnames?\b|\bnamed\b|\bnaming\b", re.I)


def absent_names(ex, words):
    """The names in a_name / b_name the captions never say (25 s before the pick to 12 s after): {"a": .., "b": ..}.
    Only a full name of two or more capitalised words ("Jay Dyer", "Earthling Ed") is checked: a description ("a
    Protestant", "Student", "Protestant") is never a name, so it is never absent."""
    heard = {norm(w) for t, w in words if ex["start"] - 25 <= t <= ex["end"] + 12}
    gone = {}
    for side in ("a", "b"):
        name = ex.get(f"{side}_name") or ""
        if not name[:1].isupper():
            continue   # "a Protestant", "an atheist": a description, not a name
        caps = [norm(w) for w in name.split() if w[:1].isupper() and len(norm(w)) > 2]
        if len(caps) >= 2 and len(caps) == len([w for w in name.split() if norm(w)]) and not any(c in heard for c in caps):
            gone[side] = name
    return gone


def name_fault(verdict, why, fails, ex, words):
    """The second reader faults rule 5 for a name, and a name in our title is in fact not in the captions."""
    return verdict == "WEAK" and 5 in fails and bool(NAME_GONE.search(why)) and bool(absent_names(ex, words))


LABEL_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["picks"],
    "properties": {"picks": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["key", "a_label", "b_label"],
        "properties": {"key": {"type": "string"}, "a_label": {"type": "string"}, "b_label": {"type": "string"}}}}},
}

LABEL = """Each pick below is a clip from a debate. Its title names a person the captions never say, so the title must call
them by the side they argue instead. For each pick give a_label and b_label: two to four plain words for what A and B
argue or say they are, like "a Protestant", "an Orthodox Christian", "a pro lifer", "a Harris voter", "a student".
Keep a name only when it is listed as said. Never a political label they did not use themselves, never their race,
never a word about their body or health, never a hint of who wins. Return every key once. Only return the JSON.

{picks}"""


def relabel(picks, words):
    """One call for every pick whose title names someone the captions never say -> {key: ex with the new names}."""
    blocks = []
    for key, ex in picks:
        gone = absent_names(ex, words)
        blocks.append(f"## {key}\nMotion: {ex['motion']}\nA ({'never said' if 'a' in gone else 'said'}: "
                      f"{ex['a_name']}) argues: {ex['a_side']}\nB ({'never said' if 'b' in gone else 'said'}: "
                      f"{ex['b_name']}) argues: {ex['b_side']}\n")
    got, _ = ask(LABEL.format(picks="\n".join(blocks)), LABEL_SCHEMA, "bulk", 600)
    src, out = dict(picks), {}
    for r in got["picks"]:
        ex = src.get(r["key"])
        if not ex:
            continue
        gone, new = absent_names(ex, words), dict(ex)
        for side, name in gone.items():
            label = re.sub(r"[^\w' ]+", " ", r.get(f"{side}_label") or "").strip()
            if not re.match(r"(a|an|the) \w", label, re.I) or any(norm(w) in {norm(x) for x in label.split()} for w in name.split() if w[:1].isupper()):
                break   # no "a ..." label for a person, or it keeps the unsaid name: no rename
            new[f"{side}_name"] = label
            for w in [name] + [x for x in name.split() if x[:1].isupper() and len(x) > 2]:
                for f in ("hook_topic", "take_hook", "motion", "a_side", "b_side", "retention"):
                    if new.get(f):   # every field that reaches the screen, the judge or job.json
                        new[f] = re.sub(rf"(^|[.?!]\s+)?\b{re.escape(w)}\b",
                                        lambda m: (m.group(1) or "") + (label[:1].upper() + label[1:] if m.group(1) is not None
                                                                        else label), new[f])
        else:
            new["matchup"] = f"{new['a_name']} vs {new['b_name']}"   # the title's names are the two sides now
            new["renamed_from"] = dict(gone)
            out[r["key"]] = new
    return out


# WEAK to the beat edit (11/6, ask a366): a clip-route pick the second reader calls WEAK (a real debate, failing only
# the clip's hook and window rules 3 to 5, never PULL) and that no recut or rename saved is not dropped: the edit
# picker reads the captions around it (WIDEN s either side) and returns a 20 to 60 s exchange for 64_beatedit, which
# faces check() and the second reader in edit mode, unchanged (KEEP or WEAK files, PULL never), with "mode": "edit".
WIDEN = 40


def edit_repick(title, channel, words, weak, avoid, n):
    """[(ex, from_key)]: 20 to 60 s edit picks, each widened around ONE weak pick (it must contain or overlap the
    moment the second reader called WEAK, inside WIDEN s either side of it); none overlap avoid. weak: [(key, ex)]."""
    wins = [(k, max(0.0, ex["start"] - WIDEN), ex["end"] + WIDEN, ex) for k, ex in weak]
    text = "\n...\n".join(transcript_text([(t, w) for t, w in words if a <= t <= b]) for _, a, b, _ in wins)
    got, by = ask(PROMPT.format(title=title, channel=channel, n=n, transcript=text, voices=voices_note()) + EDIT_NOTE, SCHEMA)
    if not got["debate"]["two_sided"]:
        return [], by
    picks = []
    for ex in got["exchanges"]:
        src = next((k for k, a, b, w in wins if a - 1 <= ex["start"] and ex["end"] <= b + 1
                    and ex["start"] < w["end"] and w["start"] < ex["end"]), None)   # widened around this weak pick
        if src and not any(ex["start"] < o["end"] and o["start"] < ex["end"] for o in avoid) \
                and not any(f == src for _, f in picks):   # one edit job per weak pick
            picks.append((ex, src))
    return picks, by


# The open is a line of the side REF scores higher (11/6, j1217): beatedit edits that side (focus_side) and its open is
# one whole 3 to 6.3 s sentence they say alone. The edit picker aims its 3 to 6 s sentence at "the better known person"
# before REF has scored, so on 0e2wThS_5oU_3558 and Z8nSnsmidQU_7684/_6848 the kill phrase sat on the side REF scored
# lower, and on b75GNVh4ABo_865 Andrew Wilson (REF's side) spoke only in bursts of 3.1 s and less: "no line of the
# edited debater fits the open", 10 of 24 gate refusals on 11/6. So when beatedit spec refuses an edit pick's open
# (open_run, OPEN_RUN: tests only; no pre-check refuses a pick before beatedit has read it), the picker is asked
# once more with that side named, for the same clash widened or shifted (WIDEN s either side, 20 to 60 s) to hold one
# sentence of theirs of 3 to 6 s alone. The new pick faces check(), the second reader, REF (still that side) and
# beatedit spec again, all unchanged. Off with BRAIN_OPEN_REPICK=0.
OPEN_REPICK = os.environ.get("BRAIN_OPEN_REPICK", "1") != "0"
OPEN_RUN = 2.6   # caption starts run short of beatedit's aligned words + 0.12 s lead in: a margin, never a new bar
NO_OPEN = "no line of the edited debater fits the open"
OPEN_NOTE = """

OPEN REPICK. One exchange was picked from {s0:.1f} to {s1:.1f} s, matchup "{matchup}". The edit is of {name} (side
{letter}, the side the judge scored higher), and its 6 second open is one whole sentence {name} says alone, 3 to 6
seconds from first word to last, no one else talking inside it. That pick has none ({why}). Return at most ONE exchange
from this transcript: the same clash (it overlaps {s0:.1f} to {s1:.1f} s), widened or shifted, 20 to 60 seconds, in
which {name} says such a sentence, a claim, a comeback or a number that lands on its own for a stranger. Keep {name}
as side {letter} and put that sentence's hardest 2 to 6 words in kill_phrase: this sentence is {name}'s, whoever is
better known (it replaces that rule above). Every other test holds as written. When
{name} never talks 3 seconds alone anywhere near this clash, return no exchanges."""


def focus_of(verdict, cap):
    """The side beatedit edits (beatedit.focus_side): REF's higher average, a tie to the side that talks more."""
    v = verdict["averageScores"]
    if v["participantA"] != v["participantB"]:
        return "A" if v["participantA"] > v["participantB"] else "B"
    return max(("A", "B"), key=lambda s: sum(1 for c in cap if c["s"] == s))


def open_run(cap, side):
    """The longest stretch the side talks with no word of the other side inside, in seconds (caption word starts, the
    last word given 0.6 s). Under OPEN_RUN no 3 s sentence of theirs alone can exist, so beatedit cannot find an open."""
    best, k = 0.0, 0
    while k < len(cap):
        if cap[k]["s"] != side:
            k += 1; continue
        j = k
        while j + 1 < len(cap) and cap[j + 1]["s"] == side:
            j += 1
        end = min(cap[j + 1]["t"], cap[j]["t"] + 0.6) if j + 1 < len(cap) else cap[j]["t"] + 0.6
        best, k = max(best, end - cap[k]["t"]), j + 1
    return round(best, 2)


GENERIC = {"man", "woman", "guy", "girl", "speaker", "person", "panelist", "caller", "guest", "host", "student", "the"}


def same_person(a, b):
    """Two labels name one person: a shared name word ("Andrew Wilson", "Wilson"), never only "man" or "speaker"."""
    tok = lambda x: {norm(w) for w in (x or "").split() if len(norm(w)) > 2 and norm(w) not in GENERIC}
    if tok(a) or tok(b):
        return bool(tok(a) & tok(b))
    return bool(norm(a or "")) and norm(a or "") == norm(b or "")


def open_repick(title, channel, words, ex, side, why, avoid):
    """-> (ex, by) or (None, why): the same clash again, widened or shifted so REF's side says a 3 to 6 s line alone."""
    s0, s1 = ex["picked_at"]
    name = ex["a_name"] if side == "A" else ex["b_name"]
    a, b = max(0.0, s0 - WIDEN), s1 + WIDEN
    text = transcript_text([(t, w) for t, w in words if a <= t <= b])
    note = OPEN_NOTE.format(s0=s0, s1=s1, matchup=ex.get("matchup", ""), name=name, letter=side, why=why)
    got, by = ask(PROMPT.format(title=title, channel=channel, n=1, transcript=text, voices=voices_note()) + EDIT_NOTE + note,
                  SCHEMA)
    if not got["debate"]["two_sided"]:
        return None, "the picker says no debate here"
    for e in got["exchanges"]:
        if not (a - 1 <= e["start"] and e["end"] <= b + 1 and e["start"] < s1 and s0 < e["end"]):
            continue   # outside the widened window, or no longer the same clash
        if any(e["start"] < o["end"] and o["start"] < e["end"] for o in avoid):
            continue
        if abs(e["start"] - s0) < 1 and abs(e["end"] - s1) < 1:
            continue   # the same window again: beatedit would refuse it again (Z8nSnsmidQU_6848)
        if not same_person(e["a_name"] if side == "A" else e["b_name"], name):
            continue   # the sides came back swapped: REF's side is not the one asked for
        bad = check(e, words, edit=True)
        if bad:
            return None, f"the repick fails check: {bad}"
        return e, by
    return None, f"no repick holds {name} 3 s alone"


# Footage beatedit can cut (11/6, ask a391): beatedit.py render refused all 4 edit jobs filed after a366 on the
# picture, never on the words: DhpfsOSNakY_723 and u14d6ajzHZw_10938 "no line of the edited debater fits the open"
# (the side REF favours is a crowd member, never on camera for a whole 3 to 6.3 s line), koC8A86BS2k_3087 a blank
# split screen panel, t_JmqOFTLjI_1162 edited-in text. So an edit job is filed only when beatedit itself has cut the
# window and found its open: two cheap skips first (a 1 vs N show where the crowd side wins, a split screen call),
# then `beatedit.py spec` (prep, the face track, pick_open, the beats and the text read; no build) on the job staged
# where only beatedit looks. Off with BRAIN_BEATEDIT_GATE=0.
BEATEDIT = pathlib.Path(os.path.expanduser(os.environ.get(
    "BRAIN_BEATEDIT", "~/Documents/ARENA/render-farm/formats/beatedit.py")))
BEATEDIT_GATE = os.environ.get("BRAIN_BEATEDIT_GATE", "1") != "0"
GATE_SECS = int(os.environ.get("BRAIN_BEATEDIT_SECS", 25 * 60))
GATE_LOG = pathlib.Path(os.path.expanduser("~/.render-farm/beatedit_gate.jsonl"))
ONE_VS_N = re.compile(r"\b1\s+((?:[A-Za-z][\w']*\s+){0,2}?)(?:vs\.?|v|versus|confronts?|against|faces?|takes on|debates?)\s+"
                      r"(?:\d+|a crowd|the crowd)\b|\b\d+\s+(?:[A-Za-z][\w']*\s+){0,2}?(?:vs\.?|v|versus)\s+1\s+"
                      r"((?:[A-Za-z][\w']*\s*){1,2})|surrounded", re.I)
SPLIT = re.compile(r"\blive on \w|\bon (?:his |her |the )?stream\b|\bstream(?:er|ed|ing)?\b|\btwitch\b|\bkick\b|"
                   r"\bzoom\b|\bfacetime\b|\bvideo call\b|\bcalls? (?:in|out)\b|\bphone call\b|\bspaces\b|\bremote\b|"
                   r"\beye to eye\b", re.I)


def one_side(title, channel):
    """In a 1 vs N show ("1 Atheist vs 10 Christians", "Surrounded"), the words naming the one: the noun after
    the "1" and every capitalised name in the title and channel. None when the title is not a 1 vs N show."""
    m = ONE_VS_N.search(title or "")
    if not m:
        return None
    one = {norm(w) for g in m.groups() if g for w in g.split() if len(norm(w)) > 2}
    caps = re.findall(r"\b[A-Z][\w']+(?:\s+[A-Z][\w']+)+", f"{title} {channel or ''}")   # "Adam Green", "King Kenny"
    return one | {norm(w) for c in caps for w in c.split() if len(norm(w)) > 2}


def crowd_wins(ex, verdict, title, channel):
    """The side REF favours (beatedit edits that side) is the crowd of a 1 vs N show: its label is not the one's and
    the other side's is. The crowd member is on camera for seconds at a time, so beatedit finds no open (u14d6ajzHZw)."""
    one = one_side(title, channel)
    try:
        v = verdict["averageScores"]
        win = "a" if v["participantA"] > v["participantB"] else "b" if v["participantB"] > v["participantA"] else None
    except (KeyError, TypeError):
        return False
    if one is None or win is None:
        return False
    hit = lambda side: bool({norm(w) for w in (ex.get(f"{side}_name") or "").split()} & one)
    lose = "b" if win == "a" else "a"
    return not hit(win) and hit(lose)


def split_screen(title, channel):
    """A call or a stream (a split screen, a guest in a box): beatedit refuses the blank panel (koC8A86BS2k)."""
    return bool(SPLIT.search(f"{title or ''} {channel or ''}"))


def beatedit_dirs():
    """Where beatedit (chain_formats) reads a job before the engine's jobs dir: data/chain_jobs/<key>/job.json and
    $TMPDIR/beatedit/chain/src/<key>/src.mp4. Neither farm.py nor beatedit_feed.py looks there."""
    work = os.path.join(os.environ.get("TMPDIR") or os.path.expanduser("~/Library/Caches"), "beatedit")
    return BEATEDIT.parent / "data" / "chain_jobs", pathlib.Path(work, "chain", "src"), pathlib.Path(work, "clips")


def note_gate(key, outcome, why=""):
    try:
        GATE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with GATE_LOG.open("a") as f:
            f.write(json.dumps({"at": time.strftime("%F %T"), "key": key, "outcome": outcome, "why": why[:300]}) + "\n")
    except OSError:
        pass


def gated():
    """{key: outcome} of every edit job beatedit already refused, so a rerun never judges or downloads it again."""
    out = {}
    for line in GATE_LOG.read_text().splitlines() if GATE_LOG.exists() else ():
        try:
            r = json.loads(line)
            out[r["key"]] = r["outcome"]
        except (ValueError, KeyError, TypeError):
            continue
    return out


def beatedit_spec(key, job, src):
    """Stage the job where only beatedit reads it, run `beatedit.py spec <key>` -> ("pass" | "refused" | "host", why).
    refused: beatedit stopped on the footage (its SystemExit line). host: a traceback, a timeout, no beatedit, the Air
    away; the job is not filed this run and is not marked refused. The staged files go either way; the cut beatedit
    cached ($TMPDIR/beatedit/clips/clip_<key>_*) stays for the render on a pass and is removed on a refusal."""
    if not BEATEDIT.exists():
        return "host", f"no beatedit at {BEATEDIT}"
    jobs, srcs, clips = beatedit_dirs()
    jd, sd = jobs / key, srcs / key
    try:
        jd.mkdir(parents=True, exist_ok=True)
        sd.mkdir(parents=True, exist_ok=True)
        (jd / "job.json").write_text(json.dumps(job, indent=1))
        shutil.copy(src, sd / "src.mp4")
        try:
            r = subprocess.run([sys.executable, str(BEATEDIT), "spec", key], capture_output=True, text=True,
                               timeout=GATE_SECS, cwd=str(BEATEDIT.parent), start_new_session=True)
        except subprocess.TimeoutExpired:
            return "host", f"beatedit spec over {GATE_SECS} s"
        text = (r.stderr or "").strip()
        if r.returncode == 0:
            try:
                spec = json.loads(r.stdout)
                o = spec["open"]
                return "pass", f"line {o['a0']:.2f}+{o['voice_len']:.2f} s, red word {spec['red']['text']}, {len(spec['shots'])} beats"
            except (ValueError, KeyError, TypeError):
                return "pass", (text.splitlines() or [""])[-1][:300]
        last = (text.splitlines() or [f"exit {r.returncode}"])[-1]
        why = last.split(". this format needs")[0][:300]
        return ("host" if "Traceback" in text else "refused"), why
    finally:
        shutil.rmtree(jd, ignore_errors=True)
        shutil.rmtree(sd, ignore_errors=True)


# Short on beats, open found (11/7, j1362): "only N distinct moments of the edited debater fit a beat, 15 needed" is
# the gate's biggest refusal (34 of 11/6-11/7, in same-video runs: Cq9boZ4au8o x3, blNvE504OLQ x3, CcySYtrQGVg x3).
# render-farm/beatedit_feed.py pairs such a job with the same person's other edit jobs (BEATEDIT_BEATS_WITH: this
# job keeps its open and its share of the beats, each partner's share passes the same face, shot, motion and text
# bars), and pairing kept 0e2wThS_5oU_502/_6786, Z8nSnsmidQU_1392 and 3Xv_ZjIEKXk_741/_217/_496 on 11/6. But a job
# the gate refuses is never filed, so the feed never sees it. So one with N >= SHORT_MIN moments of a full-named
# person (a partner pool beatedit_feed accepts: no role, at most 3 partners) is filed as "short"; the feed renders it,
# beatedit refuses it alone in seconds off the cached cut, and the pair retry carries it. Nothing is lowered: the
# kept piece still passes every beatedit gate. Off with BRAIN_SHORT_PAIRS=0.
SHORT = re.compile(r"only (\d+) distinct moments of the edited debater fit a beat, (\d+) needed")
SHORT_MIN = 4          # beatedit_feed.partners: ceil(15 / N) - 1 partners, at most 3
SHORT_PAIRS = os.environ.get("BRAIN_SHORT_PAIRS", "1") != "0"
ROLE_NAME = re.compile(r"\b(panelist|caller|guest|host|student|audience|crowd|man|woman|guy|girl|member|speaker|"
                       r"challenger|christian|muslim|atheist|liberal|conservative|participant|person)s?\b", re.I)


# REOPEN (11/7, j1362): the gate's open repick (j1217) only reaches picks the gate itself refuses. A job filed before
# the gate, or one beatedit refuses at render (beatedit_feed.json: b75GNVh4ABo_865/_1209 and 0e2wThS_5oU_3558 11/6,
# "no line of the edited debater fits the open"), was never repicked. brain.py URL --reopen KEY runs the same open
# repick on it: the clash widened or shifted so REF's side says one line alone, read again, gated, filed new.


def short_lend(why, name):
    """True when a beatedit refusal is only too few beat moments and the feed can pair it (see SHORT above)."""
    m = SHORT.search(why or "")
    name = (name or "").strip()
    return bool(SHORT_PAIRS and m and int(m.group(1)) >= SHORT_MIN and full_name(name))


def full_name(name):
    """A person's own name ("Andrew Wilson", "Christian Wagner"): two words or more, each capitalized, one at least
    no role word. "a panelist", "Christian conservative", "Harris voter", "the moderator" are roles."""
    ws = (name or "").split()
    return len(ws) >= 2 and all(w[:1].isupper() for w in ws) and any(not ROLE_NAME.fullmatch(w) for w in ws)


def drop_cache(key):
    for d in beatedit_dirs()[2].glob(f"clip_{key}_*"):
        shutil.rmtree(d, ignore_errors=True)


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
    """The config dir of a Claude login with room for background work (the Max plan first), by ARENA's own rule.
    The answer is reused for 30 minutes: accounts.py reads usage over the network and has taken 6 minutes. A login
    that fills up meanwhile answers "usage limit" itself, which backs the feeder off."""
    if os.environ.get("BRAIN_CLAUDE_DIR"):
        return os.path.expanduser(os.environ["BRAIN_CLAUDE_DIR"])
    memo = pathlib.Path(os.path.expanduser("~/.render-farm/claude_login.json"))
    try:
        last = json.loads(memo.read_text())
    except (OSError, ValueError):
        last = {}
    if time.time() - last.get("at", 0) < 1800:
        return last["dir"]
    try:
        r = subprocess.run([sys.executable, ACCOUNTS, "pick", "--for", "task"], capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        if last.get("dir"):
            return last["dir"]  # no answer: the login that had room last time
        raise PickerDown("usage limit: chat/accounts.py did not answer which Claude login has room")
    if r.returncode or not r.stdout.strip():
        raise PickerDown("usage limit: no Claude login has room for the picker right now")
    memo.write_text(json.dumps({"dir": r.stdout.split()[0], "at": time.time()}))
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
    want, vids = {r[0] for r in rows}, got["videos"]
    if len(vids) == len(rows) and not any(v["id"].strip() in want for v in vids):
        vids = [dict(v, id=r[0]) for v, r in zip(vids, rows)]  # ids mangled but every row answered in order
    return {v["id"].strip(): {"debate": v["debate"], "figure": v["figure"].strip(), "why": v["why"].strip(), "by": by}
            for v in vids if v["id"].strip() in want}


ASSENT = {"yes", "yeah", "yep", "no", "nope", "absolutely", "certainly", "okay", "ok", "right", "sure", "agreed", "exactly", "correct"}
MAX_PICK = 19.5  # render.py plays 19 s or less ending on the payoff (MAX_CLIP): a longer pick loses its own hook


# --wire (68_wirepost's news desk, 10/17): the clip goes out today as breaking news ("JUST IN: A vs B"), so the
# moment the news is about is the pick, and a formal debate (timed answers, a moderator) is still a debate. The code
# checks below hold except one: a claim and its rebuttal (A then B, both state a case) stands without a third turn.
WIRE = False
WIRE_NOTE = """

WIRE MODE. This clip is posted today as breaking news, so the best pick is the moment the video's title and the news
are about (the line everyone is quoting), when it passes the tests. A formal debate with a moderator counts as two
sided when the two candidates or guests answer each other: look for the crosstalk, the rebuttals and the interruptions
inside the timed answers, where both speak inside 19 seconds. A payoff may be a sharp line aimed at the other person
when it is about the question they argue (test 4 and test 6 still rule out pure insults with no argument).
In wire mode test 3 reads: the other side answers inside 8 seconds and no one talks for more than 10 seconds. One
candidate's claim and the other's direct rebuttal is enough; it need not trade lines every 5 seconds. A timed debate
almost always has such a moment where one candidate answers the other by name, so return your best ones."""


WIRE_REVIEW = """

WIRE MODE. These picks come from a timed debate posted today and are cut as breaking news, the way a news desk clips
a candidate's line and the other's comeback. Rule 4 reads: the last line is a whole sentence that lands a point about
the question; timed answers run long, so more of the same answer after it does not make it WEAK. It is WEAK on 4 only
when the last line stops mid thought, or the words after it show it was a setup ("but here's the thing"). Rule 3: a
"he" or "she" in the first sentence that means the other candidate on stage is clear, since the title names both."""


# --edit (64_beatedit, ask a391 10/21): the pick is never played as a 19 s clip. It feeds a fan edit of ONE debater
# (a 6 s open on one of their lines, then half second shots of them talking), which needs 20 to 60 s of the exchange.
# The 19 s, hook-first and payoff-last rules starved the beat edit (0 fresh moments 10/21); two sides, the captions
# and take-not-person hold as written. Jobs carry "mode": "edit" and the clip farm never renders them.
EDIT = False
EDIT_MAX = 60.5
EDIT_NOTE = """

EDIT MODE. These picks are not played as a 19 second clip. Each feeds a fan edit of ONE debater (the better known
person in the exchange): a 6 second open on one sentence of theirs, then half second shots of them talking. So:
Length, first word to last: 20 to 60 seconds (this replaces the 10 to 19 second rule). Tests 1, 5 and 6 hold as
written. Test 3 reads: the other side answers inside 20 seconds and no one talks for more than 25 seconds. Tests 2
and 4 read: the exchange starts on the start of a sentence and ends on a finished sentence. Inside it the better
known person says one whole sentence of 3 to 6 seconds that lands on its own for a stranger (a claim, a comeback, a
number); put its hardest 2 to 6 words in kill_phrase (it may be in any line, not only the last). Prefer the exchanges
where that person makes their case the hardest."""


EDIT_REVIEW = """

EDIT MODE. These picks feed a fan edit of one debater, not a who won clip, and run 20 to 60 seconds. Rules 1, 2 and 6
hold as written. Rules 3 and 4 read: the pick starts on the start of a sentence and ends on a finished sentence, and
the kill phrase sits in one whole sentence a stranger gets on its own. Rule 5 holds for the title."""


def check(ex, words, edit=None):
    """What the picker claims, held against the transcript and the clock. -> "" when it stands, else why it is
    thrown out. (The length, turn and payoff tests came from the independent review of the first 21 picks, 10/7:
    all were real debates, but 16 ran past the 19 s that play and lost the opening they were picked for.)"""
    EDIT_ = EDIT if edit is None else edit   # a clip-route WEAK pick re-picked for the beat edit (11/6, a366)
    lines, t0, t1 = ex["lines"], ex["start"], ex["end"]
    if EDIT_ and not 20 <= t1 - t0 <= EDIT_MAX:
        return f"{t1 - t0:.0f} s: an edit pick is 20 to 60"
    if not EDIT_ and not 8 <= t1 - t0 <= MAX_PICK:
        return f"{t1 - t0:.0f} s: only 19 s play, a pick is 8 to 19"
    said = {}
    for l in lines:
        said[l["speaker"]] = said.get(l["speaker"], 0) + len([w for w in l["text"].split() if norm(w)])
    if len(said) < 2:
        return "one speaker"
    if min(said.values()) < 6:
        return f"one side says {min(said.values())} words: not two sides"
    # a side that only asks questions or only assents has made no case (review 2: cross examinations passed)
    stated = dict.fromkeys(said, 0)
    for l in lines:
        ws = [norm(w) for w in l["text"].split() if norm(w)]
        if not l["text"].strip().endswith("?"):
            stated[l["speaker"]] += len([w for w in ws if w not in ASSENT])
    if min(stated.values()) < 6:
        return "one side only asks or agrees: a cross examination, not a debate"
    if any(b["start"] <= a["start"] for a, b in zip(lines, lines[1:])):
        return "line times do not increase (speaker tags would flip)"
    # each voice's unbroken stretch, from the line times
    runs = [[lines[0]["speaker"], lines[0]["start"], t1]]
    for l in lines[1:]:
        if l["speaker"] != runs[-1][0]:
            runs[-1][2] = l["start"]
            runs.append([l["speaker"], l["start"], t1])
    if len(runs) < (2 if WIRE else 3):     # wire mode: a claim and its rebuttal, both heard, is the news moment
        return "no back and forth (the speaker changes once)"
    if runs[1][1] - t0 > (20 if EDIT_ else 10.5 if WIRE else 8):     # wire mode: a candidate's claim may run as long as any voice
        return f"no reply for {runs[1][1] - t0:.0f} s: the question is a speech"
    longest = max(e - b for _, b, e in runs)
    if longest > (25 if EDIT_ else 10.5):
        return f"one voice for {longest:.0f} s"
    # every line is what the captions say in its own stretch of time (a line stitched from elsewhere fails)
    for k, l in enumerate(lines):
        nxt = lines[k + 1]["start"] if k + 1 < len(lines) else t1
        heard = {norm(w) for t, w in words if l["start"] - 2.5 <= t <= nxt + 2.5}
        mine = [norm(w) for w in l["text"].split() if norm(w)]
        if mine and sum(w in heard for w in mine) / len(mine) < 0.6:
            return f"a line is not what the transcript says at {l['start']:.0f} s"
    kill = [norm(w) for w in ex["kill_phrase"].split() if norm(w)]
    last = [norm(w) for w in lines[-1]["text"].split() if norm(w)]
    if EDIT_:  # the edit's open line may be any of the debater's sentences
        last = [norm(w) for l in lines for w in l["text"].split() if norm(w)]
    if not kill or not any(last[i:i + len(kill)] == kill for i in range(len(last))):
        return "the kill phrase is not in the last line: the payoff is not the end"
    if not ex["retention"].strip() or not ex["hook_topic"].strip():
        return "no reason or no topic given"
    return ""


def snap_end(words, ex):
    """End on the last word of the last line as the captions time it, not on the picker's rounded guess (the review
    found stray words of the next sentence after 9 of 21 payoffs)."""
    last = [norm(w) for w in ex["lines"][-1]["text"].split() if norm(w)]
    near = [t for t, w in words if last and norm(w) == last[-1] and abs(t - ex["end"]) <= 4 and t > ex["lines"][-1]["start"]]
    return min(near, key=lambda t: abs(t + 0.5 - ex["end"])) + 0.5 if near else ex["end"]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def turn_tags(cap):
    """The word tags follow the line starts, which snap to the captions a word or two off, so a turn's first word
    ("Because", "That") went to the side before it and each side's line was cut mid sentence (11/6: beatedit refused
    DhpfsOSNakY_723 and u14d6ajzHZw_10938, "no line of the edited debater fits the open"). The captions mark each turn
    with ">>": every speaker change moves to the nearest mark within 2 s, between its neighbours, and the mark leaves
    the word text (it would show on screen)."""
    marks = [i for i, c in enumerate(cap) if c["w"].replace("&gt;", ">").startswith(">>")]
    bounds = [i for i in range(1, len(cap)) if cap[i]["s"] != cap[i - 1]["s"]]
    gap = lambda m, b: abs(cap[m]["t"] - cap[b]["t"])
    owned = {b: [] for b in bounds}   # each mark goes to its nearest speaker change only (a turn the captions left
    for m in marks:               # unmarked keeps its own place instead of taking the next turn's mark)
        if bounds:
            b = min(bounds, key=lambda b: (gap(m, b), b))
            if gap(m, b) <= 2.0:
                owned[b].append(m)
    new = []
    for n, b in enumerate(bounds):
        lo = new[-1] + 1 if new else 1
        hi = bounds[n + 1] - 1 if n + 1 < len(bounds) else len(cap) - 1
        near = [m for m in owned[b] if lo <= m <= hi]
        new.append(min(near, key=lambda m: gap(m, b)) if near else max(b, lo))
    out, side, k = [], cap[0]["s"] if cap else "A", 0
    for i, c in enumerate(cap):
        if k < len(new) and i == new[k]:
            side, k = cap[bounds[k]]["s"], k + 1
        w = re.sub(r"^(?:>>|&gt;&gt;)\s*", "", c["w"]).strip()
        if w:
            out.append(dict(c, w=w, s=side))
    return out


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
            words.append((ts(m.group(1)), html.unescape(first.group(1).strip())))
        for t, w in re.findall(r"<(\d\d:\d\d:\d\d\.\d+)><c>\s*([^<]*)</c>", line):
            if w.strip():
                words.append((ts(t), html.unescape(w.strip())))   # "&gt;&gt;" is the ">>" turn mark
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


# Windows (11/6, j1075): one picker call over a whole 18,000 word transcript returned 1.2 exchanges a video (93
# videos 11/6, 108 exchanges, 4 jobs): the model reads the start and skims the rest. The same prompt, the same tests
# and the same second reader now run on each WINDOW-word stretch of the captions (OVERLAP words shared, so a moment on
# a seam is whole in one of them), at most MAX_WINDOWS (longer windows on a long video), PICK_THREADS at a time. The video is a
# debate when most windows say so; exchanges come only from windows that do, best of each window first, and an
# exchange overlapping a better one is dropped.
WINDOW, OVERLAP, MAX_WINDOWS, PICK_THREADS = 3000, 250, int(os.environ.get("BRAIN_WINDOWS", 8)), 4


def windows(words):
    """[words, ...]: the caption words cut into stretches of at least WINDOW words (OVERLAP shared with the next), at
    most MAX_WINDOWS of them. A long video gets longer windows, never skipped stretches; a tail under half a window
    joins the window before it instead of costing a call of its own."""
    if len(words) <= WINDOW + OVERLAP:
        return [words]
    size = max(WINDOW, -(-(len(words) - OVERLAP) // MAX_WINDOWS))
    starts = list(range(0, len(words) - OVERLAP, size))
    if len(starts) > 1 and len(words) - starts[-1] < size // 2:
        starts.pop()
    return [words[a:(starts[k + 1] + OVERLAP if k + 1 < len(starts) else len(words))] for k, a in enumerate(starts)]


def pick_windows(title, channel, words, n, note=""):
    """The picker on each window -> ({"debate": .., "exchanges": [at most n]}, by). PickerDown in any window is
    raised at once (windows not started are cancelled), so the feeder backs off without spending more usage."""
    import concurrent.futures as cf
    parts = windows(words)
    if len(parts) == 1:
        return ask(PROMPT.format(title=title, channel=channel, n=n, transcript=transcript_text(words), voices=voices_note())
                   + rapid_note(words) + note, SCHEMA)
    per = max(1, min(n, 6))
    def one(part):
        try:
            return ask(PROMPT.format(title=title, channel=channel, n=per, transcript=transcript_text(part),
                                     voices=voices_note()) + rapid_note(part) + note, SCHEMA)
        except PickerDown:
            raise
        except Exception as e:   # one window's bad answer loses that window only
            print(f"window at {part[0][0]:.0f} s failed: {str(e)[-200:]}", file=sys.stderr)
            return None
    pool = cf.ThreadPoolExecutor(PICK_THREADS)
    futs = [pool.submit(one, part) for part in parts]
    try:
        got = [f.result() for f in futs]
    except PickerDown:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown()
    got = [g for g in got if g]
    if not got:
        raise RuntimeError("every picker window failed")
    yes = [g for g, by in got if g["debate"]["two_sided"]]
    verdict = dict((yes or [g for g, _ in got])[0]["debate"])
    verdict["two_sided"] = 2 * len(yes) >= len(got)
    verdict["why"] = f"{len(yes)} of {len(got)} windows two sided. " + verdict["why"]
    exs, depth = [], max((len(g["exchanges"]) for g in yes), default=0)
    for r in range(depth):   # rank 1 of every window, then rank 2, ...
        for g in yes:
            if r < len(g["exchanges"]):
                ex = g["exchanges"][r]
                if not any(ex["start"] < o["end"] and o["start"] < ex["end"] for o in exs):
                    exs.append(ex)
    exs = exs[:n]   # --max still caps what one video returns
    print(f"picker windows: {len(parts)} x ~{len(parts[0])} words, {len(exs)} exchanges", file=sys.stderr)
    return {"debate": verdict, "exchanges": exs}, got[0][1]


def _raw_voices(words):
    """Each word's voice: the diarizer segment holding its time, else the nearest within 1.5 s ("" none)."""
    import bisect
    starts = [a for a, _, _ in SEGS]
    out = []
    for t, _ in words:
        i = bisect.bisect_right(starts, t) - 1
        best, gap = "", 1.5
        for k in (i, i + 1):
            if 0 <= k < len(SEGS):
                a, b, sp = SEGS[k]
                d = 0 if a <= t <= b else min(abs(t - a), abs(t - b))
                if d < gap:
                    best, gap = sp, d
        out.append(best)
    return out


def smooth_voices(words, out, min_words=3, min_secs=1.0, reach=1.5):
    """Clean word voices (11/6, j1088): j946's test put raw diarizer tags in front of the picker and the second reader,
    and the reader pulled picks because "the voice tags break in the middle of sentences" (3w4PLc2r0Yc_1081,
    MPXLCKZVz14_675). 1) a run of another voice shorter than min_words words or min_secs seconds is crosstalk or a
    diarizer slip and keeps its neighbours' voice; 2) every remaining change of voice moves to the nearest real turn
    point within reach seconds: a ">>" caption turn mark first, else a sentence end, else a pause of 0.6 s or more."""
    out = list(out)
    for k in range(len(out)):          # words with no voice take the one before them
        if not out[k] and k:
            out[k] = out[k - 1]
    def runs():
        r = []
        for k, v in enumerate(out):
            if r and r[-1][0] == v:
                r[-1][2] = k
            else:
                r.append([v, k, k])
        return r
    changed = True
    while changed:
        changed = False
        rs = runs()
        for n, (v, a, b) in enumerate(rs):
            short = b - a + 1 < min_words or words[b][0] - words[a][0] < min_secs
            if short and 0 < n < len(rs) - 1:   # an edge run may be a turn cut by the window: it stays
                fill = rs[n - 1][0]
                for k in range(a, b + 1):
                    out[k] = fill
                changed = True
                break
    def turn_point(k):   # 2 = caption turn mark, 1 = sentence end or pause before word k, 0 = none
        w = words[k][1]
        if w.startswith(">>") or w in ("-", "--") or (k and words[k - 1][1] in ("-", "--")):
            return 2   # ">>" auto-caption turn marks; "- " opens a new speaker in hand-made captions
        if k and (words[k - 1][1][-1:] in ".?!" or words[k][0] - words[k - 1][0] >= 0.6):
            return 1
        return 0
    rs = runs()
    for n in range(1, len(rs)):
        b = rs[n][1]                   # first word of the new voice
        lo, hi = rs[n - 1][1] + 1, rs[n][2]
        cands = [k for k in range(lo, hi + 1) if abs(words[k][0] - words[b][0]) <= reach and turn_point(k)]
        if not cands or turn_point(b) == 2:
            continue
        k = min(cands, key=lambda k: (-turn_point(k), abs(words[k][0] - words[b][0])))
        for x in range(min(k, b), max(k, b)):
            out[x] = rs[n - 1][0] if k > b else rs[n][0]
    return out


VOICE_CACHE = {}


def voice_of(words):
    """Each caption word's voice from the diarizer ("" without one), cleaned by smooth_voices over the whole video
    once (set_voices) and looked up per word, so a window or a pick reads the same tags."""
    if not SEGS:
        return [""] * len(words)
    if not VOICE_CACHE:
        return smooth_voices(words, _raw_voices(words))
    return [VOICE_CACHE.get((t, w), "") for t, w in words]


def set_voices(words):
    VOICE_CACHE.clear()
    if SEGS:
        VOICE_CACHE.update({(t, w): v for (t, w), v in zip(words, smooth_voices(words, _raw_voices(words)))})


def voices_note():
    return VOICES if SEGS else NO_VOICES


def rapid_note(part):
    """The diarizer's fast stretches inside this window, as a reading hint (empty without the diarizer)."""
    if not SEGS or not part:
        return ""
    rapid = [r for r in diarize.rapid_stretches(SEGS, part, voices=voice_of(part))]
    return RAPID.format(stretches="\n".join(f"{x:.1f} to {y:.1f} s: {c} changes of voice" for x, y, c in rapid)) if rapid else ""


def transcript_text(words):
    """Caption lines; with the diarizer, a new line at every change of voice, tagged with the voice (S1, S2 ...)."""
    lines, cur, t0, v0 = [], [], None, ""
    for (t, w), v in zip(words, voice_of(words)):
        if cur and SEGS and v and v != v0:
            lines.append(f"{t0:.1f} [{v0}] {' '.join(cur)}"); cur, t0 = [], None
        if t0 is None:
            t0, v0 = t, v or v0
        cur.append(w)
        if t - t0 > 8 and w[-1:] in ".?!" or t - t0 > 14:
            lines.append(f"{t0:.1f} " + (f"[{v0}] " if SEGS else "") + " ".join(cur)); cur, t0 = [], None
    if cur:
        lines.append(f"{t0:.1f} " + (f"[{v0}] " if SEGS else "") + " ".join(cur))
    return "\n".join(lines)


def tagged(words, a, b):
    """The raw caption words from a to b, with the diarizer's voice tag at each change of voice."""
    out, last = [], None
    for (t, w), v in zip(words, voice_of(words)):
        if a <= t < b:
            if SEGS and v and v != last:
                out.append(f"[{v}]"); last = v
            out.append(w)
    return " ".join(out)


SEGS = []   # the diarizer's [(start, end, "S1")] for the video being picked; [] = plain captions
VOICES = """ After the time, [S1], [S2] ... is the voice speaking, from a speaker diarizer run on the audio:
a new line starts when the voice changes. Use the tags as a hint for who speaks when, never as proof: they miss turns
at crosstalk, can give one person two tags, and can merge two people who sound alike. When the words show a turn the
tags missed, trust the words. A and B in your answer are people, not tags."""
NO_VOICES = " Captions carry no speaker labels: work out who is speaking from the words."
RAPID = """

RAPID STRETCHES. The diarizer found these windows of 19 s or less where the voice changes three or more times between
two people who each say six words or more. They are where short clashes live: read each one (and the lines around it)
first, and pick from them when one passes every test. A stretch is a hint, not a pick; its edges are not your start and
end.
{stretches}"""


STRETCHES = """

THIS TRANSCRIPT IS ONLY THE FAST STRETCHES. The video was already ruled two sided. Below are only the stretches of it
where the diarizer heard the voice change three or more times inside 19 seconds, each with the lines around it, cut
out of the video in time order ("..." marks the cut between two stretches). Read every stretch whole and return the
exchange it holds when one passes every test (most hold none: zero is still a correct answer). An exchange never
crosses a "..."."""


def stretch_pass(title, channel, words, have, most=8):
    """A second, focused read (11/6, ask a357): the first read over a whole video returned 1 to 3 picks however many
    fast stretches the diarizer found (7WjuYFgseDQ: 1 pick, 20 stretches). The picker gets only the busiest stretches
    it did not already pick from, each whole with 25 s before and 12 s after, and rules on each. -> new exchanges."""
    rapid = diarize.rapid_stretches(SEGS, words, voices=voice_of(words))
    free = [r for r in sorted(rapid, key=lambda r: -r[2])
            if not any(r[0] < e["end"] and e["start"] < r[1] for e in have)][:most]
    if not free:
        return []
    wins = []
    for x, y, _ in sorted(free):
        x, y = x - 25, y + 12
        if wins and x <= wins[-1][1]:
            wins[-1][1] = max(wins[-1][1], y)
        else:
            wins.append([x, y])
    text = "\n...\n".join(transcript_text([(t, w) for t, w in words if x <= t <= y]) for x, y in wins)
    try:
        got, by = ask(PROMPT.format(title=title, channel=channel, n=len(free), transcript=text, voices=VOICES)
                      + STRETCHES, SCHEMA)
    except Exception as e:   # the first read stands on its own
        print(f"stretch pass failed: {str(e)[:160]}", file=sys.stderr)
        return []
    new = [e for e in got.get("exchanges", []) if not any(e["start"] < h["end"] and h["start"] < e["end"] for h in have)]
    print(f"stretch pass {by}: {len(free)} stretches in {len(wins)} windows, {len(new)} new exchanges", file=sys.stderr)
    return new


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


# "auto" (default): plain captions first, speaker labels only for a video that kept nothing; "1" always; "0" never
DIARIZE = os.environ.get("BRAIN_DIARIZE", "auto")


def main():
    ap = argparse.ArgumentParser()
    if "--recut-stats" in sys.argv[1:]:
        return recut_stats()
    ap.add_argument("url")
    ap.add_argument("--recut-stats", action="store_true", help="print end recuts tried, read-kept and filed per day "
                    "from ~/.render-farm/recut_ledger.jsonl, then stop (no url needed)")
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--wire", action="store_true", help="breaking news picks for 68_wirepost (see WIRE_NOTE)")
    ap.add_argument("--edit", action="store_true", help="20 to 60 s picks for 64_beatedit's fan edit (see EDIT_NOTE)")
    ap.add_argument("--reopen", default="", help="KEY[,KEY]: filed edit jobs of this video that beatedit refused at render "
                    "for no open line; each gets one open repick (the same clash widened or shifted, see REOPEN)")
    ap.add_argument("--dry", action="store_true", help="print the picks and their reasons; judge, download and file nothing")
    ap.add_argument("--dry-read", action="store_true", help="--dry plus check(), the second reader and the end recut")
    a = ap.parse_args()
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}

    with tempfile.TemporaryDirectory() as tmp:
        info, words = fetch(a.url, pathlib.Path(tmp))
    vid, title, channel = info["id"], info.get("title", ""), info.get("channel", "")
    print(f"{vid}: {title} — {len(words)} caption words", file=sys.stderr)
    cache = HERE / "picks" / f"{vid}_wire.json"  # wire mode keeps its picks, so a rerun rereads them instead of rerolling
    if a.wire and cache.exists():
        got, by = json.loads(cache.read_text()), "cached picks"
    else:
        try:
            global SEGS
            SEGS = diarize.turns(vid, sys.stderr) if DIARIZE == "1" else []
            set_voices(words)
            rapid = diarize.rapid_stretches(SEGS, words, voices=voice_of(words)) if SEGS else []
            print(f"diarizer: {len(SEGS)} segments, {len({s for *_, s in SEGS})} voices, {len(rapid)} rapid stretches",
                  file=sys.stderr)
            if a.reopen:   # REOPEN: no new picks, only the open repick of the named jobs below
                got, by = {"debate": {"two_sided": True, "why": "reopen of filed edit jobs"}, "exchanges": []}, "reopen"
            else:
                got, by = pick_windows(title, channel, words, a.max, (WIRE_NOTE if a.wire else "") + (EDIT_NOTE if a.edit else ""))
        except PickerDown as e:
            sys.exit(f"picker down, {e}")  # the feeder reads "usage limit" here and backs off instead of failing the source
        if a.wire:
            cache.parent.mkdir(exist_ok=True)
            cache.write_text(json.dumps(got, indent=1))
    global WIRE, EDIT
    WIRE, EDIT = a.wire, a.edit or bool(a.reopen)
    if SEGS and got["debate"]["two_sided"] and not (a.wire or a.edit):
        got["exchanges"] += stretch_pass(title, channel, words, got["exchanges"])
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

    made, stood = 0, []
    for rank, ex in enumerate(exchanges, 1):  # the picker returns its best first
        key = f"{vid}_{int(ex['start'])}"
        why_not = "already in the ledger" if key in ledger else check(ex, words)
        if why_not:
            print(f"skip {key}: {why_not}", file=sys.stderr); continue
        stood.append((key, rank, ex))
    read, read_by = {}, ""
    if stood:
        try:
            read, read_by = second_read(title, channel, [(k, ex) for k, _, ex in stood], words)
        except PickerDown as e:
            sys.exit(f"picker down, {e}")
    kept, recut, weak = [], [], []
    verdicts = {key: read.get(key, ("PULL", "the second reader gave no verdict", [])) for key, _, _ in stood}
    renamed = {}   # a367: picks whose title names someone the captions never say, under the sides' own labels
    to_name = [(key, ex) for key, _, ex in stood if not EDIT and name_fault(*verdicts[key], ex, words)]
    if to_name:
        try:
            renamed = relabel(to_name, words)
        except Exception as e:   # no labels, no rename: the picks go on as they were
            print(f"rename failed: {str(e)[-200:]}", file=sys.stderr)
    for key, rank, ex in stood:
        verdict2, why2, fails = verdicts[key]
        if verdict2 == "KEEP" or (EDIT and verdict2 == "WEAK"):   # WEAK fails only the clip's hook and window
            # rules (3 to 5); beatedit picks its own open sentence and gates it, so an edit pick stops only on PULL
            kept.append((key, rank, ex, read_by, why2)); continue
        print(f"skip {key}: second reader, {verdict2.lower()}: {why2}", file=sys.stderr)
        if EDIT or verdict2 != "WEAK":
            continue
        weak.append((key, rank, ex))   # a366: a WEAK pick nothing below saves goes to the beat edit
        base = renamed.get(key, ex)
        if key in renamed:
            print(f"rename {key}: {', '.join(base['renamed_from'].values())} never said, title now "
                  f"\"{base['matchup']} {base['hook_topic']}\"", file=sys.stderr)
        if not end_only(verdict2, why2, fails):
            if key in renamed:   # the same lines under the new names, to the second reader again
                recut.append((key, rank, dict(base, recut_from=key)))
            continue
        cuts, no_cut = caption_recut(base, words)
        if not cuts:
            print(f"recut {key}: no caption cut, {no_cut}", file=sys.stderr)
            note_recut(key, "no_cut", a.dry_read, no_cut); continue
        # only picks that can still be filed block a recut (a pulled or weak neighbour is never filed)
        others = [e for k, _, e in stood if k != key and verdicts[k][0] == 'KEEP'] + [e for _, _, e in recut]
        for n, cut in enumerate(cuts):
            key2 = f"{vid}_{int(cut['start'])}" + ("" if n == 0 else f"_{int(cut['end'])}")
            why_not = ("already in the ledger" if f"{vid}_{int(cut['start'])}" in ledger else
                       "overlaps another pick" if any(cut["start"] < o["end"] and o["start"] < cut["end"] for o in others)
                       else check(cut, words))
            if why_not:
                print(f"recut {key} -> {key2}: {why_not}", file=sys.stderr); note_recut(key, "check", a.dry_read, why_not); continue
            print(f"recut {key} -> {key2}: {cut['start']:.1f} to {cut['end']:.1f} s, to the second reader again", file=sys.stderr)
            cut["recut_from"], cut["cut_end"] = key, True
            recut.append((key2, rank, cut))
    if recut:
        try:
            read2, read2_by = second_read(title, channel, [(k, ex) for k, _, ex in recut], words)
        except Exception as e:   # no fresh read, no recut filed
            read2, read2_by = {}, f"second read failed, {e}"
        for key, rank, ex in recut:
            verdict2, why2, _ = read2.get(key, ("PULL", "the second reader gave no verdict", []))
            how = "recut" if ex.get("cut_end") else "renamed"
            if verdict2 != "KEEP":     # once: a recut or rename that is not a fresh KEEP is dropped, never tried again
                print(f"skip {key}: {how}, second reader, {verdict2.lower()}: {why2}", file=sys.stderr)
                note_recut(key, verdict2.lower(), a.dry_read, f"[{how}] {why2}", ex.get("recut_from")); continue
            if any(k[2].get("recut_from") == ex.get("recut_from") for k in kept):
                continue   # both ends of one pick kept: the first (the shorter) is filed
            print(f"{how} {key}: second reader, keep: {why2}", file=sys.stderr)
            note_recut(key, "read_keep", a.dry_read, f"[{how}] {why2}", ex.get("recut_from"))
            ex["recut"] = bool(ex.get("cut_end"))   # a recut's end already sits on its sentence end; a rename's is snapped
            kept.append((f"{vid}_{int(ex['start'])}", rank, ex, f"{read2_by} ({'recut end' if ex['recut'] else 'renamed'})", why2))
    saved = {ex.get("recut_from") for _, _, ex, _, _ in kept}
    weak = [(k, r, e) for k, r, e in weak if k not in saved and set(verdicts[k][2]) <= {3, 4, 5}]
    if weak and BEATEDIT_GATE and split_screen(title, channel):   # a391: beatedit refuses the blank panel
        print(f"no edit repick: a call or stream (split screen), beatedit cannot cut it ({', '.join(k for k, _, _ in weak)})",
              file=sys.stderr)
        weak = []
    if weak:
        try:
            picks, eby = edit_repick(title, channel, words, [(k, e) for k, _, e in weak], [e for _, _, e, _, _ in kept], len(weak))
        except Exception as e:   # the clip picks stand as they are; no edit job this run
            picks, eby = [], ""
            print(f"edit repick failed: {str(e)[-200:]}", file=sys.stderr)
        print(f"edit repick {eby}: {len(picks)} 20 to 60 s picks around {len(weak)} weak "
              f"({', '.join(k for k, _, _ in weak)})", file=sys.stderr)
        stood_e, refused = [], {k: v for k, v in gated().items() if v in ("refused", "crowd")}
        for ex, src in picks:
            ex["edit_from"] = src
            key = f"{vid}_{int(ex['start'])}"
            why_not = ("already in the ledger" if key in ledger else
                       f"beatedit gate said {refused[key]} before" if key in refused else
                       "same key as a kept pick" if any(k == key for k, *_ in kept) else check(ex, words, edit=True))
            if why_not:
                print(f"skip edit {key}: {why_not}", file=sys.stderr); continue
            stood_e.append((key, ex))
        if stood_e:
            try:
                read3, read3_by = second_read(title, channel, stood_e, words, edit=True)
            except Exception as e:
                read3, read3_by = {}, f"second read failed, {e}"
            for key, ex in stood_e:
                verdict3, why3, _ = read3.get(key, ("PULL", "the second reader gave no verdict", []))
                if verdict3 == "PULL":   # edit mode files KEEP and WEAK, never PULL (as brain.py --edit does)
                    print(f"skip edit {key}: second reader, pull: {why3}", file=sys.stderr); continue
                print(f"edit {key}: second reader, {verdict3.lower()}: {why3}", file=sys.stderr)
                ex["edit"] = True   # edit_from: the one weak pick it was widened around
                kept.append((key, 0, ex, f"{read3_by} (edit from weak)", why3))
    if not kept and DIARIZE == "auto" and verdict_on_video["two_sided"] and exchanges and not a.wire:
        # auto: plain captions kept nothing, so the same video again with speaker labels (on 10 rapid videos the
        # plain windows kept 11 and labels 4, but labels kept 2 on koC8A86BS2k where plain kept 0): labels only add
        print(f"auto diarize: 0 kept from {len(exchanges)} plain exchanges, again with speaker labels", file=sys.stderr)
        sys.stderr.flush(); sys.stdout.flush()
        os.execve(sys.executable, [sys.executable, os.path.abspath(__file__), *sys.argv[1:]],
                  {**os.environ, "BRAIN_DIARIZE": "1"})
    if a.dry_read:
        print(json.dumps({"video": {"id": vid, "title": title}, "first_read": {k: list(v) for k, v in read.items()},
                          "kept": [{"key": k, "recut": bool(ex.get("recut")), "renamed": ex.get("renamed_from"),
                                    "edit": bool(ex.get("edit")), "start": ex["start"], "end": ex["end"],
                                    "lines": ex["lines"], "second_read": w} for k, _, ex, _, w in kept]}, indent=1))
        print(f"dry read: {len(kept)} kept ({sum(1 for k in kept if k[2].get('recut'))} by recut, "
              f"{sum(1 for k in kept if k[2].get('renamed_from'))} renamed, {sum(1 for k in kept if k[2].get('edit'))} edit) of "
              f"{len(exchanges)} exchanges", file=sys.stderr)
        return
    def repick_open(key, ex, side, why):   # j1217: once per pick, the open on REF's side (OPEN_NOTE)
        if not OPEN_REPICK or ex.get("open_from"):
            return
        try:
            e2, by2 = open_repick(title, channel, words, ex, side, why, [o for _, _, o, _, _ in kept if o is not ex])
        except Exception as e:
            e2, by2 = None, f"open repick failed: {str(e)[-200:]}"
        if e2 is None:
            print(f"open repick {key}: none, {by2}", file=sys.stderr); return
        k2 = f"{vid}_{int(e2['start'])}"
        if k2 == key or any(k == k2 for k, *_ in kept):   # widened at the end only: the start key is taken
            k2 = f"{vid}_{int(e2['start'])}_{int(e2['end'])}"
        if k2 in ledger or any(k == k2 for k, *_ in kept) or gated().get(k2) in ("refused", "crowd"):
            print(f"open repick {key}: {k2} already in the ledger, kept or refused", file=sys.stderr); return
        try:
            r3, r3_by = second_read(title, channel, [(k2, e2)], words, edit=True)
        except Exception as e:
            print(f"open repick {key}: second read failed, {e}", file=sys.stderr); return
        v3, w3, _ = r3.get(k2, ("PULL", "the second reader gave no verdict", []))
        if v3 == "PULL":
            print(f"open repick {key} -> {k2}: second reader, pull: {w3}", file=sys.stderr); return
        e2.update(edit=True, open_from=key, open_side=ex["a_name"] if side == "A" else ex["b_name"],
                  **({"edit_from": ex["edit_from"]} if ex.get("edit_from") else {}))
        print(f"open repick {key} -> {k2} ({e2['start']:.0f} to {e2['end']:.0f} s): second reader, {v3.lower()}: {w3}",
              file=sys.stderr)
        kept.append((k2, rank, e2, f"{by2} (open repick of {key})", w3))   # the loop below reaches it in turn

    for key in [k for k in a.reopen.split(",") if k]:   # REOPEN
        jf = JOBS / key / "job.json"
        if not key.startswith(vid + "_") or not jf.exists():
            print(f"reopen {key}: no filed job of {vid}", file=sys.stderr); continue
        old = json.loads(jf.read_text())
        ex = {k: v for k, v in old.items() if k not in ("key", "mode", "source", "picker", "words", "judge_request",
                                                          "judge_response", "open_from", "open_side")}
        ex.setdefault("picked_at", (old["start"], old["end"]))
        try:
            side = focus_of(old["judge_response"], old.get("words") or [])
        except (KeyError, TypeError):
            print(f"reopen {key}: REF gave no side scores", file=sys.stderr); continue
        print(f"reopen {key}: beatedit found no open line of {ex['a_name'] if side == 'A' else ex['b_name']} in "
              f"{old['start']:.0f} to {old['end']:.0f} s; one open repick", file=sys.stderr)
        repick_open(key, ex, side, "beatedit found no 3 to 6.3 s line of theirs alone here with no camera cut inside a word")

    for ex in (k[2] for k in kept):
        ex["picked_at"] = (ex["start"], ex["end"])   # the window as picked, before the snap below moves it
    for key, rank, ex, read_by, why2 in kept:
        ex.setdefault("picked_at", (ex["start"], ex["end"]))
        for l in ex["lines"]:
            l["start"] = snap(words, l["start"], l["text"])
        ex["start"] = ex["lines"][0]["start"]  # open on the question itself, never on leftover words
        if not ex.get("recut"):   # a recut's end already sits on its sentence end, clear of the next word
            ex["end"] = snap_end(words, ex)
        edit = EDIT or bool(ex.get("edit"))
        if ex["end"] - ex["start"] > (EDIT_MAX if edit else MAX_PICK):
            print(f"skip {key}: {ex['end'] - ex['start']:.0f} s once snapped to the captions", file=sys.stderr); continue
        # caption words for this exchange, each tagged with whoever's line it falls in
        span = [(t, w) for t, w in words if ex["start"] - 0.05 <= t <= ex["end"] + 0.05]
        starts = [(l["start"], l["speaker"]) for l in ex["lines"]]
        cap = turn_tags([{"t": round(t, 2), "w": w, "s": max([s for s in starts if s[0] <= t + 0.05] or [starts[0]])[1]}
                         for t, w in span])
        req, verdict = judge(ex)
        if not verdict.get("success"):
            print(f"judge failed {key}", file=sys.stderr); continue
        if edit and BEATEDIT_GATE and crowd_wins(ex, verdict, title, channel):   # a391: the crowd side is never on
            print(f"skip edit {key}: 1 vs N show and REF favours the crowd side, beatedit finds no open", file=sys.stderr)
            note_gate(key, "crowd"); continue                                    # camera for a whole line
        try:
            side = focus_of(verdict, cap) if edit else None
        except (KeyError, TypeError):
            side = None
        if edit and ex.get("open_from") and side is None:
            print(f"skip edit {key}: REF gave no side scores", file=sys.stderr); continue
        if edit and ex.get("open_from") and not same_person(ex["a_name"] if side == "A" else ex["b_name"], ex["open_side"]):
            print(f"skip edit {key}: REF now favours the other side, not {ex['open_side']}", file=sys.stderr); continue
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
        ex["take_hook"] = re.sub(r"\s+-+\s+|\s*[\u2013\u2014]\s*", " ", ex.get("take_hook") or "").strip()
        if len(re.findall(r"[\w'%]+", ex["take_hook"].replace("*", ""))) > 7:
            ex["take_hook"] = ""   # over the copy rule's seven words: the title falls back to the matchup
        job = {"key": key, **({"mode": "edit"} if edit else {}), "source": {"url": a.url, "id": vid, "title": title, "channel": channel, "t0": round(t0, 2)},
               **ex, "picker": {"by": by, "at": time.strftime("%F %T"), "rank": rank, "video": verdict_on_video["why"],
                          "second_reader": read_by, "second_read": why2},
               "words": cap, "judge_request": req, "judge_response": verdict}
        if edit and BEATEDIT_GATE:   # a391: file an edit job only once beatedit has cut the window and found its open
            outcome, why = beatedit_spec(key, job, d / "src.mp4")
            if outcome == "refused" and short_lend(why, ex.get("a_name" if side == "A" else "b_name") if side else ""):
                outcome = "short"            # filed for beatedit_feed's pair retry; the cut stays cached for it
            note_gate(key, outcome, why + (f" (open repick of {ex['open_from']})" if ex.get("open_from") else ""))
            if outcome == "short":
                print(f"beatedit spec {key}: short, filed for a pair retry: {why}", file=sys.stderr)
            elif outcome != "pass":
                print(f"skip edit {key}: beatedit spec {'refused' if outcome == 'refused' else 'did not run'}: {why}",
                      file=sys.stderr)
                shutil.rmtree(d, ignore_errors=True)
                if outcome == "refused":
                    drop_cache(key)
                    if NO_OPEN in why and side:   # the lines were there but beatedit cut none, or burned-in text
                        # covered them (a shifted window can fall on a stretch with none: Z8nSnsmidQU_7684)
                        repick_open(key, ex, side, "every line of theirs here is under 3 s, ends mid thought, or has a "
                                                   "camera cut inside a word")
                continue
            if outcome == "pass":
                print(f"beatedit spec {key}: pass, {why}", file=sys.stderr)
        (d / "job.json").write_text(json.dumps(job, indent=1))
        if ex.get("recut_from"):
            note_recut(key, "filed", False, "[recut]" if ex.get("recut") else "[renamed]", ex.get("recut_from"))
        # several brains run at once (render-farm feeder): merge with what the others wrote since we started
        ledger = {**(json.loads(LEDGER.read_text()) if LEDGER.exists() else {}), key: {"title": title, "motion": ex["motion"]}}
        tmp = LEDGER.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(ledger, indent=1))
        tmp.replace(LEDGER)
        made += 1
        print(f"job {key}: {'[edit] ' if ex.get('edit') else ''}{ex['matchup']} — {ex['motion']}", file=sys.stderr)
        print(f"  holds because: {ex['retention']}", file=sys.stderr)
    print(f"{made} jobs from {len(exchanges)} exchanges", file=sys.stderr)


if __name__ == "__main__":
    main()
