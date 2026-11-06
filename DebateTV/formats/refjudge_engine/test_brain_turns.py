"""Tests for brain.py's caption turn marks (11/6, asks a366/a367): YouTube VTT words carry ">>" as "&gt;&gt;", and the
job's speaker tags move onto those marks so each side's line is whole sentences (beatedit's open needs one).
Run: python3 test_brain_turns.py   (no network, no models: the two functions are read out of brain.py alone)"""
import html, pathlib, re, tempfile

SRC = (pathlib.Path(__file__).parent / "brain.py").read_text()
NS = {"re": re, "html": html}
for name in ("turn_tags", "vtt_words"):
    i = SRC.index(f"def {name}(")
    exec(SRC[i:SRC.index("\ndef ", i + 5)], NS, NS)


def test_vtt_unescapes_turn_mark():
    p = pathlib.Path(tempfile.mktemp(suffix=".vtt"))
    p.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi<00:00:01.500><c> &gt;&gt; No</c><00:00:01.800><c> way</c>\n")
    assert NS["vtt_words"](p) == [(1.0, "Hi"), (1.5, ">> No"), (1.8, "way")]


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
