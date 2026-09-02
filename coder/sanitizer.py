import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DisregardedSpan:
    note_index: int
    quote: str
    reason: str
    start: int
    end: int


SYSTEM_DIRECTIVE_PATTERNS = [
    r'note\s+to\s+(?:coding|ai|system|coder)',
    r'disregard\s+(?:the\s+)?(?:earlier|previous|prior)\s+(?:guidance|instructions?|advice)',
    r'(?:ignore|override|bypass)\s+(?:the\s+)?(?:guideline|rule|instruction)',
    r'record\s+this\s+(?:encounter|visit|case)\s+as',
    r'code\s+(?:this|it)\s+as',
    r'for\s+insurance\s+purposes',
    r'coding\s+system',
]

IMPERATIVE_VERBS = [
    'disregard', 'ignore', 'override', 'bypass', 'record', 'code', 'change',
    'alter', 'modify', 'force', 'require', 'mandate', 'instruct', 'direct'
]

CLINICAL_CONTEXT_WORDS = [
    'patient', 'pt', 'history', 'exam', 'examination', 'assessment', 'plan',
    'diagnosis', 'treatment', 'medication', 'prescribed', 'advised', 'referred',
    'observed', 'noted', 'reported', 'stated', 'complains', 'c/o', 'presents'
]


def detect_injection_spans(note_text: str, note_index: int) -> List[DisregardedSpan]:
    spans = []
    sentences = re.split(r'(?<=[.!?])\s+', note_text)
    char_offset = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            char_offset += len(sentence) + 1
            continue

        sentence_lower = sentence.lower()
        signals = 0
        signal_details = []

        if any(re.search(pattern, sentence_lower) for pattern in SYSTEM_DIRECTIVE_PATTERNS):
            signals += 2
            signal_details.append("system_directive_pattern")

        has_imperative = any(re.search(rf'\b{verb}\b', sentence_lower) for verb in IMPERATIVE_VERBS)
        if has_imperative:
            signals += 1
            signal_details.append("imperative_verb")

        is_addressed_to_system = bool(re.search(
            r'\b(?:coding\s+system|ai\s+system|system|coder|ai)\b', sentence_lower
        ))
        if is_addressed_to_system:
            signals += 1
            signal_details.append("addressed_to_system")

        clinical_context = any(word in sentence_lower for word in CLINICAL_CONTEXT_WORDS)
        if clinical_context and signals >= 2:
            signals = max(0, signals - 1)
            signal_details.append("clinical_context_reduces")

        all_caps_words = re.findall(r'\b[A-Z]{3,}\b', sentence)
        if all_caps_words and any(len(w) > 4 for w in all_caps_words):
            signals += 1
            signal_details.append("anomalous_all_caps")

        if signals >= 3:
            start = note_text.find(sentence, char_offset)
            end = start + len(sentence)
            spans.append(DisregardedSpan(
                note_index=note_index,
                quote=sentence,
                reason=f"Embedded directive addressed to coding system ({', '.join(signal_details)})",
                start=start,
                end=end
            ))

        char_offset += len(sentence) + 1

    return spans


def sanitize_episode(notes: list) -> Tuple[list, List[DisregardedSpan]]:
    all_disregarded = []
    sanitized_notes = []

    for i, note in enumerate(notes):
        spans = detect_injection_spans(note["text"], i)
        all_disregarded.extend(spans)

        sanitized_text = note["text"]
        for span in reversed(spans):
            sanitized_text = sanitized_text[:span.start] + "[DISREGARDED: " + span.quote + "]" + sanitized_text[span.end:]

        sanitized_notes.append({
            "t": note["t"],
            "author": note["author"],
            "text": sanitized_text,
            "original_text": note["text"]
        })

    return sanitized_notes, all_disregarded