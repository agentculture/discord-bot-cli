"""Parse a ``--since`` value into an aware UTC :class:`datetime.datetime`.

This module exists because of one line in the discord.py 2.7.1 docs for
``Messageable.history``'s ``before``/``after`` parameters: *"If the datetime
is naive, it is assumed to be local time."* A naive datetime silently shifts
the caller's window by the machine's UTC offset — the exact same ``--since``
value would select a different set of messages depending on the ``TZ`` of the
box the CLI happens to run on. To make that impossible, :func:`parse_since`
guarantees its return value is **always** timezone-aware and normalised to
UTC; there is no code path that can hand back a naive datetime.

Three input forms are accepted:

1. An ISO 8601 timestamp carrying an explicit UTC offset (``+00:00``, ``Z``,
   ``-05:00``, ...), e.g. ``2026-06-01T12:00:00-04:00``. Converted to the
   equivalent UTC instant.
2. A bare date, ``YYYY-MM-DD``, e.g. ``2026-06-01``. Interpreted as midnight
   **UTC** on that date (a recorded user decision — not local midnight),
   giving ``2026-06-01T00:00:00+00:00``.
3. A duration relative to *now*: an integer followed by a unit —
   ``h`` (hours), ``d`` (days), ``w`` (weeks), or ``m`` (months, approximated
   as 30 days each since the stdlib has no calendar-aware duration type).
   Resolves to ``now - delta`` in UTC. ``m`` is months, not minutes, because
   these units read as an ascending calendar-unit progression
   (hour/day/week/month); it does not overload the finer-grained "minutes"
   meaning some tools give ``m``. This is intentional and stated in the
   error hint below so a caller can't guess wrong.

Anything else raises :class:`~discord_bot_cli.cli._errors.CliError` with a
hint naming all three accepted forms.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from discord_bot_cli.cli._errors import EXIT_USER_ERROR, CliError

_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DURATION_RE = re.compile(r"^(\d+)([hdwm])$")

_UNIT_TO_TIMEDELTA = {
    "h": lambda n: timedelta(hours=n),
    "d": lambda n: timedelta(days=n),
    "w": lambda n: timedelta(weeks=n),
    "m": lambda n: timedelta(days=n * 30),
}

_HINT = (
    "Use one of: an ISO 8601 timestamp with a UTC offset (e.g. "
    "'2026-06-01T12:00:00+00:00' or '...Z'), a bare date 'YYYY-MM-DD' "
    "(interpreted as midnight UTC), or a duration '<N><unit>' where unit is "
    "h=hours, d=days, w=weeks, or m=months (e.g. '90d')."
)


def parse_since(value: str) -> datetime:
    """Parse ``value`` into an aware UTC :class:`datetime.datetime`.

    Raises :class:`CliError` (``EXIT_USER_ERROR``) on anything that isn't one
    of the three accepted forms documented in the module docstring.
    """
    text = value.strip()
    if not text:
        raise CliError(EXIT_USER_ERROR, "--since value is empty.", _HINT)

    duration_match = _DURATION_RE.match(text)
    if duration_match:
        unit = duration_match.group(2)
        try:
            count = int(duration_match.group(1))
            delta = _UNIT_TO_TIMEDELTA[unit](count)
            return datetime.now(timezone.utc) - delta
        except (ValueError, OverflowError) as exc:
            # The digit run is unbounded, so int()/timedelta()/subtraction can
            # all blow up on something like '99999999999999999999d'. That is
            # invalid user input, not an internal bug — keep the format hint.
            raise CliError(
                EXIT_USER_ERROR,
                f"--since duration {value!r} is out of range.",
                _HINT,
            ) from exc

    if _DATE_ONLY_RE.match(text):
        try:
            date_only = datetime.fromisoformat(text)
        except ValueError as exc:
            raise CliError(
                EXIT_USER_ERROR, f"Could not parse --since value {value!r}.", _HINT
            ) from exc
        return date_only.replace(tzinfo=timezone.utc)

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CliError(EXIT_USER_ERROR, f"Could not parse --since value {value!r}.", _HINT) from exc

    if parsed.tzinfo is None:
        raise CliError(
            EXIT_USER_ERROR,
            f"--since value {value!r} has no UTC offset; a bare local timestamp is ambiguous.",
            _HINT,
        )

    return parsed.astimezone(timezone.utc)
