#!/bin/bash
# Wrapper for cron and manual runs — loads env and runs daily summary
# Usage: run_summary.sh [lookback_hours]
#   e.g. run_summary.sh 24    # look back 24 hours
#   e.g. run_summary.sh       # auto (since last run)
set -a
source "$(dirname "$0")/../.env"
set +a

export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.12/bin:$PATH"

# Attempt to refresh AWS credentials (non-interactive, uses cached browser session)
duo-sso -profile claudecode -valid-session-threshold 7200 -chrome-persistent >> /tmp/webex-summary.log 2>&1 || true

if [ -n "$1" ]; then
    export SUMMARY_LOOKBACK_H="$1"
fi

cd "$(dirname "$0")/.."
if ! .venv/bin/python3.12 scripts/daily_summary.py >> /tmp/webex-summary.log 2>&1; then
    # If the script failed, try to notify via Webex (which uses separate OAuth, not AWS)
    .venv/bin/python3.12 -c "
import os, sys
sys.path.insert(0, '.')
sys.path.insert(0, 'servers')
from oauth import get_valid_token
from webex_client import WebexClient
token = get_valid_token(os.environ.get('WEBEX_CLIENT_ID',''), os.environ.get('WEBEX_CLIENT_SECRET',''))
if not token: sys.exit(1)
webex = WebexClient(token)
spaces = webex.list_spaces(max_results=200)
target = [s for s in spaces if 'my webex summaries' in s['title'].lower()]
if target:
    webex.send_message(target[0]['id'], '⚠️ Daily triage failed — likely expired AWS credentials. Run: duo-sso -profile claudecode', markdown='⚠️ **Daily triage failed** — likely expired AWS credentials.\n\nRun: \`duo-sso -profile claudecode\`')
" >> /tmp/webex-summary.log 2>&1
fi
