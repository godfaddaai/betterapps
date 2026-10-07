#!/usr/bin/env python3
"""Write pain_hooks.json's pain_hook + viewer into each job.json (the xpain arm reads them). Prints the keys."""
import json, pathlib
HERE = pathlib.Path(__file__).parent
hooks = json.loads((HERE / "pain_hooks.json").read_text())["hooks"]
for key, h in hooks.items():
    p = HERE / "jobs" / key / "job.json"
    job = json.loads(p.read_text())
    assert "-" not in h["pain_hook"].replace("*", "").replace("'", ""), (key, "no dashes on screen")
    job.update(pain_hook=h["pain_hook"], viewer=h["viewer"])
    p.write_text(json.dumps(job, indent=1))
print(" ".join(hooks))
