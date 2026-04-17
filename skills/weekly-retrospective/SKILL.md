---
name: Weekly Retrospective
description: |
  This skill defines the methodology for extracting weekly learnings from Webex conversations and maintaining the personal knowledge base. Use this skill when the user asks "what did I learn this week", "run my weekly retrospective", or when updating knowledge.md.
version: 1.0.0
---

Extract and organize weekly learnings from Webex conversations into the personal knowledge base (knowledge.md).

## When to Run

- User asks for a weekly retrospective or "what did I learn this week"
- End of week (Friday) if scheduled
- User asks to update the knowledge base

## Extraction Process

### Step 1: Gather Conversations
- Pull messages from the past 7 days across all active spaces
- Focus on spaces where the user participated (sent messages or was mentioned)
- Include both group spaces and key 1:1 conversations

### Step 2: Classify Insights

Each insight must be classified into exactly one category:

**Technical Insights**
- How systems/features actually work (vs. how people assume they work)
- Bug discoveries, architecture decisions, performance characteristics
- Integration behaviors, API quirks, data model nuances
- Test: "Would this help me debug a problem or make a technical decision?"

**Process Learnings**
- How teams coordinate, communicate, or make decisions
- Release management, cross-team handoffs, escalation patterns
- Development workflow improvements or friction points
- Test: "Would this help me work more effectively with other teams?"

**Business Insights**
- Strategy, roadmap, adoption metrics, customer feedback patterns
- Competitive intelligence, market positioning, pricing/packaging
- Stakeholder priorities and organizational dynamics
- Test: "Would this help me make a better product decision?"

**Performance Data**
- Specific metrics, benchmarks, or quantitative findings
- SLAs, throughput numbers, adoption rates, capacity figures
- Test: "Is this a specific number or measurement I might need to reference later?"

### Step 3: Deduplicate

Before adding a new insight, check existing knowledge.md entries:
- If the same insight was captured in a prior week, skip it
- If a prior insight has been updated or evolved, replace the old version with the new one and note the update
- If a prior insight is contradicted by new information, flag the conflict explicitly

### Step 4: Assess Relevance

Each insight should pass the "future me" test:
- Would I want to know this in 2 weeks? 2 months?
- Is this specific enough to be actionable, or just noise?
- Does this change how I'd approach something?

Skip: routine status updates, scheduling logistics, social chatter, things that are obvious or widely known.

### Step 5: Write Entry

Format each insight as:

```markdown
- **[Concise Title]**: [1-2 sentence explanation with specific details]

*Source: [space name], [date range]*
*Why it matters: [One sentence on relevance to Ben's work]*
```

### Step 6: Organize the Week

Group the week's entry under:

```markdown
## Week of [YYYY-MM-DD]

## **Technical Insights**
- ...

## **Process Learnings**
- ...

## **Business Insights**
- ...

## **Performance Data**
- ...

*Source: [primary spaces], [date range]*
*Why it matters: [Overall theme or takeaway for the week]*
```

## Quality Checks

- Every insight has a source citation
- Every insight has a "why it matters" that connects to Ben's actual work
- No duplicates with prior weeks
- Categories are correct (not everything is a "technical insight")
- Insights are specific, not vague ("SCIM marks attributes as required only if..." not "learned about SCIM")

## Cross-Referencing

When extracting insights, check if they relate to:
- Prior knowledge base entries (note the connection)
- Active projects (flag for relevant agents)
- Recurring themes (if the same topic appears 3+ weeks, call it out as a pattern)
