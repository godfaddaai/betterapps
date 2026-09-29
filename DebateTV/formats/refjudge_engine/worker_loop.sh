#!/bin/zsh
# Keeps rendering new jobs until the brains finish and the queue is empty. Own TMPDIR per worker.
# Stops rendering when free disk drops under FLOOR GB (default 4). 9/28: Reagan asked for a 15 GB floor, but a parallel iOS
# test session held the Mac at 5-10 GB all afternoon; each render nets ~15 MB, so the floor guards HyperFrames (refuses <1 GB).
cd "${0:A:h}"
export TMPDIR=$(mktemp -d /tmp/refw.XXXX)/
while true; do
  free=$(df -g ~ | awk 'NR==2{print $4}')
  if (( free < ${FLOOR:-4} )); then echo "disk ${free}G < ${FLOOR:-4}, pausing"; sleep 60; continue; fi
  n=$(python3 -c "
import pathlib,os
suf=('-'+os.environ['REF_VARIANT']) if os.environ.get('REF_VARIANT') else ''
print(sum(1 for j in pathlib.Path('jobs').iterdir() if (j/'job.json').exists() and not (pathlib.Path('out')/(j.name+suf)).exists()))")
  if (( n == 0 )); then [[ -f logs/brains.done ]] && break; sleep 30; continue; fi
  python3 render.py --queue
done
rm -rf "$TMPDIR"
