# Webex Agent for Claude Code — Setup Guide

> A Claude Code plugin that acts as your Webex chief of staff. It triages your messages, searches conversations, drafts responses, and runs automated daily briefings — so you spend less time scrolling Webex and more time on the work that matters.

---

## What It Does

### Triage & Briefings
- **Smart triage**: Scans all your Webex spaces and categorizes what needs attention into four priority buckets:
  1. **Blocked on You** — someone's waiting for your input
  2. **Decisions Made Without You** — things decided that affect your work
  3. **Opportunities to Add Value** — threads where your expertise could help
  4. **FYI** — context only, no action needed
- **Draft responses**: Generates ready-to-send replies for items that need your attention
- **Automated daily briefings**: Cron-scheduled triage delivered to a Webex space or email (e.g., 8:30am and 4pm)
- **Weekly retrospectives**: Extracts learnings from the week's conversations and builds a personal knowledge base

### Search & Analysis
- **Keyword search**: Find specific messages across all your spaces
- **Topic search**: Semantic search — finds conversations by concept, not just exact words
- **Deep analysis**: Ask questions about what's been discussed on a topic across spaces
- **Transcript formatting**: Chronological, readable conversation threads

### Communication
- **Send messages**: Post to any Webex space directly from Claude
- **Pre-meeting context**: Automatically pulls recent DM history with your meeting attendees before calls

### Trainable Preferences
- Teach it what matters to you — which spaces are high-priority, which topics to always flag, what to ignore
- Learns over time through a `preferences.md` file you can edit or train conversationally

---

## Prerequisites

- **Claude Code** installed and working (with an Anthropic API key or AWS Bedrock access)
- **Python 3.12+**
- **A Cisco Webex account**
- ~30 minutes for initial setup

---

## Setup — Step by Step

### 1. Clone the repo

```bash
git clone https://github.com/benmyers-cisco/webex-agent.git ~/projects/webex-agent
cd ~/projects/webex-agent
```

### 2. Create a Python virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Set up Webex authentication

You have two options. **OAuth is recommended** — personal tokens expire every 12 hours.

#### Option A: OAuth (Recommended)

