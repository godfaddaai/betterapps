#!/bin/zsh
# Codex hit its usage limit 9/28 2:40 PM (resets 7:15 PM): pick more clashes from the remaining Film Room sources after that.
cd "${0:A:h}"
rm -f logs/brains.done
while [[ $(date +%H%M) -lt 1920 ]]; do sleep 60; done
while read -r url; do
  [[ -z "$url" ]] && continue
  python3 brain.py "$url" --max 6 >> logs/brain2_${url##*v=}.log 2>&1
  sleep 30
done < sources_0928c.txt
touch logs/brains.done
