#!/usr/bin/env python3
"""Daily Webex summary — fetches recent messages, triages with Claude, and delivers via Webex or email."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import anthropic
from webex_client import WebexClient

# Add servers dir for oauth import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "servers"))
from oauth import get_valid_token

LAST_RUN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".last_run")
DEFAULT_LOOKBACK_H = 12


def get_lookback_time() -> datetime:
    """Get the start time for this run: either last run time, SUMMARY_LOOKBACK_H, or default."""
    # Explicit override takes priority (for manual/agent calls)
    override = os.environ.get("SUMMARY_LOOKBACK_H")
    if override:
        return datetime.now(timezone.utc) - timedelta(hours=int(override))

    # Otherwise, use last run timestamp
    if os.path.exists(LAST_RUN_FILE):
        try:
            with open(LAST_RUN_FILE) as f:
                ts = f.read().strip()
            return datetime.fromisoformat(ts)
        except (ValueError, OSError):
            pass

    # Fallback
    return datetime.now(timezone.utc) - timedelta(hours=DEFAULT_LOOKBACK_H)


def save_run_timestamp():
    """Record when this run started."""
    with open(LAST_RUN_FILE, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def get_webex_client() -> WebexClient:
    client_id = os.environ.get("WEBEX_CLIENT_ID", "")
    client_secret = os.environ.get("WEBEX_CLIENT_SECRET", "")
    token = ""
    if client_id and client_secret:
        token = get_valid_token(client_id, client_secret)
    if not token:
        token = os.environ.get("WEBEX_ACCESS_TOKEN", "")
    if not token:
        print("No valid Webex token available.", file=sys.stderr)
        sys.exit(1)
    return WebexClient(token)


def get_claude_client() -> anthropic.Anthropic:
    """Create Claude client — supports both direct API and Bedrock."""
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "true":
        return anthropic.AnthropicBedrock(
            aws_profile=os.environ.get("AWS_PROFILE", "default"),
        )
    return anthropic.Anthropic()


def load_preferences() -> str:
    """Load user preferences for triage relevance filtering."""
    prefs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "preferences.md")
    if os.path.exists(prefs_path):
        with open(prefs_path) as f:
            return f.read()
    return ""


def triage_with_claude(client, transcript: str, space_name: str, user_email: str) -> str:
    """Analyze a conversation and triage into actionable categories with draft responses."""
    model = "us.anthropic.claude-sonnet-4-20250514-v1:0" if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "true" else "claude-sonnet-4-6-20250514"
    preferences = load_preferences()
    prefs_block = f"\n\nUSER PREFERENCES (use these to judge relevance):\n{preferences}" if preferences else ""

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"""You are a chief-of-staff creating an actionable briefing for {user_email}.
{prefs_block}

Analyze this Webex conversation and categorize into EXACTLY these sections. Only include sections that have content — omit empty sections entirely.

### Blocked on you
People waiting for your input, approval, or response. These are the highest priority — someone else cannot move forward until you act.
For each item: who is waiting, what they need, and a **suggested reply** you could send (in a quoted block).

### Decisions made without you
Decisions, conclusions, or direction changes that happened in this conversation that affect your work. You weren't part of the decision but need to know about it.
For each: what was decided, by whom, and whether you need to weigh in.

### Opportunities to add value
Discussions where your expertise or perspective could meaningfully help, but nobody has asked you directly. These are chances to be proactive.
For each: what's being discussed, why your input matters, and a **suggested message** you could send (in a quoted block).

### FYI
Important context or updates — no action needed, but useful to know.

RULES:
- ERR ON THE SIDE OF OVER-INFORMING. When in doubt about whether something is relevant, include it. It's better to flag something the user can quickly skip than to miss something important. Only respond with "No items requiring your attention." if the conversation is truly unrelated to their work.
- Be specific — include names, timestamps, and quote key phrases
- Draft responses should be concise, professional, and ready to send with minimal editing
- Don't include items where {user_email} has already responded
- Prioritize within each section (most urgent first)
- Only skip topics/spaces the user has explicitly marked as irrelevant in preferences

Space: {space_name}

