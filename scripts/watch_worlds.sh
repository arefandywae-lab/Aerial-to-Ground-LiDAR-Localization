#!/bin/bash
# Watches the world queue: new result/error lines, stalls, queue death, and a status heartbeat every 30 min. One stdout line = one alert.
L=/a/SlamProject/scripts
declare -A pos
for f in $L/world_*.log $L/allworlds.log; do [ -f "$f" ] && pos[$f]=$(wc -l < "$f"); done
last_change=$(date +%s); beat=$(date +%s)
while true; do
  for f in $L/world_*.log $L/allworlds.log; do
    [ -f "$f" ] || continue
    n=$(wc -l < "$f"); p=${pos[$f]:-0}; [ "$n" -lt "$p" ] && p=0
    if [ "$n" -gt "$p" ]; then
      last_change=$(date +%s)
      tail -n +$((p+1)) "$f" | grep -E --line-buffered "ATE rmse|GT robot poses|best 2D shift|prior:|global:|WORLD_.*_DONE|ALLWORLDS_DONE|Traceback|Error|No such file|Killed|Aborted" | sed "s|^|$(basename $f): |" | cut -c1-330
      pos[$f]=$n
    fi
  done
  now=$(date +%s)
  alive=$(MSYS_NO_PATHCONV=1 powershell -c "wsl -d Ubuntu-24.04 -u root -- bash -c 'pgrep -f world_pipeline.sh | head -1'" 2>/dev/null | tr -d '\r')
  if [ -z "$alive" ] && ! grep -q ALLWORLDS_DONE $L/allworlds.log 2>/dev/null; then echo "ALERT: queue is NOT running and has not finished (WSL restarted or the script died)"; fi
  if [ $((now - last_change)) -gt 2400 ] && [ -n "$alive" ]; then echo "ALERT: no new log line for $(( (now - last_change) / 60 )) min while the queue is alive (possible stall)"; last_change=$now; fi
  if [ $((now - beat)) -gt 1800 ]; then beat=$now; cur=$(ls -t $L/world_*.log | head -1); echo "STATUS: queue alive=${alive:+yes}, current $(basename $cur): $(tail -n 1 $cur | cut -c1-120)"; fi
  sleep 60
done
