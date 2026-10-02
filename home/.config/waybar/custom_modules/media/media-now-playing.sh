#!/usr/bin/env bash

zscroll -l 25 \
  --delay 0.4 \
  --update-check true \
  "playerctl metadata --format '{{title}} - {{artist}}'" 2>/dev/null

wait
