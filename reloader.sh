#!/bin/bash

do_reload() {
  PID=$1
  kill -15 $PID
  while ps -p $PID >/dev/null 2>&1; do
    sleep 1
  done
  python3 telemon.py > telemon.log 2>&1 </dev/null &
}

do_reload $1 >> telemon-reload.log 2>&1 &
