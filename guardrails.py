import re

SCOPE_MESSAGE = (
    "TeamMatch helps you find or recruit teammates for projects and competitions. "
    "Please use the search box to find a competition."
)

# Small, transparent fixed-rule guard. It targets task-performing instructions,
# not ordinary competition/topic keywords.
_TASK_REQUEST_PATTERNS = [
    re.compile(r"\bwrite\b.*\b(proposal|presentation|script|essay|report)\b", re.I),
    re.compile(r"\b(create|draft|make)\b.*\b(proposal|presentation|script|essay|report)\b.*\bfor me\b", re.I),
    re.compile(r"\bdo\b.*\b(assignment|homework|project)\b.*\bfor me\b", re.I),
]


def is_out_of_scope_search(query):
    """True only for clear requests to perform unrelated work in search."""
    text = " ".join((query or "").strip().split())
    if not text:
        return False
    return any(pattern.search(text) for pattern in _TASK_REQUEST_PATTERNS)
