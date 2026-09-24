from helios.services.cost import calculate_cost, estimate_tokens, resolve_pricing


def test_exact_model_id_is_priced_from_the_table():
    prices = resolve_pricing("claude-opus-5")
    assert (prices.input, prices.output) == (5.0, 25.0)
    assert prices.match == "exact"


def test_dated_snapshot_resolves_to_its_base_model():
    prices = resolve_pricing("claude-sonnet-4-5-20250929")
    assert (prices.input, prices.output) == (3.0, 15.0)
    assert prices.match == "prefix"


def test_longest_prefix_wins_over_shorter_family_entry():
    # claude-sonnet-4-6 must not resolve to the cheaper claude-sonnet-4 entry
    # only because that key also prefixes the id.
    assert resolve_pricing("claude-sonnet-4-6").input == 3.0
    assert resolve_pricing("claude-sonnet-5").input == 2.0


def test_vendor_prefixed_and_suffixed_ids_are_normalized():
    assert resolve_pricing("anthropic.claude-opus-5").match == "exact"
    assert resolve_pricing("us.claude-haiku-4-5@20251001").input == 1.0


def test_unknown_model_falls_back_to_its_family():
    prices = resolve_pricing("claude-opus-9-9-20991231")
    assert prices.match == "family"
    assert prices.input == 5.0


def test_missing_model_uses_default_and_is_flagged_unknown():
    prices = resolve_pricing(None)
    assert prices.match == "default"
    assert not prices.is_known


def test_cache_tokens_are_priced_separately():
    cost = calculate_cost(
        tokens_in=1_000_000,
        tokens_out=0,
        model="claude-opus-5",
        cache_creation_tokens=1_000_000,
        cache_read_tokens=1_000_000,
    )
    assert cost == 5.0 + 6.25 + 0.5


def test_estimate_tokens_is_never_zero():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100
