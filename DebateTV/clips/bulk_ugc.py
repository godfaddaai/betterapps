#!/usr/bin/env python3
"""Bulk UGC: turn the existing parts (reaction faces x debate clips x hooks) into thousands
of DISTINCT reels, without ever rendering the same combination twice.

make_ugc.py renders ONE reel from one (reaction, hook, debate) triple. This wraps it:
inventories the parts, plans unused triples, renders them in parallel, shards the output
into per-account folders, and remembers what it already made in used.json — so tomorrow's
batch is new even if you forget what yesterday's was.

  python3 bulk_ugc.py inventory                 # what we have and how many reels it can make
  python3 bulk_ugc.py plan 200                  # write a manifest of 200 unused combos
  python3 bulk_ugc.py build 200                 # plan + render + shard into ACCOUNT_01..N
  python3 bulk_ugc.py build 36 --workers 4 --out ~/Desktop/DebateTV_POST_0920

Rules baked in (from the fleet's scar tissue):
- The same debate clip never goes in two reels in the same batch until every clip has been
  used once, so one day's posts are never near-duplicates of each other.
- A (reaction, hook, debate) triple is never repeated across runs: used.json is the ledger.
- Output is written LOCAL, never iCloud: a full iCloud silently zeroed a whole batch once.
- Renders run in parallel workers because ffmpeg is the slow part (~45-95s per reel).

Edit config.json (auto-created) to add reaction folders, clip folders, or hooks.
"""
import argparse
import itertools
import json
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "bulk_config.json")
USED = os.path.join(HERE, "bulk_used.json")
ICLOUD = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/DebateTV Debates")
VID = (".mp4", ".mov", ".MOV", ".MP4", ".m4v")

# 10/7 (ask a039, "retire the Starbucks takes"): the reaction face comes from the cleared list only, the list the
# hand-off and queue gates check (~/Documents/ARENA/render-farm/cleared_reactions.py). The founders' own takes and
# their shared reaction clips are retired, and no folder of clips can be named here any more: a config that still
# lists one stops the run. No cleared clip that fits = the run stops with a plain message; nothing falls back.
sys.path.insert(0, os.path.expanduser("~/Documents/ARENA/render-farm"))
try:
    import cleared_reactions as CR  # noqa: E402
except ImportError:
    CR = None

DEFAULT_CONFIG = {
    "_note": "Paths are expanded with ~.",
    "_reaction_note": "Reactions are the cleared list (python3 ~/Documents/ARENA/render-farm/cleared_reactions.py "
                      "list). A take we may post joins by getting a row in that list, never a folder here.",
    "political": True,
    "_political_note": "Are the debate clips political? true (the safe answer when nobody checked every clip): "
                       "only faces whose license has no political limit. false: Pexels faces too.",
    "clip_dirs": [
        f"{ICLOUD}/Reels",
        f"{ICLOUD}/Enhanced",
        f"{ICLOUD}/Jun20 Clips",
        f"{ICLOUD}/June19 Sports Reels",
        f"{ICLOUD}/June19 Non-Sports Reels",
        f"{ICLOUD}/Viral Clips",
        f"{ICLOUD}/POST THESE",
    ],
    "_skip_note": "Reels_pre-apostrophe-fix is the same 29 clips with a caption bug. Raw LiveKit "
                  "recordings are full debates, not clips: run debate_clips.py on them first.",
    "hooks": [
        "he really said this with his whole chest 💀",
        "POV: you have to debate this guy for 3 minutes",
        "bro argued this with a straight face 👀",
        "i cannot believe he actually won this one",
        "tell me he's wrong. i'll wait.",
        "this took an insane turn at the end",
        "he had NO business winning this",
        "an AI judged this and picked a side 😭",
        "who's actually right here",
        "i lost my mind at 0:08",
    ],
    "caption_template": "settle it on DebateTV 🏆 who's right? {tags}",
    "tag_sets": [
        "#debate #freespeech #america",
        "#debate #philosophy #hottake",
        "#debate #goat #nba",
        "#debate #firstamendment #politics",
        "#debate #argument #truth",
    ],
    "music": "",
    "_music_note": "Path to the bed that plays under the UGC/reaction portion and ducks under "
                   "the demo. Empty = no music. Tracks available: assets/music/{epic,feelgood,"
                   "got_trial,interstellar,oppenheimer,phonk,tension}.mp3",
    "music_vol": 0.22,
    "logo": "",
    "_logo_note": "Watermark shown for the whole reel, lower-left so it clears TikTok's own UI. "
                  "Empty = none. e.g. ~/DebateTV2/debate-tv-landingpage/dtv-logo.png",
    "react_secs": 2.6,
    "accounts_shard_size": 9,
}


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def config():
    if not os.path.exists(CONFIG):
        save_json(CONFIG, DEFAULT_CONFIG)
        print(f"wrote {CONFIG} — edit it to add folders or hooks")
    return load_json(CONFIG, DEFAULT_CONFIG)


