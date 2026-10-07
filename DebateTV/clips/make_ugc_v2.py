#!/usr/bin/env python3
"""DebateTV UGC factory v2 — value-first, Hormozi captions, viral sound design.

Per reel: [reaction face + native IG-text hook ~2.5s] -> [debate clip: Hormozi word-by-word
captions (Anton, yellow active word), top brand-bar hiding the iOS status bar, app crisp-up,
viral SFX punch on the cut] -> end CTA. Music bed loud on hook, ducked under speech.

Upgrades over v1 (Apify-validated, Jun-24): captions are the proven Hormozi style; status bar
is covered (capture leak); a viral SFX hits the hook->clip cut; end CTA drives comments/sends.

  python3 make_ugc_v2.py manifest.json /path/to/POST_folder
manifest item: {"id","slug","reaction","hook","debate","caption","react_secs":2.5,"sfx":"x_vine_boom.mp3"}
"""
import subprocess, os, sys, json, html, re

# 10/7 (ask a039, "retire the Starbucks takes"): the reaction face is a clip from the cleared list or nothing is built.
# The founders' takes (~/Downloads/my reactions, ~/Downloads/ugc) and any other file stop the run with a plain
# message; there is no fallback. The list: python3 ~/Documents/ARENA/render-farm/cleared_reactions.py list
sys.path.insert(0, os.path.expanduser("~/Documents/ARENA/render-farm"))
try:
    import cleared_reactions as CR
except ImportError:
    CR = None


def cleared(reaction, who):
    if CR is None:
        raise SystemExit(f"\nNO CLEARED REACTION for {who}: ~/Documents/ARENA/render-farm/cleared_reactions.py is "
                         f"missing.\n  Nothing was built. The founder takes are retired and nothing falls back to them.\n")
    CR.from_file(reaction, who)


GARBLE={"chachibuki":"ChatGPT","chachibut":"ChatGPT","hermosy":"Hormozi","hermozi":"Hormozi","aspikasa":"a Picasso","kik":"Kick","wismo":"Wizzmo","wizmo":"Wizzmo"}
def degarble(w):
    lw=w.lower().strip(".,!?")
    if lw in GARBLE:
        fixed=GARBLE[lw]
        return w.replace(w.strip(".,!?"),fixed)
    if lw=="slot" : return w  # "AI slot"->"AI slop" needs context; handled below
    return w

CLIPS=os.path.expanduser("~/Documents/BetterApps/DebateTV/clips")
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
J2A=os.path.join(CLIPS,"captools/json_to_ass.py")
FONTS=os.path.join(CLIPS,"captools/fonts")
ANTON=os.path.join(FONTS,"Anton-Regular.ttf")
WHISPER_MODEL="/Users/username/Documents/BetterApps/DebateTV/clips/models/ggml-small.en.bin"
ASSETS=os.path.join(CLIPS,"assets")
BRANDLOCKUP=os.path.join(ASSETS,"brand/brandbar_lockup.png")  # 1080x175 badge+wordmark
BRANDBAR=os.path.join(ASSETS,"meme/brandbar.png")          # 1080x150, covers status bar
WORDMARK=os.path.join(ASSETS,"meme/debatetv_wordmark.png") # 560x150, placed lowered (IG-safe)
ENDCTA=os.path.join(ASSETS,"meme/endcta.png")              # 1080x1920 end card
MUSIC=os.path.expanduser("~/.claude/skills/video-edit/music/bg-feelgood-builder.mp3")
SFXDIR=os.path.join(ASSETS,"sfx")
CAPCACHE=os.path.expanduser("~/Desktop/DebateTV_POST/_captioned")  # cache captioned debate clips
VERDICT_CARD=os.path.expanduser("~/Desktop/DebateTV_POST/_clips/VERDICT_CARD.mp4")  # generic sped-up AI verdict/VICTORY + "full debate on IG"

def fitwide(tag="a", extra=""):
    """TikTok-native 'widen': fit the WHOLE frame (never crop/magnify) over a blurred fill of
    itself. Unique label `tag` so two chains can live in one filter_complex without colliding."""
    return (f"split[{tag}bs][{tag}fs];"
            f"[{tag}bs]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"gblur=sigma=42,eq=brightness=-0.16:saturation=0.85[{tag}b];"
            f"[{tag}fs]scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos[{tag}f];"
            f"[{tag}b][{tag}f]overlay=(W-w)/2:(H-h)/2,fps=30,setsar=1" + extra)
CRISP=",unsharp=5:5:0.9:5:5:0.0,eq=contrast=1.06:saturation=1.09:gamma=1.02"

def _dur(p):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",p],capture_output=True,text=True)
    try: return float(r.stdout.strip())
    except: return 0.0

