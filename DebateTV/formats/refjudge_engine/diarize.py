"""Who speaks when, for the picker (11/6, ask a346 / j812): YouTube auto-captions carry no speaker labels, so the
picker guessed turns from the words and 32 of 90 picks in a day died on "the speaker changes once". This gives it
voices: the video's audio (bestaudio, 16 kHz mono, on the SSD) through pyannote segmentation 3.0 + a WeSpeaker
English embedding (sherpa-onnx, CPU, no token), cached per video.

    python3 diarize.py <video id or url>       -> prints the turns, caches /Volumes/Untitled/ARENA-media/diar-cache/<id>.json
    (runs on the Air first, ~/render/diar_air.py; this Mac only when the Air fails)

brain.py calls turns(vid) -> [(start, end, "S1"), ...] or [] when anything fails (the picker then reads plain captions).
The model run happens in ~/.render-farm/diar-venv (python 3.12, sherpa-onnx); this file itself runs on any python.
"""
import json, os, pathlib, subprocess, sys, time

SSD = pathlib.Path(os.environ.get("DIAR_HOME", "/Volumes/Untitled/ARENA-media"))
CACHE = SSD / "diar-cache"
MODELS = SSD / "diar-models"
VENV_PY = pathlib.Path(os.path.expanduser(os.environ.get("DIAR_PY", "~/.render-farm/diar-venv/bin/python")))
THRESHOLD = float(os.environ.get("DIAR_THRESHOLD", "0.6"))   # clustering distance; lower = more speakers
TIMEOUT = int(os.environ.get("DIAR_TIMEOUT", "3000"))         # a 2.6 h debate is ~28 min on the Air
WAIT = int(os.environ.get("DIAR_WAIT", "1500"))               # most seconds a brain queues for the Air
ROUTE = os.environ.get("DIAR_ROUTE", "air")                   # air; mac (slow under load, by hand); auto = Air then Mac

RUNNER = r"""
import json, sys, numpy as np, soundfile as sf, sherpa_onnx
wav, seg, emb, thr, out = sys.argv[1:6]
cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
    segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=seg), num_threads=4),
    embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=emb, num_threads=4),
    clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=float(thr)),
    min_duration_on=0.3, min_duration_off=0.4)
sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
audio, sr = sf.read(wav, dtype="float32", always_2d=True)
r = sd.process(audio[:, 0]).sort_by_start_time()
json.dump([[round(s.start, 2), round(s.end, 2), int(s.speaker)] for s in r], open(out, "w"))
"""


def _audio(vid, dst):
    """bestaudio -> 16 kHz mono wav. This Mac's yt-dlp first; the file stays on the SSD."""
    raw = dst.with_suffix(".m4a")
    if not raw.exists():
        subprocess.run(["yt-dlp", "--no-warnings", "-q", "-f", "bestaudio[ext=m4a]/bestaudio", "-o", str(raw),
                        f"https://www.youtube.com/watch?v={vid}"], check=True, timeout=900)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(raw), "-ac", "1", "-ar", "16000", str(dst)],
                   check=True, timeout=600)
    raw.unlink(missing_ok=True)


AIR = os.environ.get("BRAIN_AIR", "air")   # the render farm Mac: ~/render/diar_air.py in ~/render/diar-venv
LOCK = pathlib.Path(os.path.expanduser("~/.render-farm/diar.lock"))


def _on_air(vid, out):
    """The Air fetches the audio itself and returns the turns (RTF ~0.18 with 6 threads, 11/6: 300 s in 53 s; this
    Mac ran >0.4 at load 250). One video at a time there: brains queue on a lock instead of piling onto its cores."""
    import fcntl
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "w") as lk:
        t0 = time.time()
        while True:   # the feeder kills a brain at 75 min: past WAIT in line, this video goes on plain captions
            try:
                fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB); break
            except BlockingIOError:
                if time.time() - t0 > WAIT:
                    raise TimeoutError(f"waited {WAIT // 60} min for the Air diarizer")
                time.sleep(10)
        if out.exists():          # another brain diarized this video while we waited
            return
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=60", AIR,
                            f"perl -e 'alarm {TIMEOUT}; exec @ARGV' $HOME/render/diar-venv/bin/python "
                            f"$HOME/render/diar_air.py '{vid}' {THRESHOLD}"],
                           check=True, timeout=TIMEOUT + 60, capture_output=True, text=True)
        segs = json.loads(r.stdout.strip().splitlines()[-1])
        out.write_text(json.dumps(segs))