def files_in(dirs):
    out = []
    for d in dirs:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            print(f"  (missing) {d}")
            continue
        for name in sorted(os.listdir(d)):
            if name.startswith(".") or not name.endswith(VID):
                continue
            p = os.path.join(d, name)
            # An iCloud file that hasn't downloaded is a 0-byte placeholder; rendering it
            # produces a broken reel, so skip it and say so.
            if os.path.getsize(p) < 50_000:
                print(f"  (not downloaded / too small) {p}")
                continue
            out.append(p)
    return out


def cleared_reactions(cfg):
    """file -> its row in the cleared list, for every clip that may open these reels. Stops when there is none."""
    who = "bulk_ugc"
    if CR is None:
        sys.exit(f"\nNO CLEARED REACTION for {who}: ~/Documents/ARENA/render-farm/cleared_reactions.py is missing.\n"
                 f"  Nothing was built. The founder takes are retired and nothing falls back to them.\n")
    old = [k for k in ("reaction_dirs", "reaction_has_hook") if cfg.get(k)]
    if old:
        CR.stop(who, f"{os.path.basename(CONFIG)} still sets {' and '.join(old)} (a folder of the founders' reaction "
                     f"clips). Delete those keys: the face comes from the cleared list only")
    return {CR.path_of(r): r for r in CR.fitting(cfg.get("political", True), who, cfg["react_secs"])}


def inventory(cfg):
    lib = cleared_reactions(cfg)
    reactions = list(lib)
    clips = files_in(cfg["clip_dirs"])
    # a stock face reacts to the clip; a first person line would put words in that person's mouth (their license)
    mine = [h for h in cfg["hooks"] if CR.speaks_for_the_person(h)]
    hooks = [h for h in cfg["hooks"] if h not in mine]
    if not hooks:
        CR.stop("bulk_ugc", "every hook line is in the first person, and a stock face never speaks as a user")
    used = load_json(USED, [])
    total = len(reactions) * len(clips) * len(hooks)
    print(f"\nreactions      {len(reactions)}  (cleared list, {'political' if cfg.get('political', True) else 'not political'}"
          f", at least {cfg['react_secs']} s)")
    print(f"debate clips   {len(clips)}")
    print(f"hooks          {len(hooks)}" + (f"  ({len(mine)} first person lines set aside for a stock face)" if mine else ""))
    print(f"combinations   {total:,}  (already rendered: {len(used):,})")
    print(f"remaining      {total - len(used):,} reels available with today's parts")
    print(f"\nat 108 posts/day that is {(total - len(used)) // 108 if total else 0} days of content")
    print("More raw debates in LiveKit Recordings can become new clips: debate_clips.py")
    return lib, clips, hooks


