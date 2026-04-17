#!/usr/bin/env python3.12
"""One-shot script to send a reminder message to Webex."""
import json
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "servers"))

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

from oauth import get_valid_token
from webex_client import WebexClient

ROOM_ID = "Y2lzY29zcGFyazovL3VzL1JPT00vODBhYTQ0NDAtMmUxMS0xMWYxLThmNmYtOGIyZWYwNGY4NmUw"

client_id = os.environ["WEBEX_CLIENT_ID"]
client_secret = os.environ["WEBEX_CLIENT_SECRET"]

token = get_valid_token(client_id, client_secret)
if not token:
    print("ERROR: Could not get valid Webex token. Re-auth may be needed.", file=sys.stderr)
    sys.exit(1)

message = sys.argv[1] if len(sys.argv) > 1 else "Reminder: no message specified"

client = WebexClient(access_token=token)
client.send_message(room_id=ROOM_ID, text=message)
print(f"Sent reminder to My Webex Summaries")
