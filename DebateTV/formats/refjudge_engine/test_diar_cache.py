"""The diarizer never crashes a brain over its cache (11/6, j1154): with the SSD unplugged, mkdir under /Volumes
raised PermissionError and the labeled pass died. Now the cache falls back to ~/.render-farm/diar-cache, and a cache
dir that still can't be made means plain captions ([])."""
import importlib, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(monkeypatch, tmp_path, diar_home):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DIAR_HOME", str(diar_home))
    import diarize
    return importlib.reload(diarize)


def test_ssd_unplugged_falls_back_to_mac(monkeypatch, tmp_path):
    d = _load(monkeypatch, tmp_path, "/Volumes/NotPluggedIn_j1154/ARENA-media")
    assert d.CACHE == tmp_path / ".render-farm" / "diar-cache"
    d._on_air = lambda vid, out: out.write_text(json.dumps([[0, 1, 7], [1, 2, 3], [2, 3, 7]]))
    assert d.turns("vid_ssd_off") == [(0, 1, "S1"), (1, 2, "S2"), (2, 3, "S1")]
    assert (d.CACHE / "vid_ssd_off.json").exists()


def test_ssd_present_keeps_ssd_cache(monkeypatch, tmp_path):
    ssd = tmp_path / "ssd" / "ARENA-media"
    ssd.mkdir(parents=True)
    d = _load(monkeypatch, tmp_path, ssd)
    assert d.CACHE == ssd / "diar-cache"


def test_cache_dir_unmakeable_is_plain_captions(monkeypatch, tmp_path):
    d = _load(monkeypatch, tmp_path, "/Volumes/NotPluggedIn_j1154/ARENA-media")
    d.CACHE = pathlib.Path("/Volumes/NotPluggedIn_j1154/diar-cache")   # root-only parent: mkdir raises
    called = []
    d._on_air = lambda vid, out: called.append(vid)
    assert d.turns("vid_no_dir") == []
    assert not called
