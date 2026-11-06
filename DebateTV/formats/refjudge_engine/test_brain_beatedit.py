"""a391: the cheap pre-skips brain.py runs before filing an edit job beatedit would refuse. python3 test_brain_beatedit.py"""
import json, os, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import brain as B

V = lambda a, b: {"averageScores": {"participantA": a, "participantB": b}}
ex = lambda a, b: {"a_name": a, "b_name": b}

# the four refused 11/6, then the one beatedit kept (KUh4chttVqc_436)
U14 = ("1 Atheist vs 10 Christians: Can Adam Green Defend His Beliefs? 📱", "Digital Social Hour Podcast by Sean Kelly")
KOC = ("1 Christian confronts 20 Atheists Eye to Eye", "Cruise")
TJM = ("1 YouTuber vs 9-5 Workers Debate : What is Harder?", "King Kenny")
KUH = ("🇺🇸😅🔥NYC STREET DEBATE‼️Christian REGRETS Debating These 2 Muslims ft. @CentralDawahOfficial", "One Message Foundation")
DHP = ("Andrew Wilson gets DESTROYED by 20 yr old Objectivist Philosopher @ProphetDivinityy", "Eduardo")

assert B.crowd_wins(ex("Adam Green", "Christian"), V(47, 52), *U14)            # the crowd (Christian) won
assert not B.crowd_wins(ex("Adam Green", "Christian"), V(60, 52), *U14)        # the one (Adam Green) won
assert not B.crowd_wins(ex("Atheist", "Christian"), V(43, 55), *KOC)           # the one (the Christian) won
assert B.split_screen(*KOC)                                                     # ... but it is a split screen call
assert not B.crowd_wins(ex("Postman", "King Kenny"), V(33, 71), *TJM)          # the one won: left to beatedit spec
assert not B.split_screen(*TJM)
assert B.one_side(*KUH) is None and not B.crowd_wins(ex("Muslim", "Christian"), V(42, 69), *KUH)
assert not B.split_screen(*KUH) and not B.split_screen(*DHP) and B.one_side(*DHP) is None
assert B.split_screen("Destiny vs caller on stream", "") and B.split_screen("Zoom debate", "")
assert not B.split_screen("Surrounded: 1 Liberal vs 25 Conservatives", "Jubilee")
assert B.one_side("Surrounded: 1 Liberal vs 25 Conservatives", "Jubilee") is not None
assert not B.crowd_wins(ex("Liberal", "Conservative"), V(1, 1), "1 Liberal vs 25 Conservatives", "")   # a tie: no call

# the gate log: refused and crowd block a rerun, a host failure does not
with tempfile.TemporaryDirectory() as t:
    B.GATE_LOG = pathlib.Path(t, "g.jsonl")
    B.note_gate("a_1", "refused", "no line"); B.note_gate("b_2", "host", "timeout"); B.note_gate("c_3", "crowd")
    assert B.gated() == {"a_1": "refused", "b_2": "host", "c_3": "crowd"}

# beatedit_spec with no beatedit: host, nothing staged
B.BEATEDIT = pathlib.Path("/nonexistent/beatedit.py")
assert B.beatedit_spec("x_1", {}, "/dev/null")[0] == "host"
print("ok")
