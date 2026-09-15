#!/bin/bash
# Browse and search the MedCite chat database.
#
#   bash db.sh                     overview: rows per day, users, medicines
#   bash db.sh days                how many questions on each day
#   bash db.sh day 2026-09-11      everything asked on one day
#   bash db.sh today               everything asked today
#   bash db.sh search pregnant     find a word in any question or answer
#   bash db.sh search preg 09-11   ...limited to one day
#   bash db.sh user user-104       one person's full history
#   bash db.sh drug linzess        every question about one medicine
#   bash db.sh refusals            questions the bot declined to answer
#   bash db.sh full 42             the complete row (untruncated) by id
#
# watch-db.sh is the live tail; this one is for looking things up.
DB="${DB:-medcite}"
# Hosted databases (e.g. Neon) run in UTC; show times in India time.
export PGTZ="${PGTZ:-Asia/Kolkata}"
q() { psql -d "$DB" -P pager=off -c "$1"; }

# Every listing shows the same columns, so output always looks the same.
COLS="id AS \"ID\",
      to_char(to_timestamp(ts),'DD Mon YYYY') AS \"Date\",
      to_char(to_timestamp(ts),'HH24:MI') AS \"Time\",
      user_id AS \"User\",
      COALESCE(drug,'-') AS \"Medicine\",
      LEFT(question,40) AS \"Question\",
      LEFT(answer,60) AS \"Answer\""

case "${1:-overview}" in
  overview|"")
    echo "── Questions per day ────────────────────────────────────────"
    q "SELECT to_timestamp(ts)::date AS \"Date\",
              count(*) AS \"Questions\",
              count(DISTINCT user_id) AS \"Users\",
              count(*) FILTER (WHERE is_refusal = 1) AS \"Refused\"
       FROM chat_history GROUP BY 1 ORDER BY 1;"
    echo "── Busiest medicines ────────────────────────────────────────"
    q "SELECT COALESCE(drug,'-') AS \"Medicine\", count(*) AS \"Questions\"
       FROM chat_history GROUP BY 1 ORDER BY 2 DESC LIMIT 8;"
    echo "── Most active users ────────────────────────────────────────"
    q "SELECT user_id AS \"User\", count(*) AS \"Questions\",
              to_char(to_timestamp(max(ts)),'DD Mon HH24:MI') AS \"Last seen\"
       FROM chat_history GROUP BY 1 ORDER BY 2 DESC LIMIT 8;"
    ;;
  days)
    q "SELECT to_timestamp(ts)::date AS \"Date\",
              count(*) AS \"Questions\", count(DISTINCT user_id) AS \"Users\"
       FROM chat_history GROUP BY 1 ORDER BY 1;" ;;
  day)
    [ -z "$2" ] && { echo "usage: bash db.sh day 2026-09-11"; exit 1; }
    q "SELECT $COLS FROM chat_history
       WHERE to_timestamp(ts)::date = DATE '$2' ORDER BY ts;" ;;
  today)
    q "SELECT $COLS FROM chat_history
       WHERE to_timestamp(ts)::date = current_date ORDER BY ts;" ;;
  search)
    [ -z "$2" ] && { echo "usage: bash db.sh search <word> [YYYY-MM-DD]"; exit 1; }
    # Optional 3rd argument narrows the search to a single day.
    DAY_FILTER=""
    [ -n "$3" ] && DAY_FILTER="AND to_timestamp(ts)::date = DATE '$3'"
    q "SELECT $COLS FROM chat_history
       WHERE (question ILIKE '%$2%' OR answer ILIKE '%$2%') $DAY_FILTER
       ORDER BY ts DESC;" ;;
  user)
    [ -z "$2" ] && { echo "usage: bash db.sh user user-104"; exit 1; }
    q "SELECT $COLS FROM chat_history WHERE user_id = '$2' ORDER BY ts;" ;;
  drug)
    [ -z "$2" ] && { echo "usage: bash db.sh drug linzess"; exit 1; }
    q "SELECT $COLS FROM chat_history WHERE drug ILIKE '%$2%' ORDER BY ts;" ;;
  refusals)
    q "SELECT $COLS FROM chat_history WHERE is_refusal = 1 ORDER BY ts DESC;" ;;
  full)
    [ -z "$2" ] && { echo "usage: bash db.sh full 42"; exit 1; }
    q "SELECT id, to_char(to_timestamp(ts),'DD Mon YYYY HH24:MI') AS when,
              user_id, drug, is_refusal, question, answer, citations
       FROM chat_history WHERE id = $2;" ;;
  *)
    sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//' ;;
esac
