import re

from token_tracker.core.models import Warning


def check_vague_intent(prompt: str) -> Warning | None:
    patterns = [
        r"\btell me (something|a bit|a little) about\b",
        r"\bcan you (talk|speak|say something) about\b",
        r"\b(something|stuff|things) about\b",
        r"\bwhat do you (know|think) about\b",
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
        r"\b(explain|describe|summarize|tell me about|give me an overview|introduction to|guide (to|on))\b",
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
    match = re.search(
        r"\b(fix it|do it|make it|change it|update it|improve it|rewrite it|check it)\b",
        prompt, re.IGNORECASE,
    )
    if match and len(prompt.split()) < 15:
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


# Rules that take only (prompt) - wall_of_text is called separately with token count
RULES = [
    check_vague_intent,
    check_missing_format,
    check_missing_scope,
    check_filler_words,
    check_redundant_context,
    check_ambiguous_pronoun,
    check_open_ended_task,
]
