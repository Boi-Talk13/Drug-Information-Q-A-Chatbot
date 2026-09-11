#!/bin/bash
# Live view of the MedCite chat database — one table, refreshes in place.
# The clock ticks every second; the database is re-queried every INTERVAL secs.
# Usage:  bash watch-db.sh        (Ctrl+C to stop)
DB="${DB:-medcite}"
INTERVAL="${INTERVAL:-10}"

# Short, tidy table — grouped by day (Today / Yesterday / date) then newest first.
fetch() {
  psql -d "$DB" -P pager=off -c \
    "SELECT CASE
              WHEN to_timestamp(ts)::date = current_date THEN 'Today'
              WHEN to_timestamp(ts)::date = current_date - 1 THEN 'Yesterday'
              ELSE to_char(to_timestamp(ts), 'DD Mon')
            END AS \"Day\",
            to_char(to_timestamp(ts), 'HH24:MI') AS \"Time\",
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
