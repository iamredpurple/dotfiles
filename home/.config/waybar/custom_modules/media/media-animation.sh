#!/usr/bin/env bash

# "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"

#frames=("▂▄▆" "▄▂▆" "▄▆▂" "▆▄▂" "▂▆▄" "▆▂▄")

frames=(
  "⣴⣄⣴"
  "⣴⣄⣤"
  "⣴⣄⣠"
  "⣴⣤⣠"
  "⣤⣤⣠"
  "⣠⣠⣤"
  "⣠⣀⣤"
  "⣠⣄⣦"
  "⣤⣄⣦"
  "⣤⣀⣤"
  "⣄⣀⣤"
  "⣄⣄⣴"
  "⣠⣤⣰"
  "⣰⣤⣠"
  "⣰⣴⣠"
  "⣰⣰⣠"
  "⣤⣰⣴"
  "⣤⣤⣶"
  "⣄⣤⣶"
  "⣄⣤⣦"
  "⣤⣄⣦"
  "⣤⣄⣶"
  "⣤⣄⣦"
  "⣠⣄⣤"
  "⣀⣄⣤"
  "⣀⣀⣠"
  "⣤⣠⣠"
  "⣴⣤⣤"
  "⣤⣤⣶"
  "⣤⣀⣶"
  "⣀⣀⣶"
  "⣀⣄⣦"
  "⣀⣆⣦"
  "⣠⣆⣶"
)

while :; do
  for frame in "${frames[@]}"; do

    status=$(playerctl metadata --format '{{status}}' 2>/dev/null)

    if [ "$status" == "Playing" ]; then
      echo "$frame"
    elif [ "$status" == "Paused" ]; then
      echo "  "
    else
      echo ""
    fi

    sleep 0.1

  done
done
