#!/bin/bash
# One-shot reminder via Webex — deletes itself from crontab after running
set -a
source "$(dirname "$0")/../.env"
set +a

export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.12/bin:$PATH"

cd "$(dirname "$0")/.."
.venv/bin/python3.12 -c "
import sys; sys.path.insert(0, 'servers')
from oauth import get_valid_token
from webex_client import WebexClient
import os

token = get_valid_token(os.environ['WEBEX_CLIENT_ID'], os.environ['WEBEX_CLIENT_SECRET'])
client = WebexClient(token)
spaces = client.list_spaces(max_results=200)
matches = [s for s in spaces if 'my webex summaries' in s['title'].lower()]
if matches:
    client.send_message(matches[0]['id'],
        '**Reminder: Two things for today**\n\n'
        '1. **Train your Webex agent** on what\'s relevant to you! '
        'Launch with \`webex-agent\` and tell it things like:\n'
        '   - \"I lead the auth team\"\n'
        '   - \"Always flag migration project updates\"\n'
        '   - \"Skip general help desk chatter\"\n'
        '   - \"In kit-kat, only flag me if mentioned by name\"\n\n'
        '2. **Research adding email analysis** to the agent — '
        'extend triage and retrospectives to cover your inbox, not just Webex.')
    print('Reminder sent')
"

# Remove this reminder from crontab
crontab -l | grep -v 'send_reminder.sh' | crontab -
