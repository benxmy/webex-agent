---
name: Decision Log
description: |
  This skill maintains a structured log of decisions extracted from Webex conversations, Confluence, and Jira. Use this skill when the user asks "what was decided about X", wants to log a decision, or when the triage framework surfaces decisions made without the user.
version: 1.0.0
---

Capture, store, and query decisions across the user's work streams.

## Decision Structure

Each decision entry contains:

```json
{
  "date": "YYYY-MM-DD",
  "topic": "Short description of what was decided",
  "decision": "The actual decision made",
  "decided_by": ["Person 1", "Person 2"],
  "source": "Space name, Confluence page, or Jira ticket",
  "context": "Brief background on why this came up",
  "ben_involved": true/false,
  "impact": "How this affects Ben's work or projects",
  "status": "active | superseded | revisiting",
  "superseded_by": null,
  "tags": ["project-name", "team-name", "topic"]
}
```

## When to Capture

Capture a decision when:
- The triage framework identifies a "Decision Made Without You" (auto-capture)
- A conversation contains phrases like "we decided", "the plan is", "we're going with", "agreed to", "final call"
- The user explicitly says "log this decision"
- A Jira ticket or Confluence page records a formal decision

Do NOT capture:
- Tentative plans ("we might...", "we're thinking about...")
- Opinions without resolution
- Scheduling decisions (unless they affect project timelines)

## Storage

Decisions are stored in `decision-log.json` in the webex-agent project root. Read the file at the start of any decision-related task. Write updated entries back after capturing new decisions.

## Querying

When the user asks about past decisions:

1. **By topic**: Search `topic`, `decision`, `context`, and `tags` fields
2. **By person**: Search `decided_by` field
3. **By project**: Search `tags` field
4. **By recency**: Sort by date, filter by time range
5. **By involvement**: Filter `ben_involved` to find decisions made without the user

### Query Response Format

```
**[Topic]** — [Date]
Decision: [what was decided]
By: [who decided]
Source: [where it happened]
Status: [active/superseded/revisiting]
```

If a decision has been superseded, show the chain:
```
**[Original Topic]** — [Date] (SUPERSEDED)
Original: [old decision]
Replaced by: [new decision] on [new date]
```

## Integration with Triage

When the webex-agent runs triage and finds decisions in the "Decisions Made Without You" category:
1. Auto-capture them to the decision log with `ben_involved: false`
2. Flag them in the triage output with a note that they've been logged
3. Ask the user if they want to weigh in or just acknowledge

## Maintenance

- When capturing a new decision on a topic that has a prior entry, check if the old decision is being superseded
- Mark superseded decisions and link to the replacement
- Periodically surface decisions tagged "revisiting" that haven't been updated
