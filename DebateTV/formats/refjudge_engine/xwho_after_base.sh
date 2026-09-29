#!/bin/zsh
# Experiment arm: once every base job has a render, render the same clips with the open-loop hook (out/<key>-xwho).
cd "${0:A:h}"
while true; do
  n=$(python3 -c "import pathlib;print(sum(1 for j in pathlib.Path('jobs').iterdir() if (j/'job.json').exists() and not (pathlib.Path('out')/j.name).exists()))")
  (( n == 0 )) && break
  sleep 120
done
REF_VARIANT=xwho exec ./worker_loop.sh
