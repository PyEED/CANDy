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
    import pytest

    with pytest.raises(ValueError):
        get_curation_backend("unknown-backend")