def plan(cfg, n):
    lib, clips, hooks = inventory(cfg)
    reactions = list(lib)
    if not reactions or not clips:
        sys.exit("\nNeed at least one reaction and one debate clip.")
    used = set(tuple(u) for u in load_json(USED, []))
    rng = random.Random(0xDEBA7E)

    # Walk clips in order and rotate reaction+hook, so a batch spreads across every clip
    # before reusing one. Skip any triple already rendered in an earlier run.
    # Shuffle so one batch spreads across topics instead of walking four cuts of the
    # same debate in a row (the first test batch was four "is cereal a soup" clips).
    rng.shuffle(clips)
    items, guard = [], 0
    clip_cycle = itertools.cycle(clips)
    ri = hi = 0
    while len(items) < n and guard < n * 200:
        guard += 1
        clip = next(clip_cycle)
        reaction = reactions[ri % len(reactions)]
        hook = hooks[hi % len(hooks)]
        ri += 1
        if ri % len(reactions) == 0:
            hi += 1
        key = (os.path.basename(reaction), hook, os.path.basename(clip))
        if key in used:
            continue
        used.add(key)
        slug = os.path.splitext(os.path.basename(clip))[0].lower()
        slug = "".join(c if c.isalnum() else "-" for c in slug).strip("-")[:40]
        items.append({
            "id": len(items) + 1,
            "slug": slug,
            "reaction": reaction,
            "reaction_id": lib[reaction]["id"],
            "reaction_license": lib[reaction]["license"].split(":")[0],
            "hook": hook,
            "debate": clip,
            "react_secs": cfg["react_secs"],
            "caption": cfg["caption_template"].format(tags=rng.choice(cfg["tag_sets"])),
            "prebaked_hook": False,     # a cleared face is silent and carries no text: the hook card is drawn
            "music": os.path.expanduser(cfg["music"]) if cfg.get("music") else None,
            "music_vol": cfg.get("music_vol", 0.22),
            "logo": os.path.expanduser(cfg["logo"]) if cfg.get("logo") else None,
            "_key": list(key),
        })
    if len(items) < n:
        print(f"\nonly {len(items)} unused combinations left — add reactions, clips or hooks")
    return items


DEMOS = os.path.expanduser("~/Documents/BetterApps/DebateTV/clips/demo_pool")


# Only recordings from this date forward carry the branded composite (two-up, motion title,
# FOR/AGAINST plates). Earlier ones are a single camera with a corner thumbnail: appended to a
# reaction they read as two faces in a row, not an app demo. Verified 2026-09-20 on the June 19
# Steph Curry recording vs the September 6 Odyssey one.
BRANDED_FROM = "2026-09"


def cut_demos(sources, seconds, skip_head=20, skip_tail=15):
    """Slice finished debate recordings into short app-demo segments.

    The recordings are the product on screen: two-up video, motion title, FOR/AGAINST plates,
    no TestFlight status bar. One 3-minute recording becomes ~10 demo segments, and every new
    segment multiplies against all 335 reactions.

    skip_head/skip_tail drop the waiting room and the verdict screen at the ends.
    """
    os.makedirs(DEMOS, exist_ok=True)
    made = 0
    for src in sources:
        base = os.path.basename(os.path.dirname(src)) or os.path.basename(src)
        base = "".join(c if c.isalnum() else "-" for c in base.lower())[:48]
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", src], capture_output=True, text=True)
        try:
            dur = float(probe.stdout.strip())
        except ValueError:
            print(f"  unreadable: {src}")
            continue
        t = skip_head
        idx = 0
        while t + seconds <= dur - skip_tail:
            idx += 1
            out = os.path.join(DEMOS, f"{base}_{idx:02d}.mp4")
            if not os.path.exists(out):
                r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", src,
                                    "-t", str(seconds), "-vf", "scale=1080:1920:force_original_aspect_ratio="
                                    "increase,crop=1080:1920,fps=30,setsar=1",
                                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", out],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    print(f"  cut failed {out}: {r.stderr[-160:]}")
                    continue
            made += 1
            t += seconds
        print(f"  {base}: {idx} segments")
    print(f"demo pool now holds {len([f for f in os.listdir(DEMOS) if f.endswith('.mp4')])} clips ({made} this run)")


