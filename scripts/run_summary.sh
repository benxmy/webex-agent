#!/bin/bash
# Wrapper for cron and manual runs — loads env and runs daily summary
# Usage: run_summary.sh [lookback_hours]
#   e.g. run_summary.sh 24    # look back 24 hours
#   e.g. run_summary.sh       # auto (since last run)
set -a
source "$(dirname "$0")/../.env"
set +a

export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.12/bin:$PATH"

if [ -n "$1" ]; then
    export SUMMARY_LOOKBACK_H="$1"
fi

cd "$(dirname "$0")/.."
.venv/bin/python3.12 scripts/daily_summary.py >> /tmp/webex-summary.log 2>&1
