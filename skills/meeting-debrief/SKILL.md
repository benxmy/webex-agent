---
name: Meeting Debrief
description: |
  This skill extracts structured debriefs from Webex conversations after meetings. Use this skill when the user asks "what happened in that meeting", "debrief the call", or wants to extract decisions, action items, and open debates from a meeting space.
version: 1.0.0
---

Produce a structured debrief from a Webex meeting conversation, extracting what matters and surfacing what needs follow-up.

## Inputs

1. **Space** — Which Webex space was the meeting in? (name or let the agent search)
2. **Time range** — When did the meeting happen? (defaults to today if not specified)
3. **Context** — Any additional context about what the meeting was about (optional, helps with interpretation)

## Debrief Structure

### Header
```
Meeting: [space name or topic]
Date: [date]
Participants: [names extracted from messages]
Duration: [approximate, based on first/last message timestamps]
```

### 1. Bottom Line
One sentence: what was the most important outcome of this meeting?

### 2. Decisions Made
For each decision:
- **What**: The decision
- **Who decided**: Person(s) who made or confirmed the call
- **Confidence**: Firm (explicitly agreed) / Soft (seemed agreed but not formally confirmed) / Tentative (leaning toward but revisitable)

If the decision-log skill is available, offer to log firm decisions.

### 3. Action Items
For each action:
- **Who**: Person responsible
- **What**: The task
- **By when**: Deadline if mentioned, "unspecified" if not
- **Ben's items**: Flag any actions assigned to the user separately at the top

### 4. Open Debates
Topics where the group did NOT reach agreement:
- **Topic**: What was being debated
- **Positions**: Who holds what view
- **Sticking point**: What's preventing resolution
- **Next step**: Is this being tabled, escalated, or continuing async?

### 5. Key Information Shared
Important facts, data points, or context that came up:
- New information that changes understanding
- Metrics or timelines mentioned
- External factors or dependencies surfaced

### 6. Follow-Up Recommendations
Based on the meeting content, suggest:
- Messages the user should send (draft them)
- Topics that need a separate conversation
- Information gaps that need filling
- Connections to other projects or prior decisions

## Extraction Guidelines

- **Distinguish decisions from opinions** — "I think we should..." is not a decision. "Let's go with..." followed by agreement is.
- **Attribute accurately** — Don't assign actions or positions to people unless the messages clearly support it
- **Capture tension** — If people disagreed, surface the disagreement honestly. Don't smooth over conflicts.
- **Note absences** — If key stakeholders weren't in the conversation, mention it (they may need to be looped in)
- **Flag recurring debates** — If this topic has come up before (check knowledge base), note that it's a pattern

## Integration

- **Decision log**: Offer to capture decisions via the decision-log skill
- **Knowledge base**: If technical/business insights emerged, offer to add them via weekly-retrospective skill
- **Triage**: If the meeting surfaced items that are blocked on the user, flag them for immediate attention
