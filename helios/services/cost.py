from __future__ import annotations

PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-5-haiku-20241022": {"input": 1.0, "output": 5.0},
}

DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def calculate_cost(tokens_in: int, tokens_out: int, model: str | None = None) -> float:
    """Calculate cost in USD. Prices are per 1M tokens."""
    prices = PRICING.get(model or "", DEFAULT_PRICING)
    return (tokens_in * prices["input"] + tokens_out * prices["output"]) / 1_000_000


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 characters per token."""
    return max(1, len(text) // 4)
