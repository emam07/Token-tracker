import re

from token_tracker.core.models import Warning


def check_vague_intent(prompt: str) -> Warning | None:
    patterns = [
        r"\btell me (something|a bit|a little) about\b",
        r"\bcan you (talk|speak|say something) about\b",
        r"\b(something|stuff|things) about\b",
        r"\bwhat do you (know|think) about\b",
        r"\bi (want|need|'?d like) to know\b",
        r"\bcan (u|you) tell me\b",
        r"\bdo you know (anything|something) about\b",
    ]
    for p in patterns:
        if re.search(p, prompt, re.IGNORECASE):
            return Warning(
                rule="VAGUE_INTENT",
                severity="high",
                message="No specific task - vague phrasing gives Claude no clear direction.",
                suggestion="Use an action verb: 'List 5 key concepts of X' or 'Explain how X works in 3 sentences'.",
            )
    return None


def check_missing_format(prompt: str) -> Warning | None:
    wants_list = re.search(
        r"\b(list|enumerate|give me|show me|what are|name (some|the|a few))\b",
        prompt, re.IGNORECASE,
    )
    has_format = re.search(
        r"\b(bullet|numbered|table|json|markdown|csv|as a list|as a table|in points|in steps)\b",
        prompt, re.IGNORECASE,
    )
    if wants_list and not has_format:
        return Warning(
            rule="MISSING_FORMAT",
            severity="medium",
            message="Asks for a list but output format is unspecified.",
            suggestion="Add format: 'as a numbered list', 'as a markdown table', or 'as JSON'.",
        )
    return None


def check_missing_scope(prompt: str) -> Warning | None:
    wants_explanation = re.search(
        r"\b(explain|describe|summarize|tell me about|give me an overview|introduction to|guide (to|on)|i don'?t know (about|anything about)|teach me about)\b",
        prompt, re.IGNORECASE,
    )
    has_scope = re.search(
        r"\b(\d+\s*(word|sentence|paragraph|line|point|bullet)s?|brief|concise|short|in depth|comprehensive|quick)\b",
        prompt, re.IGNORECASE,
    )
    if wants_explanation and not has_scope:
        return Warning(
            rule="MISSING_SCOPE",
            severity="medium",
            message="Open-ended explanation with no length or depth constraint.",
            suggestion="Constrain the response: 'in 3 sentences', 'in under 100 words', or 'briefly'.",
        )
    return None


def check_filler_words(prompt: str) -> Warning | None:
    filler_patterns = [
        r"\bplease\b",
        r"\bcould you kindly\b",
        r"\bI was wondering if\b",
        r"\bif you don'?t mind\b",
        r"\bwould you be so kind\b",
        r"\bI hope you can\b",
        r"\bI'?d like to ask\b",
        r"\bthank you in advance\b",
        r"\bif it'?s? (possible|not too much trouble)\b",
    ]
    found = [
        re.search(p, prompt, re.IGNORECASE).group()
        for p in filler_patterns
        if re.search(p, prompt, re.IGNORECASE)
    ]
    if found:
        examples = ", ".join(f"'{f}'" for f in found[:3])
        return Warning(
            rule="FILLER_WORDS",
            severity="low",
            message=f"Courtesy filler adds tokens with zero meaning: {examples}.",
            suggestion="Remove politeness phrases - Claude needs clarity, not courtesy.",
        )
    return None


def check_redundant_context(prompt: str) -> Warning | None:
    sentences = [s.strip() for s in re.split(r"[.!?]", prompt) if len(s.strip()) > 20]
    seen: set[str] = set()
    for s in sentences:
        normalised = re.sub(r"\s+", " ", s.lower())
        if normalised in seen:
            return Warning(
                rule="REDUNDANT_CONTEXT",
                severity="medium",
                message="Prompt contains repeated sentences.",
                suggestion="Each piece of context should appear once - remove duplicates.",
            )
        seen.add(normalised)
    return None


def check_wall_of_text(prompt: str, estimated_tokens: int) -> Warning | None:
    has_structure = re.search(r"(\n[-*•]|\n\d+\.|\n#{1,6} |\|.+\|)", prompt)
    if estimated_tokens > 500 and not has_structure:
        return Warning(
            rule="WALL_OF_TEXT",
            severity="high",
            message=f"Large unstructured block (~{estimated_tokens} tokens) with no formatting.",
            suggestion="Add headers/bullets, or summarise the context before pasting it in.",
        )
    return None


