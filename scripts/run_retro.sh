#!/bin/bash
# Wrapper for weekly retrospective cron
# Usage: run_retro.sh [lookback_days]
#   e.g. run_retro.sh 14    # look back 2 weeks
#   e.g. run_retro.sh       # default 7 days
set -a
source "$(dirname "$0")/../.env"
set +a

export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.12/bin:$PATH"

if [ -n "$1" ]; then
    export RETRO_LOOKBACK_DAYS="$1"
fi

cd "$(dirname "$0")/.."
.venv/bin/python3.12 scripts/weekly_retro.py >> /tmp/webex-retro.log 2>&1
