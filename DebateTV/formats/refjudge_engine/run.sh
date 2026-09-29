#!/bin/zsh
# One command: every URL in a file -> judged jobs -> rendered posts.
#   ./run.sh sources.txt [clips-per-video] [workers]
# sources.txt = one YouTube URL per line (full debates: a 90-min Jubilee episode gives ~6-12 clips).
cd "${0:A:h}"
MAX=${2:-12}; WORKERS=${3:-2}
while read -r url; do
  [[ -z "$url" || "$url" == \#* ]] && continue
  python3 brain.py "$url" --max "$MAX" || echo "brain failed: $url"
done < "$1"
for i in $(seq "$WORKERS"); do python3 render.py --queue & done
wait
ls -d out/*/*.mp4 2>/dev/null | wc -l | xargs echo "rendered:"
ls out/*/REJECTED.txt 2>/dev/null | wc -l | xargs echo "rejected:"
