"""Tests for brain.py's caption turn marks (11/6, asks a366/a367): YouTube VTT words carry ">>" as "&gt;&gt;", and the
job's speaker tags move onto those marks so each side's line is whole sentences (beatedit's open needs one).
Run: python3 test_brain_turns.py   (no network, no models: importing brain runs nothing, main sits under __main__)"""
import os, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import brain  # noqa: E402

NS = {"turn_tags": brain.turn_tags, "vtt_words": brain.vtt_words}


def test_vtt_unescapes_turn_mark():
    with tempfile.NamedTemporaryFile("w", suffix=".vtt", delete=False) as f:
        f.write("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi<00:00:01.500><c> &gt;&gt; No</c><00:00:01.800><c> way</c>\n")
    try:
        assert NS["vtt_words"](pathlib.Path(f.name)) == [(1.0, "Hi"), (1.5, ">> No"), (1.8, "way")]
    finally:
        os.unlink(f.name)


def test_change_moves_onto_mark_and_mark_leaves_text():
    cap = [{"t": 1, "w": "Why?", "s": "A"}, {"t": 1.5, "w": ">> Because", "s": "A"}, {"t": 1.8, "w": "no", "s": "B"},
           {"t": 4, "w": "Ok.", "s": "A"}, {"t": 6, "w": "Yes", "s": "B"}]
    out = NS["turn_tags"](cap)
    assert [(c["w"], c["s"]) for c in out] == [("Why?", "A"), ("Because", "B"), ("no", "B"), ("Ok.", "A"), ("Yes", "B")]


def test_unmarked_change_keeps_its_place():
    # DhpfsOSNakY_723: "They did that through slavery. >> Yeah, but" - the B->A change at "They" has no mark and must
    # not take the next change's mark at "Yeah"
    cap = [{"t": 0, "w": "society.", "s": "B"}, {"t": 1.0, "w": "They", "s": "A"}, {"t": 1.3, "w": "slavery.", "s": "A"},
           {"t": 2.1, "w": "&gt;&gt; Yeah,", "s": "A"}, {"t": 2.2, "w": "but", "s": "B"}]
    out = NS["turn_tags"](cap)
    assert [(c["w"], c["s"]) for c in out] == [("society.", "B"), ("They", "A"), ("slavery.", "A"), ("Yeah,", "B"), ("but", "B")]


def test_empty_and_far_mark():
    assert NS["turn_tags"]([]) == []
    cap = [{"t": 0, "w": "a", "s": "A"}, {"t": 1, "w": "b", "s": "B"}, {"t": 9, "w": ">> c", "s": "B"}]
    assert [c["s"] for c in NS["turn_tags"](cap)] == ["A", "B", "B"]


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
