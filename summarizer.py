import anthropic
from datetime import datetime


def format_messages(messages: list[dict]) -> str:
    """Format Webex messages into a readable transcript."""
    lines = []
    for msg in reversed(messages):  # Chronological order
        sender = msg.get("personEmail", "Unknown")
        timestamp = msg.get("created", "")
        text = msg.get("text", "[non-text content]")
        short_time = timestamp[:16].replace("T", " ") if timestamp else ""
        lines.append(f"[{short_time}] {sender}: {text}")
    return "\n".join(lines)


def summarize_messages(
    client: anthropic.Anthropic,
    messages: list[dict],
    space_name: str,
    model: str = "claude-sonnet-4-6-20250514",
) -> str:
    """Use Claude to summarize a list of Webex messages."""
    if not messages:
        return "No messages found in the specified timeframe."

    transcript = format_messages(messages)
    msg_count = len(messages)
    first_time = messages[-1].get("created", "")[:10] if messages else "?"
    last_time = messages[0].get("created", "")[:10] if messages else "?"

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""Summarize the following Webex space conversation.

Space: {space_name}
Messages: {msg_count} messages from {first_time} to {last_time}

Provide:
1. A brief overview (2-3 sentences)
2. Key topics discussed (bulleted list)
3. Action items or decisions made (if any)
4. Notable participants and their contributions

Transcript:
{transcript}""",
            }
        ],
    )
    return response.content[0].text


def semantic_search(
    client: anthropic.Anthropic,
    messages: list[dict],
    query: str,
    space_name: str,
    model: str = "claude-sonnet-4-6-20250514",
) -> str:
    """Use Claude to find messages matching a concept or topic."""
    if not messages:
        return "No messages to search."

    transcript = format_messages(messages)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""Search the following Webex conversation for messages related to this query: "{query}"

This is a semantic search -- find messages that are relevant to the query even if they don't contain the exact keywords. Look for related concepts, discussions, and context.

Space: {space_name}

For each relevant match, provide:
- The timestamp and sender
- The relevant message text
- Why it's relevant to the query

If nothing is relevant, say so.

Transcript:
{transcript}""",
            }
        ],
    )
    return response.content[0].text


def analyze_topic(
    client: anthropic.Anthropic,
    messages: list[dict],
    topic: str,
    space_name: str,
    model: str = "claude-sonnet-4-6-20250514",
) -> str:
    """Deeply analyze a conversation around a specific topic or concept."""
    if not messages:
        return "No messages found to analyze."

    transcript = format_messages(messages)
    msg_count = len(messages)
    first_time = messages[-1].get("created", "")[:10] if messages else "?"
    last_time = messages[0].get("created", "")[:10] if messages else "?"

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": f"""You are an expert analyst. Analyze the following Webex conversation and produce a deep, synthesized briefing focused on this topic:

"{topic}"

Space: {space_name}
Messages: {msg_count} messages from {first_time} to {last_time}

Go beyond keyword matching. Extract and connect ideas, opinions, decisions, and context related to the topic even when it's discussed indirectly. Think of this as building a knowledge briefing that someone could read to quickly get up to speed.

Structure your analysis as:

## Overview
A concise 2-4 sentence executive summary of what has been discussed about this topic.

## Key Insights
The most important takeaways, ideas, or conclusions related to the topic. Synthesize across multiple messages and participants — don't just list individual messages.

## Timeline of Discussion
How the conversation around this topic evolved over time. Note any shifts in thinking, new information that changed the direction, or escalations.

## People & Perspectives
Who contributed to this topic and what their positions or viewpoints were. Note any disagreements or alignment.

## Decisions & Action Items
Any concrete decisions made, action items assigned, or next steps agreed upon related to the topic.

## Open Questions
Anything that was raised but not resolved, or areas where there seems to be ambiguity or uncertainty.

## Related Topics
Other subjects in the conversation that connect to or overlap with the topic — things the reader might also want to look into.

If the topic is barely or not discussed, say so clearly and summarize what IS being discussed instead, in case the user is looking in the wrong place.

Transcript:
{transcript}""",
            }
        ],
    )
    return response.content[0].text
