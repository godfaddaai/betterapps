#!/usr/bin/env python3
"""DebateTV UGC factory: [reaction face + hook text] -> [debate clip] = 1 UGC reel.
Fully automated. Reads a manifest of (reaction, hook, debate_clip) and renders numbered
files + caption txt into one POST folder, ready to AirDrop to phone and post.

Usage:
  python3 make_ugc.py manifest.json /path/to/POST_folder
manifest.json: [{"id":1,"reaction":"...mov","hook":"he said a hot dog isn't a sandwich","debate":"...mp4","caption":"...","react_secs":3.0}, ...]
"""
import subprocess, os, sys, json, html

# 10/7 (ask a039, "retire the Starbucks takes"): the reaction face is a clip from the cleared list or nothing is built.
# The founders' takes (~/Downloads/my reactions, ~/Downloads/ugc) and any other file stop the run with a plain
# message; there is no fallback. The list: python3 ~/Documents/ARENA/render-farm/cleared_reactions.py list
sys.path.insert(0, os.path.expanduser("~/Documents/ARENA/render-farm"))
try:
    import cleared_reactions as CR
except ImportError:
    CR = None


def cleared(reaction, who, political=None, secs=0.0, hook=None):
    if CR is None:
        raise SystemExit(f"\nNO CLEARED REACTION for {who}: ~/Documents/ARENA/render-farm/cleared_reactions.py is "
                         f"missing.\n  Nothing was built. The founder takes are retired and nothing falls back to them.\n")
    CR.for_reel(reaction, who, political, secs, hook)   # in the list, allowed on this piece, long enough, no "i" line


CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def hook_card(text, dst):
    """NATIVE INSTAGRAM-TEXT hook (Reagan+Hudson Jun-23 call): looks like text typed
    in the IG composer — clean white sentence-case sans, soft shadow for legibility,
    sat in the upper area over the reaction. NO designed card / no red box."""
    page=f"""<body style='margin:0'><div style="display:flex;align-items:flex-start;justify-content:center;height:100vh;padding:230px 60px 0;box-sizing:border-box">
    <div style="color:#fff;font-family:-apple-system,'Helvetica Neue',Helvetica,Arial,sans-serif;font-weight:700;
    font-size:64px;line-height:1.12;text-align:center;letter-spacing:-0.5px;max-width:960px;
    text-shadow:0 2px 14px rgba(0,0,0,.55),0 1px 3px rgba(0,0,0,.7)">{html.escape(text)}</div></div></body>"""
    hp=dst+".html"; open(hp,"w").write(page)
    subprocess.run([CHROME,"--headless","--disable-gpu","--hide-scrollbars",f"--screenshot={dst}",
        "--window-size=1080,1920","--default-background-color=00000000",f"file://{hp}"],capture_output=True)
    os.remove(hp)

def fitwide(tag="a", extra=""):
    """TikTok-native 'widen': fit the WHOLE frame (never crop/magnify) over a blurred fill of
    itself. Unique label `tag` so two chains can live in one filter_complex without colliding."""
    return (f"split[{tag}bs][{tag}fs];"
            f"[{tag}bs]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"gblur=sigma=42,eq=brightness=-0.16:saturation=0.85[{tag}b];"
            f"[{tag}fs]scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos[{tag}f];"
            f"[{tag}b][{tag}f]overlay=(W-w)/2:(H-h)/2,fps=30,setsar=1" + extra)
CRISP=",unsharp=5:5:0.9:5:5:0.0,eq=contrast=1.06:saturation=1.09:gamma=1.02"
# app/debate footage = a screen recording: upscale crisp + light contrast/sat pop
MUSIC=os.path.expanduser("~/.claude/skills/video-edit/music/bg-feelgood-builder.mp3")

def _dur(p):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",p],capture_output=True,text=True)
    try: return float(r.stdout.strip())
    except: return 0.0

def render(reaction, hook, debate, out, react_secs=3.0, tmp="/tmp/ugc_work", political=None):
    cleared(reaction, "make_ugc", political, react_secs, hook)
    os.makedirs(tmp, exist_ok=True)
    card=os.path.join(tmp,"hook.png"); hook_card(hook, card)
    total=react_secs+_dur(debate); rms=int(react_secs*1000)
    music=MUSIC if os.path.exists(MUSIC) else None
    # AUDIO DESIGN (fixed Jun-22): native reaction audio DROPPED (awkward). Music bed plays
    # full reel — LOUD on the hook, auto-ducked under the debate speech via sidechain.
    # Debate speech: gentle clean only (highpass + moderate loudnorm) — NO harsh EQ/compressor.
    cmd=["ffmpeg","-y","-t",str(react_secs),"-i",reaction,"-i",card,"-i",debate]
    if music: cmd+=["-stream_loop","-1","-i",music]
    fc=(f"[0:v]{fitwide('r')}[rv];[rv][1:v]overlay=0:0[r];"
        f"[2:v]{fitwide('d',CRISP)}[d];[r][d]concat=n=2:v=1:a=0[v];"
        # debate speech, delayed to start after the hook, gentle clean only:
        f"[2:a]aresample=48000,highpass=f=90,loudnorm=I=-16:TP=-2:LRA=11,"
        f"adelay={rms}|{rms},apad=whole_dur={total}[sp]")
    if music:
        # music: LOUD on the hook (0..react_secs), ducked under debate speech after. Time-based,
        # so the hook is never silent. Hard limiter at the end guarantees no clipping/ear-pain.
        fc+=(f";[3:a]aresample=48000,atrim=0:{total},asetpts=PTS-STARTPTS,"
             f"volume='if(lt(t,{react_secs}),0.45,0.15)':eval=frame[mus];"
             f"[mus][sp]amix=inputs=2:dropout_transition=0:normalize=0,"
             f"alimiter=limit=0.9,loudnorm=I=-15:TP=-1.5[a]")
        amap="[a]"
    else:
        amap="[sp]"
    cmd+=["-filter_complex",fc,"-map","[v]","-map",amap,"-t",str(total),
          "-r","30","-c:v","libx264","-preset","medium","-crf","20",
          "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",out]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode!=0: return False, r.stderr[-1500:]
    return True, None

def main(manifest_path, outdir):
    man=json.load(open(manifest_path)); os.makedirs(outdir, exist_ok=True)
    for m in man:       # all of them, before the first render. "political": false on an item allows a Pexels face
        cleared(m["reaction"], f"make_ugc reel {m['id']}", m.get("political"), m.get("react_secs", 3.0), m.get("hook"))
    ok=0
    for m in man:
        i=m["id"]; out=os.path.join(outdir, f"{i:02d}_{m.get('slug','ugc')}.mp4")
        good,err=render(m["reaction"], m["hook"], m["debate"], out, m.get("react_secs",3.0))
        if good:
            ok+=1
            cap=os.path.join(outdir, f"{i:02d}_{m.get('slug','ugc')}.txt")
            open(cap,"w").write(m.get("caption","")+"\n")
            print(f"[{i:02d}] OK -> {os.path.basename(out)}")
        else:
            print(f"[{i:02d}] FAIL: {err}")
    print(f"DONE {ok}/{len(man)}")

if __name__=="__main__":
    main(sys.argv[1], sys.argv[2])