def prune_demos(threshold=16.0):
    """Move demo segments with a dead black band to _rejected.

    Some older recordings render one camera plus a black filler column where the second
    participant should be. Cropped to 9:16 that reads as a broken video, and it is where the
    logo would sit. Measures average brightness of the left and right fifth of a mid frame.
    """
    rej = os.path.join(DEMOS, "_rejected")
    os.makedirs(rej, exist_ok=True)
    moved = kept = 0
    for name in sorted(f for f in os.listdir(DEMOS) if f.endswith(".mp4")):
        src = os.path.join(DEMOS, name)
        dark = False
        for crop in ("iw/5:ih:0:0", "iw/5:ih:iw*4/5:0"):
            r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "3", "-i", src, "-frames:v", "1",
                                "-vf", f"crop={crop},signalstats,metadata=print:key=lavfi.signalstats.YAVG",
                                "-f", "null", "-"], capture_output=True, text=True)
            out = r.stderr + r.stdout
            for line in out.splitlines():
                if "YAVG" in line:
                    try:
                        if float(line.split("=")[-1]) < threshold:
                            dark = True
                    except ValueError:
                        pass
        if dark:
            os.rename(src, os.path.join(rej, name))
            moved += 1
        else:
            kept += 1
    print(f"demo pool: kept {kept}, rejected {moved} (black band) -> {rej}")


def render_pair(reaction, demo, out, music=None, music_vol=0.22, duck_vol=0.07, logo=None):
    """Reaction clip (its own hook text + speech, kept whole) hard-cut to the demo clip.

    Separate from make_ugc.render because that one drops the reaction's audio and pastes a
    hook card on top — both wrong when the reaction already says the hook out loud.

    music: optional bed under the whole reel, louder under the reaction (the UGC portion)
    and ducked under the demo so the debate audio stays intelligible. Time-based, not
    sidechain: sidechain once silenced the hook entirely.
    """
    norm = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1"
    app = norm + ",unsharp=5:5:0.9:5:5:0.0,eq=contrast=1.06:saturation=1.09:gamma=1.02"
    # Logo rides the WHOLE reel, low on the frame so it clears the platform's own UI:
    # TikTok's caption block and buttons sit in the lower right, so we keep left-bottom.
    vout = "[v]"
    logo_chain = ""
    if logo:
        vout = "[vl]"
        logo_chain = (f";[3:v]scale=190:-1,format=rgba,colorchannelmixer=aa=0.85[lg];"
                      f"[v][lg]overlay=x=48:y=H-h-190{vout}")
    fc = (f"[0:v]{norm}[a];[1:v]{app}[b];[a][b]concat=n=2:v=1:a=0[v];"
          f"[0:a]aresample=48000,highpass=f=85,loudnorm=I=-15:TP=-1.5[ra];"
          f"[1:a]aresample=48000,highpass=f=85,loudnorm=I=-15:TP=-1.5[da];"
          f"[ra][da]concat=n=2:v=0:a=1,alimiter=limit=0.95[aout]")
    inputs = ["-i", reaction, "-i", demo]
    if music:
        rdur = _dur(reaction)
        total = rdur + _dur(demo)
        inputs += ["-stream_loop", "-1", "-i", music]
        fc += (f";[2:a]aresample=48000,atrim=0:{total},asetpts=PTS-STARTPTS,"
               f"volume='if(lt(t,{rdur}),{music_vol},{duck_vol})':eval=frame[bed];"
               f"[bed][aout]amix=inputs=2:dropout_transition=0:normalize=0,"
               f"alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5[mixed]")
        amap = "[mixed]"
    else:
        amap = "[aout]"
    if logo:
        # Third input slot is music when present, so the logo is always input 3.
        if not music:
            inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        inputs += ["-i", logo]
        fc += logo_chain
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", fc,
           "-map", vout, "-map", amap, "-r", "30", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-400:])


