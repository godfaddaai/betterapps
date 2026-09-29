#!/bin/zsh
# Re-render every job with the current render.py, ONE AT A TIME (this Mac's RAM is the ceiling), base hook then the
# xwho hook, keys listed first go first. Old outputs move to out_archive/<stamp>/ so the queue claim logic sees them
# as missing. Each finished render is staged into the outbox right away (clips.py), so the nightly queue can use it.
#   ./rerender.sh [key ...]      # no keys = every job
cd "${0:A:h}"
export PATH="$HOME/.nvm/versions/node/v22.23.1/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export TMPDIR=$(mktemp -d /tmp/refrr.XXXX)/
PY=/opt/homebrew/bin/python3
STAMP=$(date +%Y%m%d-%H%M)
first=("$@")
all=(${(f)"$(ls jobs)"})
order=($first ${all:|first})
mkdir -p out_archive/$STAMP logs
for variant in "" xwho; do
  for key in $order; do
    [[ -f jobs/$key/job.json ]] || continue
    name=$key${variant:+-$variant}
    # already rendered (or rejected) since the platform reframe (logs/platform-reframe.stamp): a restart resumes
    [[ out/$name/qa.json -nt logs/platform-reframe.stamp || ( -f out/$name/REJECTED.txt && out/$name/REJECTED.txt -nt logs/platform-reframe.stamp ) ]] && continue
    [[ -d out/$name ]] && mv out/$name out_archive/$STAMP/$name
    free=$(df -g ~ | awk 'NR==2{print $4}')
    while (( free < 4 )); do echo "disk ${free}G, waiting"; sleep 120; free=$(df -g ~ | awk 'NR==2{print $4}'); done
    REF_VARIANT=$variant $PY render.py jobs/$key
    $PY -c "import sys; sys.path.insert(0, '$HOME/DebateTV2-content-queue/tools/content_queue'); import clips; print('staged', clips.stage())"
    for c in ${TMPDIR}hyperframes-extract-cache-*(N); do rm -rf $c; done
  done
done
rm -rf "$TMPDIR"
echo "rerender done: $(ls out/*/*.mp4 2>/dev/null | grep -v qa-fail | wc -l) rendered, $(ls out/*/REJECTED.txt 2>/dev/null | wc -l) rejected"
