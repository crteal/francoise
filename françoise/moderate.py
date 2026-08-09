import logging
import re

logger = logging.getLogger(__name__)


class UnsafeContentError(Exception):
    """Raised when text fails the moderation check."""


class MinorSafetyError(UnsafeContentError):
    """Raised when text sexualizes a child persona.

    A subclass of UnsafeContentError so callers that already block unsafe
    content keep blocking, but this category is handled separately: it is
    audited and the account is flagged, and the permissive policy never
    applies to it.
    """


# Specialized minor-safety provider. Kept separate from the permissive
# keyword gate below so this category can never be softened by policy.
# ponytail: deterministic co-occurrence gate; swap for a model provider if
# recall matters.
_MINOR_TERMS = re.compile(
    r'\b(?:child|children|kid|kids|minor|minors|underage|'
    r'little\s+(?:girl|boy)|young\s+(?:girl|boy)|preteen|toddler)\b',
    re.IGNORECASE)
_SEXUAL_TERMS = re.compile(
    r'\b(?:sex|sexual|sexually|porn|pornographic|nude|naked|explicit|'
    r'aroused?|erotic)\b', re.IGNORECASE)


def _default_flag_account(account_id):
    """Record that an account tripped the minor-safety check.

    Default sink keeps a process-local set so the flag is observable without
    a schema change. Override `flag_account` to persist it.
    """
    _flagged_accounts.add(account_id)


_flagged_accounts: set = set()

# Seam for persisting the account flag. Replace to write to the database.
flag_account = _default_flag_account


def minor_safety(text: str, account_id=None) -> None:
    """Block sexual content that involves a child persona.

    On a hit: write an audit log, flag the account, and raise. This runs
    before the permissive policy so that policy never governs this category.
    """
    if _MINOR_TERMS.search(text or '') and _SEXUAL_TERMS.search(text or ''):
        logger.warning(
            'minor-safety block: account=%s', account_id, extra={
                'audit': 'minor_safety',
                'account_id': account_id,
            })
        flag_account(account_id)
        raise MinorSafetyError('text failed the minor-safety check')


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


def check(text: str, account_id=None) -> None:
    """Raise UnsafeContentError when text fails the moderation policy.

    The specialized minor-safety check runs first and cannot be softened by
    the permissive policy below.
    """
    minor_safety(text, account_id=account_id)
    if not is_safe(text):
        raise UnsafeContentError('text failed the moderation check')
