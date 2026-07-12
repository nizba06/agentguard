"""Aho-Corasick injection signature pre-filter."""

from __future__ import annotations

from dataclasses import dataclass, field

import ahocorasick

# High-precision signatures only — avoid broad phrases that match benign prose
# (e.g. bare "act as"). Target: 50+ rules with low false-positive rate.
_BUILTIN_RULES: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore your instructions",
    "ignore all instructions",
    "disregard previous instructions",
    "disregard all prior instructions",
    "disregard your instructions",
    "forget your instructions",
    "forget all previous instructions",
    "forget the system prompt",
    "override system prompt",
    "override the system prompt",
    "override safety",
    "you are now",
    "you must now",
    "from now on you",
    "act as if you are",
    "act as if you're",
    "pretend you are",
    "pretend you're",
    "roleplay as",
    "your new role is",
    "your new task is",
    "your real task is",
    "developer mode enabled",
    "jailbreak mode",
    "jailbreak",
    "bypass safety",
    "bypass restrictions",
    "bypass all safety",
    "disable safety filters",
    "send all data to",
    "send the contents to",
    "send to http",
    "send to https",
    "POST to http",
    "POST to https",
    "exfiltrate data",
    "exfiltrate credentials",
    "exfiltrate secrets",
    "upload to attacker",
    "the real task is",
    "true instructions:",
    "new objective:",
    "updated objective:",
    "actually your task is",
    "system override",
    "priority override",
    "ignore safety guidelines",
    "reveal system prompt",
    "print system prompt",
    "show system prompt",
    "execute shell command",
    "run shell command",
    "do not follow your original",
    "discard your previous directives",
)


@dataclass
class RuleFilterResult:
    """Result of rule-based injection scanning."""

    flagged: bool
    matched_rules: list[str] = field(default_factory=list)


class InjectionRuleFilter:
    """Multi-pattern O(n) injection signature scanner."""

    def __init__(self, rules: tuple[str, ...] | None = None) -> None:
        """Initialise filter with built-in or custom rules."""
        self._rules = rules or _BUILTIN_RULES
        self._automaton = self._build_automaton()

    def _build_automaton(self) -> ahocorasick.Automaton:
        automaton = ahocorasick.Automaton()
        for idx, rule in enumerate(self._rules):
            automaton.add_word(rule.lower(), (idx, rule))
        automaton.make_automaton()
        return automaton

    def scan(self, message: str) -> RuleFilterResult:
        """Scan a message for known injection signatures.

        Args:
            message: Message text to inspect.

        Returns:
            RuleFilterResult with flagged status and matched rule labels.
        """
        lower = message.lower()
        matched: dict[str, int] = {}
        for _end, (_idx, original) in self._automaton.iter(lower):
            matched[original] = _idx
        if not matched:
            return RuleFilterResult(flagged=False)
        rules = [rule for rule, _ in sorted(matched.items(), key=lambda item: item[1])]
        return RuleFilterResult(flagged=True, matched_rules=rules)

    @property
    def rule_count(self) -> int:
        """Return the number of loaded rules."""
        return len(self._rules)
