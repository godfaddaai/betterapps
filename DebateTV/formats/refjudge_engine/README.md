# REF-judge engine

Any full debate video -> post-ready clips with the production REF's real verdict.

    ./run.sh sources.txt [clips-per-video=12] [workers=2]

1. `brain.py <url>` (Mac: needs YouTube + Codex login): YouTube per-word captions -> Codex (GPT-5.5, structured output)
   picks self-contained clashes -> each is judged by debatetvbackend `/judge` (no roomId = no DB writes) ->
   `jobs/<videoid>_<sec>/{job.json, src.mp4}`. `ledger.json` stops the same exchange being made twice.
2. `render.py --queue` (anywhere; Dockerfile): per camera shot and per speaker turn, YuNet faces + mouth motion find
   the active speaker and the crop keeps that face whole (split screens never leak the other panel; other faces fully
   in or fully out; wide shots stay wide). Layout is built once for IG Reels + TikTok + Shorts: footage in a
   1080x750 window at y 440, hook under the apps' top bar, captions at y 1266-1442 left of the button rail, bottom
   440 px empty. Master = H.264 1080x1920 30 fps ~10 Mbps, -14 LUFS / -1.5 dBTP. Every render must pass
   `~/DebateTV2-content-queue/tools/content_queue/reel_qa.py` (sampled frames: no cut or covered face, nothing under
   platform UI) or it is marked REJECTED and never filed. Crop plans cache in `jobs/<key>/crops.json`.
   Output `out/<key>/<key>.mp4 + .layout.json + qa.json + post.txt`. Workers claim jobs with an atomic mkdir.
   `./rerender.sh [keys first]` re-renders every job one at a time (old outputs to `out_archive/<stamp>/`).

Throughput (this Mac, 1 worker): ~100 s render per 40 s clip -> ~35/hour. Brain: ~4 min per 90-min video.
Supply: one 90-min Jubilee episode -> 3-12 clips. Scale = more source URLs + more workers.
Not verified: the Docker image has never been built (no Docker on this Mac).
