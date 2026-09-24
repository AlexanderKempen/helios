import json

from helios.services.claude import _parse_response


def test_usage_is_read_from_cli_json():
    raw = json.dumps({
        "result": "done",
        "model": "claude-sonnet-5",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 20,
            "cache_creation_input_tokens": 5,
            "cache_read_input_tokens": 7,
        },
    })
    result = _parse_response(raw, "the prompt")
    assert (result.tokens_in, result.tokens_out) == (100, 20)
    assert (result.cache_creation_tokens, result.cache_read_tokens) == (5, 7)
    assert not result.estimated


def test_missing_usage_estimates_input_from_prompt_not_response():
    raw = json.dumps({"result": "a" * 400, "model": "claude-sonnet-5"})
    result = _parse_response(raw, "b" * 800)
    assert result.tokens_in == 200
    assert result.tokens_out == 100
    assert result.estimated


def test_non_json_output_is_treated_as_the_response_body():
    result = _parse_response("plain text reply", "prompt")
    assert result.response == "plain text reply"
    assert result.model is None
    assert result.estimated