def _on_mac(vid, out):
    wav = CACHE / f"{vid}.wav"
    try:
        if not wav.exists():
            _audio(vid, wav)
        subprocess.run([str(VENV_PY), "-c", RUNNER, str(wav),
                        str(MODELS / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"),
                        str(MODELS / "wespeaker_en.onnx"), str(THRESHOLD), str(out)],
                       check=True, timeout=TIMEOUT, capture_output=True, text=True)
    finally:
        wav.unlink(missing_ok=True)


def turns(vid, log=None):
    """[(start, end, "S<n>")] sorted, speakers numbered by first appearance. [] when it cannot run."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{vid}.json"
    if not out.exists():
        errs = []
        for name, route in (("air", _on_air), ("mac", _on_mac)) if ROUTE == "auto" else ((ROUTE, {"air": _on_air, "mac": _on_mac}[ROUTE]),):
            try:
                route(vid, out)
                break
            except Exception as e:   # no diarization is never a failed video: the picker reads plain captions
                errs.append(f"{name}: {str(e)[:120]}")
        if not out.exists():
            if log:
                print(f"diarize {vid}: failed, plain captions ({'; '.join(errs)})", file=log)
            return []
    raw = json.loads(out.read_text())
    names = {}
    for _, _, s in raw:
        names.setdefault(s, f"S{len(names) + 1}")
    return [(a, b, names[s]) for a, b, s in raw]


def speaker_at(segs, t):
    """The voice talking at time t (the segment holding t, else the nearest one within 1.5 s)."""
    best, gap = None, 1.5
    for a, b, s in segs:
        if a <= t <= b:
            return s
        d = min(abs(t - a), abs(t - b))
        if d < gap:
            best, gap = s, d
    return best


def rapid_stretches(segs, words, max_len=19.0, min_turns=3):
    """Windows of at most max_len seconds holding min_turns+ voice changes between two voices who each say 6+ words:
    where a short clash lives. -> [(t0, t1, n_changes)] best first, non overlapping."""
    spk = [(t, speaker_at(segs, t)) for t, _ in words]
    spk = [(t, s) for t, s in spk if s]
    runs = []
    for t, s in spk:
        if runs and runs[-1][0] == s:
            runs[-1][2] = t; runs[-1][3] += 1
        else:
            runs.append([s, t, t, 1])
    runs = [r for r in runs if r[3] >= 2]            # a one word blip is crosstalk, not a turn
    found = []
    for i in range(len(runs)):
        j = i
        while j + 1 < len(runs) and runs[j + 1][2] - runs[i][1] <= max_len:
            j += 1
        win = runs[i:j + 1]
        voices = {}
        for s, _, _, n in win:
            voices[s] = voices.get(s, 0) + n
        top = sorted(voices.values(), reverse=True)
        changes = sum(1 for a, b in zip(win, win[1:]) if a[0] != b[0])
        if changes >= min_turns and len(top) >= 2 and top[1] >= 6:
            found.append((win[0][1], win[-1][2], changes))
    found.sort(key=lambda f: -f[2])
    keep = []
    for f in found:
        if all(f[1] <= k[0] or f[0] >= k[1] for k in keep):
            keep.append(f)
    return sorted(keep)


if __name__ == "__main__":
    v = sys.argv[-1]   # "--" before an id that starts with "-"
    v = v.split("v=")[-1].split("&")[0] if "v=" in v else v
    segs = turns(v, sys.stderr)
    print(f"{v}: {len(segs)} segments, {len({s for *_, s in segs})} voices")
    for a, b, s in segs[:40]:
        print(f"{a:8.1f} {b:8.1f} {s}")
