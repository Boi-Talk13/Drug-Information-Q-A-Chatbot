#!/bin/bash
# Live view of the MedCite chat database — one table, refreshes in place.
# The clock ticks every second; the database is re-queried every INTERVAL secs.
# Usage:  bash watch-db.sh        (Ctrl+C to stop)
DB="${DB:-medcite}"
INTERVAL="${INTERVAL:-10}"
# Hosted databases (e.g. Neon) run in UTC; show times in India time.
export PGTZ="${PGTZ:-Asia/Kolkata}"

# Short, tidy table — newest first. The Date column shows the real calendar
# date for every row ("12 Sep 2026"), not relative words like Today/Yesterday,
# so rows stay unambiguous and keep meaning when you read them back later.
fetch() {
  psql -d "$DB" -P pager=off -c \
    "SELECT to_char(to_timestamp(ts), 'DD Mon YYYY') AS \"Date\",
            to_char(to_timestamp(ts), 'HH24:MI:SS') AS \"Time\",
            user_id AS \"User\",
            LEFT(question, 32) AS \"Question\",
            LEFT(answer, 55)   AS \"Answer\"
     FROM chat_history
     ORDER BY ts DESC
     LIMIT 20;"
}

trap 'echo; echo "stopped."; exit 0' INT

while true; do
  DATA="$(fetch)"
  DB_TIME="$(date '+%H:%M:%S')"
  # Tick the clock every second for INTERVAL seconds, then re-fetch.
  for ((i = INTERVAL; i > 0; i--)); do
    clear
    echo "MedCite live database — chat_history   (Ctrl+C to stop)"
    echo "DB last fetched: $DB_TIME    Now: $(date '+%H:%M:%S')    next refresh in ${i}s"
    echo
    echo "$DATA"
    sleep 1
  done
done