Transcript:
{transcript}""",
        }],
    )
    return response.content[0].text


def format_messages(messages: list[dict]) -> str:
    lines = []
    for msg in reversed(messages):
        sender = msg.get("personEmail", "Unknown")
        timestamp = msg.get("created", "")[:16].replace("T", " ")
        text = msg.get("text", "[non-text content]")
        lines.append(f"[{timestamp}] {sender}: {text}")
    return "\n".join(lines)


def deliver_webex(webex: WebexClient, summary: str, space_name: str):
    spaces = webex.list_spaces(max_results=200)
    matches = [s for s in spaces if space_name.lower() in s["title"].lower()]
    if not matches:
        print(f"Could not find delivery space '{space_name}'", file=sys.stderr)
        return
    room_id = matches[0]["id"]
    # Webex has a ~7000 char limit per message — split by section if too long
    max_len = 6000
    if len(summary) <= max_len:
        webex.send_message(room_id, summary, markdown=summary)
    else:
        sections = summary.split("\n\n---\n\n")
        for i, section in enumerate(sections):
            chunk = section if i == 0 else f"*(continued)*\n\n{section}"
            if len(chunk) > max_len:
                chunk = chunk[:max_len] + "\n\n*(truncated)*"
            webex.send_message(room_id, chunk, markdown=chunk)
    print(f"Summary posted to '{matches[0]['title']}'")


def deliver_email(summary: str, to_addr: str, subject: str):
    import smtplib
    from email.mime.text import MIMEText

    smtp_host = os.environ.get("SMTP_HOST", "localhost")
    smtp_port = int(os.environ.get("SMTP_PORT", "25"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    from_addr = os.environ.get("SMTP_FROM", smtp_user or "webex-agent@localhost")

    msg = MIMEText(summary)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if smtp_port == 587:
            server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    print(f"Summary emailed to {to_addr}")


GROUP_CHAT_THRESHOLD = 10  # <=10 members = group chat, >10 = channel


def find_my_relevant_spaces(webex: WebexClient, lookback: datetime, max_spaces: int = 20) -> list[dict]:
    """Find relevant spaces based on type:
    - DMs: always include if there's new activity
    - Group chats (<=10 members): always include if there's new activity
    - Channels (>10 members): only include if @mentioned and not responded
    """
    all_spaces = webex.list_spaces(max_results=200)

    relevant_spaces = []
    total = len(all_spaces)
    for i, space in enumerate(all_spaces, 1):
        print(f"  Checking ({i}/{total}): {space['title'][:40]}...", end="\r")

        space_type = space.get("type", "group")

        if space_type == "direct":
            # DMs: include if there are new messages
            messages = webex.get_messages(space["id"], after=lookback, max_results=1)
            if messages:
                relevant_spaces.append(space)
        else:
            # Group space — check member count to distinguish chat vs channel
            member_count = webex.get_member_count(space["id"])
            if member_count <= GROUP_CHAT_THRESHOLD:
                # Small group chat: include if there's new activity
                messages = webex.get_messages(space["id"], after=lookback, max_results=1)
                if messages:
                    relevant_spaces.append(space)
            else:
                # Channel: include if @mentioned and haven't responded,
                # OR if newly added in the last 24 hours (catch up on new channels)
                if webex.has_unresponded_mentions(space["id"], after=lookback):
                    relevant_spaces.append(space)
                elif webex.is_newly_added(space["id"], within_hours=24):
                    relevant_spaces.append(space)

        if len(relevant_spaces) >= max_spaces:
            break

    print()  # Clear the progress line
    return relevant_spaces


def main():
    after = get_lookback_time()
    lookback_desc = datetime.now(timezone.utc) - after
    lookback_hours = round(lookback_desc.total_seconds() / 3600, 1)

    delivery = os.environ.get("SUMMARY_DELIVERY", "webex")
    delivery_space = os.environ.get("SUMMARY_WEBEX_SPACE", "")
    delivery_email = os.environ.get("SUMMARY_EMAIL_TO", "")
    user_email = os.environ.get("SUMMARY_USER_EMAIL", "benmyers@cisco.com")

    webex = get_webex_client()
    claude = get_claude_client()

    print(f"Looking back {lookback_hours}h (since {after.strftime('%Y-%m-%d %H:%M UTC')})...")
    target_spaces = find_my_relevant_spaces(webex, lookback=after, max_spaces=20)

    if not target_spaces:
        print("No spaces with your recent activity found.")
        save_run_timestamp()
        return

    print(f"Found {len(target_spaces)} relevant spaces. Triaging...")

    # Triage each space
    blocked_parts = []
    decisions_parts = []
    opportunities_parts = []
    fyi_parts = []

    for space in target_spaces:
        messages = webex.get_messages(space["id"], after=after, max_results=200)
        if not messages:
            continue
        print(f"  Analyzing '{space['title']}' ({len(messages)} messages)...")
        transcript = format_messages(messages)
        triage = triage_with_claude(claude, transcript, space["title"], user_email)
        if "no items requiring your attention" in triage.lower():
            print(f"    -> Nothing relevant, skipping.")
            continue

        # Parse sections from the triage output and group across spaces
        current_section = None
        current_lines = []
        for line in triage.split("\n"):
            lower = line.lower().strip().replace("*", "").replace("#", "").strip()
            if "blocked on you" in lower:
                if current_section and current_lines:
                    _append_section(current_section, current_lines, space["title"],
                                    blocked_parts, decisions_parts, opportunities_parts, fyi_parts)
                current_section = "blocked"
                current_lines = []
            elif "decisions made without you" in lower:
                if current_section and current_lines:
                    _append_section(current_section, current_lines, space["title"],
                                    blocked_parts, decisions_parts, opportunities_parts, fyi_parts)
                current_section = "decisions"
                current_lines = []
            elif "opportunities to add value" in lower:
                if current_section and current_lines:
                    _append_section(current_section, current_lines, space["title"],
                                    blocked_parts, decisions_parts, opportunities_parts, fyi_parts)
                current_section = "opportunities"
                current_lines = []
            elif lower.startswith("fyi"):
                if current_section and current_lines:
                    _append_section(current_section, current_lines, space["title"],
                                    blocked_parts, decisions_parts, opportunities_parts, fyi_parts)
                current_section = "fyi"
                current_lines = []
            else:
                current_lines.append(line)
        if current_section and current_lines:
            _append_section(current_section, current_lines, space["title"],
                            blocked_parts, decisions_parts, opportunities_parts, fyi_parts)

    if not any([blocked_parts, decisions_parts, opportunities_parts, fyi_parts]):
        print("No actionable items found.")
        save_run_timestamp()
        return

    # Build the final digest grouped by priority
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    parts = [f"# Webex Briefing — {now_str}"]

    if blocked_parts:
        parts.append("## 🔴 Blocked on You\n" + "\n".join(blocked_parts))
    if decisions_parts:
        parts.append("## 🟡 Decisions Made Without You\n" + "\n".join(decisions_parts))
    if opportunities_parts:
        parts.append("## 🟢 Opportunities to Add Value\n" + "\n".join(opportunities_parts))
    if fyi_parts:
        parts.append("## ℹ️ FYI\n" + "\n".join(fyi_parts))

    full_summary = "\n\n---\n\n".join(parts)

    # Deliver
    if delivery in ("webex", "both") and delivery_space:
        deliver_webex(webex, full_summary, delivery_space)
    if delivery in ("email", "both") and delivery_email:
        deliver_email(full_summary, delivery_email, f"Webex Briefing — {now_str}")
    if not delivery_space and not delivery_email:
        print("No delivery target configured — printing to stdout:\n")
        print(full_summary)

    save_run_timestamp()


def _append_section(section: str, lines: list[str], space_title: str,
                    blocked: list, decisions: list, opportunities: list, fyi: list):
    """Append parsed section content to the appropriate list."""
    content = "\n".join(lines).strip()
    if not content:
        return
    entry = f"**{space_title}**\n{content}\n"
    if section == "blocked":
        blocked.append(entry)
    elif section == "decisions":
        decisions.append(entry)
    elif section == "opportunities":
        opportunities.append(entry)
    elif section == "fyi":
        fyi.append(entry)


if __name__ == "__main__":
    main()