def check_ambiguous_pronoun(prompt: str) -> Warning | None:
    words = prompt.split()
    # Count standalone 'it' references
    it_count = sum(
        1 for w in words
        if re.fullmatch(r"it[,.]?", w, re.IGNORECASE)
    )
    # Flag multiple ambiguous 'it' in any length prompt
    if it_count >= 3:
        return Warning(
            rule="AMBIGUOUS_PRONOUN",
            severity="low",
            message=f"'it' appears {it_count} times — each likely refers to something different.",
            suggestion="Replace each 'it' with the actual noun it refers to.",
        )
    # Original short-prompt check for fix/do/make it
    match = re.search(
        r"\b(fix it|do it|make it|change it|update it|improve it|rewrite it|check it)\b",
        prompt, re.IGNORECASE,
    )
    if match and len(words) < 15:
        return Warning(
            rule="AMBIGUOUS_PRONOUN",
            severity="low",
            message=f"'{match.group()}' - 'it' has no clear referent in a short prompt.",
            suggestion=f"Name the thing explicitly: '{match.group().replace('it', '<subject>')}'.",
        )
    return None


def check_open_ended_task(prompt: str) -> Warning | None:
    match = re.search(
        r"\b(everything about|all about|write a (complete|full|comprehensive|detailed) (guide|tutorial|overview|book|article)|tell me all|explain everything)\b",
        prompt, re.IGNORECASE,
    )
    if match:
        return Warning(
            rule="OPEN_ENDED_TASK",
            severity="high",
            message=f"Unbounded task scope: '{match.group()}'.",
            suggestion="Pick a specific angle or add 'in under 500 words' to cap the output.",
        )
    return None


def check_text_speak(prompt: str) -> Warning | None:
    """Informal abbreviations and text-speak reduce clarity and waste tokens on correction."""
    patterns = [
        r"\bcan u\b",
        r"\b(ur|u r)\b",
        r"\b(plz|pls)\b",
        r"\bidk\b",
        r"\br u\b",
        r"\bcuz\b",
        r"\bw/o\b",
        r"\b(gonna|wanna|gotta)\b",
    ]
    found = [
        re.search(p, prompt, re.IGNORECASE).group()
        for p in patterns
        if re.search(p, prompt, re.IGNORECASE)
    ]
    if found:
        examples = ", ".join(f"'{f}'" for f in found[:3])
        return Warning(
            rule="TEXT_SPEAK",
            severity="low",
            message=f"Informal shorthand found: {examples}. Claude responds to formal language more precisely.",
            suggestion="Write out full words: 'can you' not 'can u', 'your' not 'ur'.",
        )
    return None


def check_vague_closing(prompt: str) -> Warning | None:
    """Prompt ends with a vague request rather than a specific ask."""
    closing_patterns = [
        r"\bcan (u|you) tell me\s*[?.]?\s*$",
        r"\bany (thoughts|ideas|suggestions|help)\s*[?.]?\s*$",
        r"\bwhat do you think\s*[?.]?\s*$",
        r"\b(please help|help me out|help me)\s*[?.]?\s*$",
        r"\bi need help\s*[?.]?\s*$",
        r"\blet me know\s*[?.]?\s*$",
        r"\bjust help\s*[?.]?\s*$",
    ]
    for p in closing_patterns:
        if re.search(p, prompt, re.IGNORECASE):
            return Warning(
                rule="VAGUE_CLOSING",
                severity="high",
                message="Prompt ends with a vague request — Claude has no specific task to complete.",
                suggestion="End with a concrete ask: 'List 3 steps to fix this' or 'Explain X in 2 sentences'.",
            )
    return None


def check_topic_drift(prompt: str) -> Warning | None:
    """Prompt switches to an unrelated topic mid-way, splitting Claude's focus."""
    # Look for a topic switch after 'but' that introduces a completely different subject
    # Heuristic: 'but I don't know' / 'but also' / 'also, separately' mid-prompt
    drift_patterns = [
        r"\bbut (also,?\s*)?(i don'?t know|i have no (idea|knowledge|clue)|i'?m (not|a) (sure|familiar|new to))\b",
        r"\b(also,?\s*separately|on a (different|separate|unrelated) (note|topic|subject))\b",
        r"\band (also,?\s*)?(by the way|btw|separately)\b",
    ]
    for p in drift_patterns:
        if re.search(p, prompt, re.IGNORECASE):
            return Warning(
                rule="TOPIC_DRIFT",
                severity="medium",
                message="Prompt introduces an unrelated topic mid-way — split into two separate prompts.",
                suggestion="One prompt, one task. Send the second question as a follow-up.",
            )
    return None


# Rules that take only (prompt) — check_wall_of_text is called separately with token count
RULES = [
    check_vague_intent,
    check_missing_format,
    check_missing_scope,
    check_filler_words,
    check_redundant_context,
    check_ambiguous_pronoun,
    check_open_ended_task,
    check_text_speak,
    check_vague_closing,
    check_topic_drift,
]
