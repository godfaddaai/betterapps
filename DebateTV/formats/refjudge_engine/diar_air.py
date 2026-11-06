"""Runs on the render farm Mac (~/render/diar_air.py, venv ~/render/diar-venv): one video's audio -> speaker turns JSON
on stdout. Pushed and called by diarize.py (11/6, j812). Audio is fetched by the farm's own yt-dlp, decoded in memory
(PyAV), and deleted; nothing stays on that disk."""
import json, os, pathlib, subprocess, sys, tempfile
import av, numpy as np, sherpa_onnx

vid, thr = sys.argv[1], float(sys.argv[2])
home = pathlib.Path.home() / "render"
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, PYTHONPATH=str(home / "tools" / "ytdlp"))
    subprocess.run([str(home / "py" / "bin" / "python"), "-m", "yt_dlp", "--no-warnings", "-q", "-f",
                    "bestaudio[ext=m4a]/bestaudio", "-o", f"{tmp}/a.%(ext)s", f"https://www.youtube.com/watch?v={vid}"],
                   check=True, timeout=900, env=env)
    src = next(pathlib.Path(tmp).glob("a.*"))
    rs = av.AudioResampler(format="flt", layout="mono", rate=16000)
    chunks = []
    with av.open(str(src)) as f:
        for fr in f.decode(audio=0):
            for o in rs.resample(fr):
                chunks.append(o.to_ndarray().reshape(-1))
        for o in rs.resample(None):
            chunks.append(o.to_ndarray().reshape(-1))
audio = np.concatenate(chunks).astype(np.float32)
cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
    segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(home / "diar-models" / "seg.onnx")),
        num_threads=6),
    embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(home / "diar-models" / "wespeaker_en.onnx"),
                                                          num_threads=6),
    clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=thr),
    min_duration_on=0.3, min_duration_off=0.4)
r = sherpa_onnx.OfflineSpeakerDiarization(cfg).process(audio).sort_by_start_time()
print(json.dumps([[round(s.start, 2), round(s.end, 2), int(s.speaker)] for s in r]))
