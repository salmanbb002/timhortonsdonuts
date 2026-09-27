#!/bin/sh
# Guarded live check (replaces curl_check.sh). The first path is a single probe; nothing else runs unless it passes.
#   - max 15 requests per run, 2s apart, no retries, redirects not followed
#   - any block signature (403/429, x-vercel-mitigated, block/checkpoint page) stops the run and starts a cooldown:
#     15 min, doubling on each consecutive block; every run refuses to start while a cooldown is active
#   - every request is appended to .live/requests.log (time, host, path, status, result) for exact audits
# Usage: scripts/live.sh https://host [path[=expected_status] ...]     default path "/", default status 200
#   e.g. scripts/live.sh https://timhortonsdonuts.com / /latte.html=308 /seo-research/x.csv=404
BASE=${1:?usage: scripts/live.sh https://host [path[=status] ...]}; shift
[ $# -eq 0 ] && set -- /
[ $# -gt 15 ] && { echo "live: $# paths requested, max 15 per run"; exit 2; }
DIR="$(cd "$(dirname "$0")/.." && pwd)/.live"; mkdir -p "$DIR"
LOG="$DIR/requests.log"; STAMP="$DIR/cooldown"; COOL=900; GAP=2
HOST=${BASE#*://}; HOST=${HOST%%/*}
NOW=$(date +%s)

if [ -f "$STAMP" ]; then
  read -r H T N < "$STAMP"
  WAIT=$COOL; i=1; while [ "$i" -lt "$N" ]; do WAIT=$((WAIT * 2)); i=$((i + 1)); done
  if [ "$H" = "$HOST" ] && [ $((NOW - T)) -lt "$WAIT" ]; then
    echo "live: cooldown for $HOST - $(( (WAIT - (NOW - T) + 59) / 60 )) min left (block #$N). Not sending anything."
    exit 3
  fi
fi

BODY=$(mktemp); HDRS=$(mktemp); trap 'rm -f "$BODY" "$HDRS"' EXIT
first=1; pass=0
for arg in "$@"; do
  path=${arg%%=*}; want=200; case "$arg" in *=*) want=${arg#*=} ;; esac
  [ $first -eq 0 ] && sleep $GAP
  code=$(curl -s --max-time 20 -o "$BODY" -D "$HDRS" -w '%{http_code}' "$BASE$path")
  if [ "$code" = 403 ] || [ "$code" = 429 ] || grep -qi '^x-vercel-mitigated' "$HDRS" \
     || grep -q 'Security Checkpoint\|This request was blocked' "$BODY"; then
    result=BLOCKED
  elif [ "$code" = "$want" ]; then result=ok; else result="unexpected(want $want)"; fi
  echo "$(date -u +%FT%TZ) $HOST $path $code $result $([ $first -eq 1 ] && echo probe)" >> "$LOG"
  echo "$path -> $code $result"
  if [ "$result" = BLOCKED ]; then
    N=1; [ -f "$STAMP" ] && { read -r H T N < "$STAMP"; [ "$H" = "$HOST" ] && N=$((N + 1)) || N=1; }
    echo "$HOST $(date +%s) $N" > "$STAMP"
    echo "live: BLOCKED - stopped after $pass passing request(s); cooldown started for $HOST"
    exit 1
  fi
  [ "$result" = ok ] && pass=$((pass + 1))
  [ $first -eq 1 ] && [ "$result" != ok ] && { echo "live: probe failed - nothing else sent"; exit 1; }
  first=0
done
rm -f "$STAMP"
echo "live: $pass/$# as expected"
[ "$pass" -eq $# ]