def caption_and_brand(debate, tmp="/tmp/ugc2_cap"):
    """Hormozi-caption + brand-bar (hide status bar) + app crisp. Cached by basename. Keeps audio."""
    os.makedirs(CAPCACHE, exist_ok=True); os.makedirs(tmp, exist_ok=True)
    base=os.path.splitext(os.path.basename(debate))[0]
    out=os.path.join(CAPCACHE, base+".cap.mp4")
    if os.path.exists(out) and os.path.getmtime(out)>os.path.getmtime(debate): return out
    wav=os.path.join(tmp,base+".wav")
    subprocess.run(["ffmpeg","-y","-i",debate,"-ar","16000","-ac","1",wav],capture_output=True)
    subprocess.run(["whisper-cli","-m",WHISPER_MODEL,"-f",wav,"-ml","1","-oj","-of",os.path.join(tmp,base)],capture_output=True)
    # whisper json -> flat word json
    d=json.load(open(os.path.join(tmp,base+".json")))
    words=[]
    for s in (d.get("transcription") or []):
        w=(s.get("text") or "").strip(); o=s.get("offsets") or {}
        # strip leading/trailing punctuation (keep internal apostrophes); drop punctuation-only tokens
        w=re.sub(r"^[^0-9A-Za-z]+|[^0-9A-Za-z']+$","",w)
        w=degarble(w)
        if w and o.get("from") is not None: words.append({"word":w,"start":o["from"]/1000.0,"end":o["to"]/1000.0})
    wj=os.path.join(tmp,base+".words.json"); json.dump(words,open(wj,"w"))
    ass=os.path.join(tmp,base+".ass")
    # Captions were 104px/3-words with a 9px outline — a wall of text that read as antiquated.
    # 78px, 2 words, lighter outline = TikTok-native: legible, but the footage is the subject.
    subprocess.run(["python3",J2A,"--json",wj,"--out",ass,"--font","Anton","--fontsize","78",
        "--words-per-cap","2","--outline","6","--shadow","0","--margin-v","560",
        "--active","#FFD93D","--inactive","#FFFFFF"],capture_output=True)
    # burn captions + crisp app; cover the iOS status bar with a dark strip and place the DebateTV
    # wordmark LOWERED (~y95) so IG's in-app top header doesn't clip it. keep original audio.
    # dark top bar (covers status bar) + "DebateTV" drawn as TEXT (png overlay kept clipping) — fully inside
    # Brand bar is now the real LOGO LOCKUP (badge + wordmark, ~620px wide) pre-rendered at
    # exactly 1080x175 and overlaid once — the old inline drawtext wordmark was small, and an
    # inline png overlay kept clipping. It still covers the iOS status bar.
    fc=(f"[0:v]{fitwide('d',CRISP)},ass={ass}:fontsdir={FONTS}[capped];"
        f"[capped][1:v]overlay=0:0[o]")
    r=subprocess.run(["ffmpeg","-y","-i",debate,"-i",BRANDLOCKUP,"-filter_complex",fc,
        "-map","[o]","-map","0:a?","-c:v","libx264","-preset","medium","-crf","19",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",out],capture_output=True,text=True)
    if r.returncode!=0: raise RuntimeError("caption failed: "+r.stderr[-800:])
    return out

def append_verdict(captioned, tmp="/tmp/ugc2_cap"):
    """Concat the generic VICTORY/verdict card (the AI payoff + 'full debate on IG') after the
    captioned debate clip. Verdict card is silent -> add a silent track so concat keeps audio."""
    if not os.path.exists(VERDICT_CARD): return captioned
    base=os.path.splitext(os.path.basename(captioned))[0]
    out=os.path.join(CAPCACHE, base+".verdict.mp4")
    if os.path.exists(out) and os.path.getmtime(out)>os.path.getmtime(captioned): return out
    fc=(f"[0:v]scale=1080:1920,fps=30,setsar=1[a0];[1:v]scale=1080:1920,fps=30,setsar=1[a1];"
        f"[0:a]aresample=48000[ca0];[1:a]aresample=48000[ca1];"
        f"[a0][ca0][a1][ca1]concat=n=2:v=1:a=1[v][a]")
    r=subprocess.run(["ffmpeg","-y","-i",captioned,"-i",VERDICT_CARD,
        "-filter_complex",fc,"-map","[v]","-map","[a]","-c:v","libx264","-preset","medium",
        "-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",out],capture_output=True,text=True)
    if r.returncode!=0: raise RuntimeError("append_verdict failed: "+r.stderr[-800:])
    return out

def hook_card(text, dst):
    page=f"""<body style='margin:0'><div style="display:flex;align-items:flex-start;justify-content:center;height:100vh;padding:235px 60px 0;box-sizing:border-box">
    <div style="color:#fff;font-family:-apple-system,'Helvetica Neue',Helvetica,Arial,sans-serif;font-weight:700;
    font-size:64px;line-height:1.12;text-align:center;letter-spacing:-0.5px;max-width:960px;
    text-shadow:0 2px 14px rgba(0,0,0,.55),0 1px 3px rgba(0,0,0,.7)">{html.escape(text)}</div></div></body>"""
    hp=dst+".html"; open(hp,"w").write(page)
    subprocess.run([CHROME,"--headless","--disable-gpu","--hide-scrollbars",f"--screenshot={dst}",
        "--window-size=1080,1920","--default-background-color=00000000",f"file://{hp}"],capture_output=True)
    os.remove(hp)

MUSICDIR=os.path.join(ASSETS,"music")
def render(reaction, hook, debate_raw, out, react_secs=2.5, sfx=None, bed=None, tmp="/tmp/ugc2_work"):
    cleared(reaction, "make_ugc_v2")
    os.makedirs(tmp, exist_ok=True)
    debate=append_verdict(caption_and_brand(debate_raw))   # captioned+branded debate, then the VICTORY verdict card
    card=os.path.join(tmp,"hook.png"); hook_card(hook, card)
    ddur=_dur(debate); total=react_secs+ddur; rms=int(react_secs*1000)
    bedp=os.path.join(MUSICDIR,bed) if bed and os.path.exists(os.path.join(MUSICDIR,bed)) else None  # None = clean (data winner)
    sfxp=os.path.join(SFXDIR,sfx) if sfx and os.path.exists(os.path.join(SFXDIR,sfx)) else None
    ins=["-t",str(react_secs),"-i",reaction,"-i",card,"-i",debate]
    idx_bed=idx_sfx=None; n=3
    if bedp: ins+=["-stream_loop","-1","-i",bedp]; idx_bed=n; n+=1
    if sfxp: ins+=["-i",sfxp]; idx_sfx=n; n+=1
    # video: reaction+hook -> concat debate (which already ends on the VICTORY verdict card + IG CTA)
    fc=(f"[0:v]{fitwide('r')}[rv];[rv][1:v]overlay=0:0[r];"
        f"[2:v]fps=30,setsar=1[d];[r][d]concat=n=2:v=1:a=0[v]")
    # debate speech: FULL polish chain (muddy FaceTime/screen-rec -> clean) — restored from debatetv-ugc:
    # highpass -> FFT denoise -> de-ess -> presence EQ (+3@3k, -2@180) -> compressor -> loudnorm. kept DOMINANT.
    fc+=(f";[2:a]aresample=48000,highpass=f=85,afftdn=nr=12,"
         f"deesser,equalizer=f=3000:t=q:w=1.2:g=3,equalizer=f=180:t=q:w=1:g=-2,"
         f"acompressor=threshold=-18dB:ratio=3:attack=5:release=120,loudnorm=I=-14:TP=-1.5:LRA=11,"
         f"adelay={rms}|{rms},apad=whole_dur={total}[sp]")
    if bedp:
        # split speech only when there's a bed to duck (dangling split output crashes ffmpeg otherwise)
        fc+=";[sp]asplit=2[spmix][spkey]"
        mixes=["[spmix]"]
        # viral bed: SIDECHAIN-ducked by the speech -> bed swells on hook + verdict gaps, drops under debate
        fc+=(f";[{idx_bed}:a]aresample=48000,atrim=0:{total},asetpts=PTS-STARTPTS,volume=0.85[bedraw];"
             f"[bedraw][spkey]sidechaincompress=threshold=0.02:ratio=14:attack=5:release=380,volume=0.55[bedf]")
        mixes.append("[bedf]")
    else:
        mixes=["[sp]"]
    if sfxp:
        # viral SFX punch right on the hook->debate CUT
        fc+=(f";[{idx_sfx}:a]aresample=48000,adelay={rms}|{rms},volume=0.7[sfx]"); mixes.append("[sfx]")
    fc+=f";{''.join(mixes)}amix=inputs={len(mixes)}:dropout_transition=0:normalize=0,alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5[a]"
    cmd=["ffmpeg","-y"]+ins+["-filter_complex",fc,"-map","[v]","-map","[a]","-t",str(total),
         "-r","30","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","160k","-movflags","+faststart",out]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode!=0: return False, r.stderr[-1600:]
    return True, None

def main(manifest_path, outdir):
    man=json.load(open(manifest_path)); os.makedirs(outdir, exist_ok=True); ok=0
    for m in man: cleared(m["reaction"], f"make_ugc_v2 reel {m['id']}")     # all of them, before the first render
    for m in man:
        i=m["id"]; out=os.path.join(outdir, f"{i:02d}_{m.get('slug','ugc')}.mp4")
        good,err=render(m["reaction"], m["hook"], m["debate"], out, m.get("react_secs",2.5), m.get("sfx"), m.get("bed"))
        if good:
            ok+=1; open(os.path.join(outdir, f"{i:02d}_{m.get('slug','ugc')}.txt"),"w").write(m.get("caption","")+"\n")
            print(f"[{i:02d}] OK -> {os.path.basename(out)}")
        else: print(f"[{i:02d}] FAIL: {err}")
    print(f"DONE {ok}/{len(man)}")

if __name__=="__main__":
    main(sys.argv[1], sys.argv[2])
