import re


class UnsafeContentError(Exception):
    """Raised when text fails the moderation check."""


# ponytail: permissive keyword gate; swap for a provider check if policy tightens.
# Narrow patterns for the few categories we refuse outright.
_UNSAFE_PATTERNS = [
    re.compile(r'\b(?:how\s+to\s+)?(?:make|build|synthesi[sz]e)\s+a?\s*'
               r'(?:bomb|explosive|nerve\s+agent|bioweapon)\b', re.IGNORECASE),
    re.compile(r'\bchild\s+(?:sexual|porn|abuse)\b', re.IGNORECASE),
]


def is_safe(text: str) -> bool:
    """Return whether text passes the permissive moderation policy."""
    return not any(pattern.search(text or '') for pattern in _UNSAFE_PATTERNS)


def check(text: str) -> None:
    """Raise UnsafeContentError when text fails the moderation policy."""
    if not is_safe(text):
        raise UnsafeContentError('text failed the moderation check')
