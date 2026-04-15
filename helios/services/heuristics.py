from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class HeuristicSignals:
    prompt_tokens: int = 0
    feature_count: int = 0
    has_ui: bool = False
    has_backend: bool = False
    has_tests: bool = False
    has_migration: bool = False
    has_auth: bool = False
    has_refactor: bool = False
    complexity_keywords: list[str] = field(default_factory=list)

    @property
    def scope_score(self) -> float:
        """0-1 score where higher = more complex."""
        score = 0.0
        score += min(self.prompt_tokens / 2000, 0.3)
        score += min(self.feature_count * 0.08, 0.25)
        if self.has_ui and self.has_backend:
            score += 0.15
        elif self.has_ui or self.has_backend:
            score += 0.05
        if self.has_migration:
            score += 0.1
        if self.has_auth:
            score += 0.1
        if self.has_refactor:
            score += 0.1
        if self.has_tests:
            score += 0.05
        return min(score, 1.0)

    @property
    def scope_label(self) -> str:
        s = self.scope_score
        if s < 0.3:
            return "small"
        if s < 0.6:
            return "medium"
        return "large"

    @property
    def token_range(self) -> tuple[int, int]:
        """Rough token estimate based on heuristics alone."""
        base_min, base_max = 5_000, 30_000
        multiplier = 1.0 + self.scope_score * 8
        return int(base_min * multiplier), int(base_max * multiplier)


UI_PATTERNS = re.compile(
    r"\b(ui|frontend|component|page|dashboard|modal|form|button|css|style|layout|view|render|template)\b", re.I
)
BACKEND_PATTERNS = re.compile(
    r"\b(api|endpoint|route|controller|service|database|db|query|migration|schema|server|handler|middleware)\b", re.I
)
AUTH_PATTERNS = re.compile(r"\b(auth|login|signup|register|session|token|oauth|permission|role|rbac)\b", re.I)
MIGRATION_PATTERNS = re.compile(r"\b(migrat|schema\s+change|alter\s+table|add\s+column)\b", re.I)
REFACTOR_PATTERNS = re.compile(r"\b(refactor|restructure|rewrite|reorganize|cleanup|clean\s+up|decouple)\b", re.I)
TEST_PATTERNS = re.compile(r"\b(test|spec|coverage|e2e|integration\s+test|unit\s+test)\b", re.I)

FEATURE_SPLITTERS = re.compile(r"\d+\.\s|\n[-*]\s|;\s*(?:and|also)\b|,\s*(?:and\s)?", re.I)


def analyze_prompt(text: str) -> HeuristicSignals:
    tokens = max(1, len(text) // 4)

    features = FEATURE_SPLITTERS.split(text)
    feature_count = max(1, len([f for f in features if len(f.strip()) > 10]))

    complexity_keywords: list[str] = []
    for pattern, label in [
        (AUTH_PATTERNS, "auth"), (MIGRATION_PATTERNS, "migration"),
        (REFACTOR_PATTERNS, "refactor"), (TEST_PATTERNS, "tests"),
    ]:
        if pattern.search(text):
            complexity_keywords.append(label)

    return HeuristicSignals(
        prompt_tokens=tokens,
        feature_count=feature_count,
        has_ui=bool(UI_PATTERNS.search(text)),
        has_backend=bool(BACKEND_PATTERNS.search(text)),
        has_tests=bool(TEST_PATTERNS.search(text)),
        has_migration=bool(MIGRATION_PATTERNS.search(text)),
        has_auth=bool(AUTH_PATTERNS.search(text)),
        has_refactor=bool(REFACTOR_PATTERNS.search(text)),
        complexity_keywords=complexity_keywords,
    )
