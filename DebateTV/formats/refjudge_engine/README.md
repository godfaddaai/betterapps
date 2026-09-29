# REF-judge engine

Any full debate video -> post-ready clips with the production REF's real verdict.

    ./run.sh sources.txt [clips-per-video=12] [workers=2]

1. `brain.py <url>` (Mac: needs YouTube + Codex login): YouTube per-word captions -> Codex (GPT-5.5, structured output)
   picks self-contained clashes -> each is judged by debatetvbackend `/judge` (no roomId = no DB writes) ->
   `jobs/<videoid>_<sec>/{job.json, src.mp4}`. `ledger.json` stops the same exchange being made twice.
2. `render.py --queue` (anywhere; Dockerfile): per camera shot and per speaker turn, YuNet face tracks + mouth motion
   pick the active speaker, and the crop holds that face whole and centred across the turn (split screens stay inside
   the speaker's panel; other faces are kept fully in or fully out; wide shots stay wide). Layout is built once for
   IG Reels + TikTok + Shorts: footage in a 1080x750 window at y 440, hook in y 230-430, captions at y 1266-1442 and
   x 60-900, nothing below y 1480 or on the right button rail. Master: 1080x1920 H.264 ~10 Mbps 30 fps, -14 LUFS /
   -1.5 dBTP. Then the shared gate `~/DebateTV2-content-queue/tools/content_queue/reel_qa.py` samples frames: a cut or
   covered face, text or face under platform UI, or a spec miss marks the job REJECTED (`<key>.qa-fail.mp4` kept).
   OCR still rejects clips with the source's own graphics in view. Output `out/<key>/<key>.mp4 + post.txt + qa.json`.
   Workers claim jobs with an atomic mkdir. `./rerender.sh [keys first]` redoes every job one at a time.
   (Before 9/29 the crop was a fixed 608 px column clamped to x 330-1450: on Jubilee's split screens it cut Jordan
   Peterson's face in half, and captions sat under IG's caption block.)

Throughput (this Mac, 1 worker): ~100 s render per 40 s clip -> ~35/hour. Brain: ~4 min per 90-min video.
Supply: one 90-min Jubilee episode -> 3-12 clips. Scale = more source URLs + more workers.
Not verified: the Docker image has never been built (no Docker on this Mac).
