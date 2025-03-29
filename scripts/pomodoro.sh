#!/bin/bash

WORK_MINUTES=25
BREAK_MINUTES=5
LONG_BREAK_MINUTES=15
POMODOROS_PER_LONG_BREAK=4

# Get the PID of this script (excluding the grep process itself)
MYPID=$$
if pgrep -f "pomodoro.sh" | grep -qv "$MYPID"; then
  # Another instance is running - kill it
  notify-send "Pomodoro Timer" "Timer stopped" -a "Pomodoro"
  pkill -KILL -f "pomodoro.sh"
  exit
fi

# Initialize counters
pomodoro_count=0

# Main loop
while true; do
  # Work period
  notify-send "Pomodoro Timer" "Work time! ($WORK_MINUTES minutes)" -a "Pomodoro"
  sleep ${WORK_MINUTES}m

  ((pomodoro_count++))

  if ((pomodoro_count % POMODOROS_PER_LONG_BREAK == 0)); then
    notify-send "Pomodoro Timer" "Great job! Take a long break ($LONG_BREAK_MINUTES minutes)" -a "Pomodoro"
    sleep ${LONG_BREAK_MINUTES}m
  else
    notify-send "Pomodoro Timer" "Good work! Take a short break ($BREAK_MINUTES minutes)" -a "Pomodoro"
    sleep ${BREAK_MINUTES}m
  fi

done
