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

# j1217: the open is a line of REF's side; under 3 s alone anywhere means no open (b75GNVh4ABo_865: bursts only)
cap = lambda *runs: [{"t": t, "w": "w", "s": s} for s, a, b in runs for t in [a + 0.4 * k for k in range(int((b - a) / 0.4) + 1)]]
burst = cap(("A", 0, 1.2), ("B", 1.5, 6), ("A", 6.3, 8.1), ("B", 8.4, 20))
assert B.open_run(burst, "A") < B.OPEN_RUN <= B.open_run(burst, "B")
assert B.open_run(cap(("A", 0, 2.0)), "A") >= B.OPEN_RUN                     # 2 s of word starts + the last word
assert B.open_run([{"t": 0, "s": "A"}, {"t": 1, "s": "A"}, {"t": 2.3, "s": "A"}, {"t": 2.9, "s": "B"}], "A") >= B.OPEN_RUN
assert B.focus_of(V(60, 45), burst) == "A" and B.focus_of(V(36, 62), burst) == "B"
assert B.focus_of(V(50, 50), burst) == "B"                                     # a tie: the side that talks more
assert B.same_person("Andrew Wilson", "Wilson") and not B.same_person("Nick Fuentes", "Dean Withers")
assert not B.same_person("Man 1", "Man 2") and not B.same_person("", "") and B.same_person("Christian", "christian")
assert B.NO_OPEN in "the source's own text is on screen (after 1 rounds of picking around it: no line of the edited debater fits the open)"

# the gate log: refused and crowd block a rerun, a host failure does not
with tempfile.TemporaryDirectory() as t:
    B.GATE_LOG = pathlib.Path(t, "g.jsonl")
    B.note_gate("a_1", "refused", "no line"); B.note_gate("b_2", "host", "timeout"); B.note_gate("c_3", "crowd")
    assert B.gated() == {"a_1": "refused", "b_2": "host", "c_3": "crowd"}

# j1362: a pick only short on beats is filed for beatedit_feed's pair retry (a full name, N >= 4)
W = "only 11 distinct moments of the edited debater fit a beat, 15 needed"
assert B.short_lend(W, "Daniel Haqiqatjou") and B.short_lend(W.replace("11", "4"), "Andrew Wilson")
assert not B.short_lend(W.replace("11", "3"), "Andrew Wilson")              # 3 moments: 4 partners, over the feed's 3
assert not B.short_lend(W, "a panelist") and not B.short_lend(W, "Wilson")   # a role, a single word: no partner pool
assert not B.short_lend("no line of the edited debater fits the open", "Andrew Wilson")
assert not B.short_lend("the source's own text is on screen wherever this debater talks", "Andrew Wilson")

# beatedit_spec with no beatedit: host, nothing staged
B.BEATEDIT = pathlib.Path("/nonexistent/beatedit.py")
assert B.beatedit_spec("x_1", {}, "/dev/null")[0] == "host"
print("ok")
