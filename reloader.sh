#!/bin/bash

do_reload() {
  PID=$1
  kill -15 $PID

  WAIT=1
  while ps -p $PID >/dev/null 2>&1; do
    if [ $((WAIT%10)) == "0" ]; then
      echo "Waiting for $PID for $WAIT seconds already"
      kill -15 $PID
    fi

    sleep 1
    WAIT=$((WAIT+1))
  done

  python3 telemon.py > telemon.log 2>&1 </dev/null &
}

echo "Reloading telemon process $1:"
sleep 1
do_reload $1 >> telemon-reload.log 2>&1 &
