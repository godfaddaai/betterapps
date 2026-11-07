import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain


def ex():
    return {"start": 10.0, "end": 30.0, "kill_phrase": "that is not freedom",
            "lines": [{"speaker": "A", "start": 10.0, "text": "you want the state to decide for everyone"},
                      {"speaker": "B", "start": 13.0, "text": "no I want people to choose for themselves"},
                      {"speaker": "A", "start": 17.0, "text": "choosing to harm others that is not freedom"},
                      {"speaker": "B", "start": 21.0, "text": "okay but who decides what harm is"}]}


def test_cut_ends_on_the_kill_line():
    cut = brain.end_on_kill(ex())
    assert [l["speaker"] for l in cut["lines"]] == ["A", "B", "A"] and cut["end"] == 21.0


def test_no_cut_when_phrase_absent_or_last():
    e = ex(); e["kill_phrase"] = "who decides what harm is"
    assert brain.end_on_kill(e) is None
    e["kill_phrase"] = "never said"
    assert brain.end_on_kill(e) is None
