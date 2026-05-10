"""Rule-based prompt rewriter. No API calls, no ML — just regex and heuristics."""
from __future__ import annotations

import re

from token_tracker.core.models import Warning

# Filler patterns — each is (regex, replacement)
_FILLER_SUBS: list[tuple[str, str]] = [
    (r"\bplease\s+",                          ""),
    (r"\bcould you kindly\s+",                ""),
    (r"\bcould you please\s+",                ""),
    (r"\bI was wondering if\s+(you could)?",  ""),
    (r"\bif you don'?t mind,?\s+",            ""),
    (r"\bwould you be so kind (to|as to)\s+", ""),
    (r"\bI hope you can\s+",                  ""),
    (r"\bI'?d like to ask\s+",                ""),
    (r"\bif (it'?s? )?possible,?\s+",         ""),
    (r"\bthank you in advance\b",             ""),
    (r"\bif it'?s? not too much trouble,?\s+",""),
    (r"\bkindly\s+",                          ""),
]

# Vague intent → action verb
_VAGUE_SUBS: list[tuple[str, str]] = [
    (r"\btell me (something|a bit|a little) about\b",  "Explain"),
    (r"\bcan you (talk|speak|say something) about\b",  "Explain"),
    (r"\bwhat do you (know|think) about\b",            "Summarize"),
]

# Open-ended task → bounded scope
_OPEN_SUBS: list[tuple[str, str]] = [
    (r"\beverything about\b",      "the key concepts of"),
    (r"\ball about\b",              "the main aspects of"),
    (r"\bexplain everything\b",     "explain the core concepts"),
    (r"\btell me all\b",            "summarize the key points"),
    (r"\bwrite a (complete|full|comprehensive|detailed) (guide|tutorial|overview)\b",
     r"write a focused \2"),
]


def _apply_subs(text: str, subs: list[tuple[str, str]]) -> str:
    for pattern, replacement in subs:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Drop dangling conjunctions left over from removed filler ("X and Y and" -> "X and Y")
    text = re.sub(r"\s+(and|or|but|so)\s*[.!?]?\s*$", "", text, flags=re.IGNORECASE)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _remove_duplicate_sentences(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen: set[str] = set()
    unique = []
    for s in sentences:
        norm = re.sub(r"\s+", " ", s.lower()).strip().rstrip(".!?")
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(s)
    return " ".join(unique)


def _add_constraints(text: str, original_warnings: list[Warning]) -> str:
    rules_present = {w.rule for w in original_warnings}
    additions: list[str] = []

    if "MISSING_FORMAT" in rules_present:
        if re.search(r"\b(list|enumerate|name|give me)\b", text, re.IGNORECASE):
            additions.append("Respond as a numbered list, one item per line.")

    if "MISSING_SCOPE" in rules_present:
        additions.append("Keep response under 200 words.")

    if "WALL_OF_TEXT" in rules_present:
        additions.append("(Consider summarizing the context above before sending.)")

    if not additions:
        return text

    if not text.rstrip().endswith((".", "?", "!")):
        text = text.rstrip() + "."
    return text + " " + " ".join(additions)


def optimize(prompt: str, warnings: list[Warning]) -> str:
    """Apply all rewrites in order. Returns optimized prompt string."""
    if not warnings:
        return ""

    text = prompt
    text = _remove_duplicate_sentences(text)
    text = _apply_subs(text, _FILLER_SUBS)
    text = _apply_subs(text, _VAGUE_SUBS)
    text = _apply_subs(text, _OPEN_SUBS)
    text = _normalize_whitespace(text)
    text = _add_constraints(text, warnings)
    return text
