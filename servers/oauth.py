#!/usr/bin/env python3
"""OAuth2 authorization code flow for Webex API."""

import http.server
import json
import os
import sys
import threading
import urllib.parse
import webbrowser

import httpx

TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".webex_token.json")
REDIRECT_URI = "http://localhost:8844/callback"
SCOPES = "spark:messages_read spark:messages_write spark:rooms_read spark:people_read spark:recordings_read meeting:recordings_read meeting:schedules_read"

_auth_code = None
_server_done = threading.Event()


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authorization successful!</h2><p>You can close this tab and return to your terminal.</p></body></html>")
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h2>Authorization failed: {error}</h2></body></html>".encode())
        _server_done.set()

    def log_message(self, format, *args):
        pass  # Suppress request logging


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    response = httpx.post(
        "https://webexapis.com/v1/access_token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Use refresh token to get a new access token."""
    response = httpx.post(
        "https://webexapis.com/v1/access_token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
    )
    response.raise_for_status()
    return response.json()


def save_token(token_data: dict):
    """Save token data to file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"Token saved to {TOKEN_FILE}")


def load_token() -> dict | None:
    """Load token data from file."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def get_valid_token(client_id: str, client_secret: str) -> str:
    """Get a valid access token, refreshing if needed."""
    token_data = load_token()
    if not token_data:
        return ""

    # Try the current access token
    response = httpx.get(
        "https://webexapis.com/v1/people/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    if response.status_code == 200:
        return token_data["access_token"]

    # Try refreshing
    if "refresh_token" in token_data:
        try:
            new_data = refresh_access_token(client_id, client_secret, token_data["refresh_token"])
            save_token(new_data)
            return new_data["access_token"]
        except Exception as e:
            print(f"Token refresh failed: {e}", file=sys.stderr)

    return ""


def login(client_id: str, client_secret: str):
    """Run the full OAuth login flow."""
    auth_url = (
        "https://webexapis.com/v1/authorize?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        })
    )

    server = http.server.HTTPServer(("localhost", 8844), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()

    print("Opening browser for Webex authorization...")
    webbrowser.open(auth_url)
    print("Waiting for authorization callback...")

    _server_done.wait(timeout=120)
    server.server_close()

    if not _auth_code:
        print("Authorization failed or timed out.", file=sys.stderr)
        sys.exit(1)

    print("Exchanging code for tokens...")
    token_data = exchange_code(client_id, client_secret, _auth_code)
    save_token(token_data)
    print("Login successful!")
    return token_data["access_token"]


if __name__ == "__main__":
    client_id = os.environ.get("WEBEX_CLIENT_ID", "")
    client_secret = os.environ.get("WEBEX_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Set WEBEX_CLIENT_ID and WEBEX_CLIENT_SECRET environment variables first.")
        sys.exit(1)

    login(client_id, client_secret)