1. Go to [developer.webex.com/my-apps/new/integration](https://developer.webex.com/my-apps/new/integration)
2. Create a new integration with these settings:
   - **Name**: Whatever you want (e.g., "Claude Webex Agent")
   - **Redirect URI**: `http://localhost:8844/callback`
   - **Scopes** — select all of these:
     - `spark:messages_read`
     - `spark:messages_write`
     - `spark:rooms_read`
     - `spark:rooms_write`
     - `spark:memberships_write`
     - `spark:people_read`
     - `spark:recordings_read`
     - `meeting:recordings_read`
     - `meeting:schedules_read`
3. Save your **Client ID** and **Client Secret**
4. Add them to your `.env` file (see step 4 below)
5. Run the OAuth flow to authorize:
   ```bash
   set -a && source .env && set +a
   python servers/oauth.py
   ```
   This opens your browser for Webex login. After you authorize, tokens are saved to `.webex_token.json` and auto-refresh on each use.

#### Option B: Personal Access Token (Quick & Dirty)

1. Go to [developer.webex.com/docs/getting-started](https://developer.webex.com/docs/getting-started)
2. Copy your personal access token
3. Add it to `.env` as `WEBEX_ACCESS_TOKEN`

> **Warning**: Personal tokens expire after 12 hours. You'll need to re-copy it daily. OAuth is better for anything beyond a quick test.

### 4. Configure your environment

Copy the example env file and fill it in:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Webex OAuth credentials
WEBEX_CLIENT_ID=your_client_id
WEBEX_CLIENT_SECRET=your_client_secret

# Your Cisco email (used to identify your messages in triage)
SUMMARY_USER_EMAIL=you@cisco.com

# Where to deliver automated briefings
SUMMARY_DELIVERY=webex                    # Options: webex, email, both
SUMMARY_WEBEX_SPACE=My Webex Summaries    # Create this space in Webex first

# Claude API (pick one)
ANTHROPIC_API_KEY=your_api_key            # Direct API access
# — OR —
CLAUDE_CODE_USE_BEDROCK=true              # Use AWS Bedrock instead
AWS_PROFILE=your_aws_profile
```

### 5. Register as a Claude Code plugin

From the webex-agent directory:

The project includes a `.mcp.json` that auto-configures the MCP server. To use it, add the project directory to your Claude Code settings as a project directory, or copy `.mcp.json` into your own project's root.

### 6. Test it

Open Claude Code and try:

```
What needs my attention in Webex?
```

Or search for something specific:

```
Search Webex for discussions about the API migration in the last 7 days
```

---

## Optional: Automated Briefings

### Daily triage via cron

Add cron jobs for automated briefings (adjust paths and times to your timezone):

```bash
crontab -e
```

```cron
# Daily triage at 8:30am and 4pm ET (weekdays only)
30 12 * * 1-5 cd ~/projects/webex-agent && set -a && source .env && set +a && .venv/bin/python3.12 scripts/daily_summary.py
0 20 * * 1-5 cd ~/projects/webex-agent && set -a && source .env && set +a && .venv/bin/python3.12 scripts/daily_summary.py

# Weekly retrospective — Fridays at 1pm ET
0 17 * * 5 cd ~/projects/webex-agent && set -a && source .env && set +a && .venv/bin/python3.12 scripts/weekly_retro.py
```

The daily summary automatically tracks when it last ran (via a `.last_run` file), so it only looks back to the last briefing — no duplicate items.

### Pre-meeting context (SessionStart hook)

The `scripts/check_upcoming_meetings.py` script can run at Claude Code startup to check for meetings in the next 10 minutes and pull DM context with attendees. Add it as a SessionStart hook in your Claude Code settings if you want this.

---

## Training Your Preferences

The agent uses `preferences.md` to learn what matters to you. You can edit it directly or train it conversationally:

```
Hey, always flag messages about security incidents.
Ignore general chatter in the All-Hands space unless I'm mentioned.
The Project Alpha space is high priority — always include it.
```

The preferences file looks like this:

```markdown
## My Role & Focus
- Jane Smith (jsmith@cisco.com), PM on the Platform team

## Always Relevant
- API breaking changes
- Security incidents
- Mentions of Project Alpha

## Never Relevant
- General help desk chatter unless mentioned by name
- Social/watercooler spaces

## Space-Specific Rules
- In All-Hands: only flag if directly mentioned
- In Platform-Eng: always include (my team)
```

---

## How It Decides What's Important

The triage logic is selective about which spaces to scan:

| Space Type | Included? |
|-----------|-----------|
| DMs | Always (if new activity) |
| Small group chats (<10 people) | Always (if new activity) |
| Large channels (10+ people) | Only if you're @mentioned and haven't responded, or you were newly added in the last 24 hours |
| Spaces with no activity in lookback period | Skipped |
| Spaces marked irrelevant in preferences | Skipped |

This keeps briefings focused. You won't get noise from 200-person channels unless something specifically needs your attention.

---

## Example Interactions

**Triage:**
> "What needs my attention from the last 24 hours?"

**Search:**
> "Search Webex for discussions about the Duo integration in the last 2 weeks"

**Deep analysis:**
> "What has the Platform team been discussing about the migration? Summarize the key decisions and open questions."

**Draft responses:**
> "Draft a response to Sarah's question in the API Design space"

**Send a message:**
> "Send a message to the Project Alpha space: 'Hey team — the updated timeline is on Confluence. Let me know if you have questions.'"

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Token expired" errors | Re-run `python servers/oauth.py` to re-authorize. If using personal token, grab a fresh one from developer.webex.com. |
| MCP server not loading | Check that `.mcp.json` exists and the Python path is correct. Run `which python3.12` to verify. |
| No spaces returned | Verify your `SUMMARY_USER_EMAIL` matches your Webex login email exactly. |
| Triage returns nothing | Check lookback period — if `.last_run` is recent, it may be looking at a very short window. Delete `.last_run` to reset. |
| OAuth callback fails | Make sure nothing else is running on port 8844. Check your redirect URI matches exactly. |

---

## Project Structure

```
webex-agent/
├── servers/webex_mcp.py        # MCP server (9 tools exposed to Claude)
├── servers/oauth.py            # OAuth2 flow + token refresh
├── webex_client.py             # Webex API HTTP client
├── agents/webex-analyst.md     # Agent definition
├── scripts/
│   ├── daily_summary.py        # Automated daily triage
│   ├── weekly_retro.py         # Weekly learning extraction
│   └── check_upcoming_meetings.py  # Pre-meeting context
├── skills/
│   ├── webex-triage.md         # Portable triage skill
│   └── weekly-retrospective/   # Insight extraction methodology
├── preferences.md              # Your trainable triage rules
├── knowledge.md                # Extracted learnings
├── .env.example                # Environment template
└── requirements.txt            # Python dependencies
```

---

## Questions?

Ping Ben Myers on Webex — or better yet, ask your Webex Agent to find the answer.
