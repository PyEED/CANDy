from unittest.mock import MagicMock, patch

import pytest

from candy.curation import get_curation_backend
from candy.curation.manual import ManualCurationBackend


def test_manual_curation_groups_by_index():
    domains = ["Catalytic domain A", "Catalytic domain B", "CBM"]
    responses = iter(["Catalytic domain", "0,1", "STOP"])
    printed = []

    backend = ManualCurationBackend(input_fn=lambda _: next(responses), print_fn=printed.append)
    result = backend.curate(domains)

    assert result == {
        "Catalytic domain": ["Catalytic domain A", "Catalytic domain B"],
        "CBM": ["CBM"],
    }


def test_manual_curation_stop_immediately_keeps_all_names_as_is():
    domains = ["A", "B"]
    responses = iter(["stop"])

    backend = ManualCurationBackend(input_fn=lambda _: next(responses), print_fn=lambda _: None)
    result = backend.curate(domains)

    assert result == {"A": ["A"], "B": ["B"]}


def test_manual_curation_ends_when_all_domains_grouped():
    domains = ["A", "B"]
    responses = iter(["Grouped", "0,1"])

    backend = ManualCurationBackend(input_fn=lambda _: next(responses), print_fn=lambda _: None)
    result = backend.curate(domains)

    assert result == {"Grouped": ["A", "B"]}


def test_get_curation_backend_returns_manual():
    backend = get_curation_backend("manual", input_fn=lambda _: "STOP", print_fn=lambda _: None)
    assert backend.name == "manual"
    assert backend.curate(["A"]) == {"A": ["A"]}


def test_get_curation_backend_unknown_raises():
    with pytest.raises(ValueError):
        get_curation_backend("unknown-backend")


def test_gemini_curate_bounds_request_with_an_explicit_timeout_and_logs_progress(caplog):
    # Regression test: a real run appeared to "hang" with zero output during
    # curation. The SDK's own retry loop (tenacity, on 408/429/5xx) doesn't
    # log anything, and no request timeout was set, so a stall here was
    # indistinguishable from a genuine hang. Assert both fixes: an explicit
    # timeout is passed to the client, and progress is logged before/after.
    pytest.importorskip("google.genai")
    from candy.curation.gemini import GeminiCurationBackend

    fake_response = MagicMock()
    fake_response.text = "{'Catalytic domain': ['A', 'B']}"
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client) as mock_client_cls, caplog.at_level("INFO"):
        backend = GeminiCurationBackend(api_key="fake-key")
        result = backend.curate(["A", "B"], family="GH173")

    assert result == {"Catalytic domain": ["A", "B"]}

    _, kwargs = mock_client_cls.call_args
    assert kwargs["api_key"] == "fake-key"
    assert kwargs["http_options"].timeout == 60_000

    messages = [record.message for record in caplog.records]
    assert any("Requesting domain-name curation from Gemini" in m for m in messages)
    assert any("Received curation response from Gemini" in m for m in messages)
