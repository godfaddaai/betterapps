"""python3 test_voices.py: smooth_voices keeps diarizer tags off the middle of a sentence (j1088)."""
import brain


def w(*pairs):
    return [(float(t), x) for t, x in pairs]


def test_blip_absorbed():
    words = w((0, "I"), (0.3, "think"), (0.6, "rights"), (0.9, "are"), (1.2, "real."), (1.5, "They"), (1.8, "are."))
    raw = ["S1", "S1", "S2", "S1", "S1", "S1", "S1"]
    assert brain.smooth_voices(words, raw) == ["S1"] * 7


def test_change_snaps_to_sentence_end():
    # the diarizer starts S2 two words early, inside S1's sentence; the change moves to the sentence end
    words = w((0, "Rights"), (0.4, "come"), (0.8, "from"), (1.2, "God."), (1.6, "No"), (2.0, "they"), (2.4, "come"),
              (2.8, "from"), (3.2, "people."))
    raw = ["S1", "S1", "S2", "S2", "S2", "S2", "S2", "S2", "S2"]
    assert brain.smooth_voices(words, raw) == ["S1"] * 4 + ["S2"] * 5


def test_turn_mark_wins():
    words = w((0, "You"), (0.4, "said"), (0.8, "it."), (1.2, ">>"), (1.3, "I"), (1.6, "never"), (2.0, "did."), (2.4, "Really"))
    raw = ["S1", "S1", "S1", "S1", "S1", "S2", "S2", "S2"]
    assert brain.smooth_voices(words, raw) == ["S1"] * 3 + ["S2"] * 5


def test_real_turns_kept():
    words = w(*[(i * 0.4, f"w{i}.") for i in range(12)])
    raw = ["S1"] * 4 + ["S2"] * 4 + ["S1"] * 4
    assert brain.smooth_voices(words, raw) == raw


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f(); print("ok", name)