def render_one(item, out_dir):
    name = f"{item['id']:04d}_{item['slug']}"
    out = os.path.join(out_dir, name + ".mp4")
    CR.from_file(item["reaction"], f"bulk_ugc reel {item['id']}")     # a cleared clip, or the run stops
    if item.get("prebaked_hook"):
        render_pair(item["reaction"], item["debate"], out,
                    music=item.get("music"), music_vol=item.get("music_vol", 0.22),
                    logo=item.get("logo"))
    else:
        sys.path.insert(0, HERE)
        import make_ugc  # imported here so `inventory` works without ffmpeg/Chrome
        make_ugc.render(item["reaction"], item["hook"], item["debate"], out,
                        react_secs=item.get("react_secs", 2.6), tmp=f"/tmp/ugc_work_{item['id']}")
    if not os.path.exists(out) or os.path.getsize(out) < 100_000:
        raise RuntimeError(f"render produced nothing usable: {out}")
    with open(os.path.join(out_dir, name + ".txt"), "w") as f:
        f.write(item["caption"] + "\n")
    return out


def shard(out_dir, size):
    reels = sorted(f for f in os.listdir(out_dir) if f.endswith(".mp4"))
    for i, reel in enumerate(reels):
        folder = os.path.join(out_dir, f"ACCOUNT_{i // size + 1:02d}")
        os.makedirs(folder, exist_ok=True)
        for ext in (".mp4", ".txt"):
            src = os.path.join(out_dir, reel.replace(".mp4", ext))
            if os.path.exists(src):
                os.rename(src, os.path.join(folder, os.path.basename(src)))
    return (len(reels) + size - 1) // size


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inventory", "plan", "build", "cut-demos", "prune-demos"])
    ap.add_argument("n", nargs="?", type=int, default=36)
    ap.add_argument("--out", default=os.path.expanduser("~/Desktop/DebateTV_BULK"))
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--seconds", type=int, default=15, help="cut-demos: length of each demo segment")
    ap.add_argument("--recordings", default=os.path.expanduser(
        "~/Library/Mobile Documents/com~apple~CloudDocs/DebateTV Debates/LiveKit Recordings"))
    ap.add_argument("--only", help="cut-demos: substring filter on recording folder name")
    ap.add_argument("--all-eras", action="store_true",
                    help="cut-demos: include pre-branding recordings (single camera, no app UI)")
    args = ap.parse_args()
    cfg = config()

    if args.cmd == "prune-demos":
        prune_demos()
        return

    if args.cmd == "cut-demos":
        root = os.path.expanduser(args.recordings)
        srcs = []
        for name in sorted(os.listdir(root)):
            if args.only and args.only.lower() not in name.lower():
                continue
            if not args.all_eras and name[:7] < BRANDED_FROM:
                continue  # pre-branding recording: no app UI on screen
            f = os.path.join(root, name, "debate.mp4")
            if os.path.exists(f) and os.path.getsize(f) > 1_000_000:
                srcs.append(f)
        print(f"cutting {len(srcs)} recordings into {args.seconds}s demo segments")
        cut_demos(srcs, args.seconds)
        return

    if args.cmd == "inventory":
        inventory(cfg)
        return

    items = plan(cfg, args.n)
    manifest = os.path.join(HERE, "bulk_manifest.json")
    save_json(manifest, items)
    print(f"\nplanned {len(items)} reels -> {manifest}")
    if args.cmd == "plan":
        return

    out_dir = os.path.expanduser(args.out)
    if "Mobile Documents" in out_dir:
        sys.exit("Refusing to render into iCloud — a full iCloud silently zeroed a batch once.")
    os.makedirs(out_dir, exist_ok=True)
    done, failed = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(render_one, it, out_dir): it for it in items}
        for fut in as_completed(futures):
            it = futures[fut]
            try:
                fut.result()
                done.append(it)
                print(f"  [{len(done)}/{len(items)}] {it['slug'][:40]}")
            except Exception as e:
                failed.append((it["id"], str(e)[:120]))

    # Only triples that actually rendered go in the ledger, so a failure can be retried.
    used = load_json(USED, [])
    used += [it["_key"] for it in done]
    save_json(USED, used)
    folders = shard(out_dir, cfg["accounts_shard_size"])
    print(f"\nrendered {len(done)}, failed {len(failed)} -> {out_dir} in {folders} account folders")
    for fid, err in failed[:5]:
        print(f"  failed #{fid}: {err}")
    print("AirDrop one ACCOUNT_ folder per phone account. Never post the same file twice.")


if __name__ == "__main__":
    main()
