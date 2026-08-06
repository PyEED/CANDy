import http.client
from unittest.mock import patch

import pandas as pd

from candy.cazy import (
    extract_characterized_ids,
    extract_ncbi_ids,
    fetch_characterized_sequences,
    fetch_sequences_fasta,
    parse_family_table,
)
from candy.config import Taxonomy

SAMPLE_FAMILY_TABLE = (
    "GH5\tBacteria\tEcoli\tP12345\tncbi\n"
    "GH5\tArchaea\tSacc\tP67890\tjgi\n"
    "GH5\tEukaryota\tYeast\tP11111\tncbi\n"
)


def test_parse_family_table_builds_taxonomy_dict():
    df, taxonomy_dict = parse_family_table(SAMPLE_FAMILY_TABLE)
    assert taxonomy_dict == {"P12345": "B", "P67890": "A", "P11111": "E"}
    assert len(df) == 3


def test_extract_ncbi_ids_excludes_jgi_sourced():
    df, taxonomy_dict = parse_family_table(SAMPLE_FAMILY_TABLE)
    ids = extract_ncbi_ids(df, taxonomy_dict, Taxonomy.ALL)
    assert ids == ["P12345", "P11111"]


def test_extract_ncbi_ids_filters_by_taxonomy():
    df, taxonomy_dict = parse_family_table(SAMPLE_FAMILY_TABLE)
    ids = extract_ncbi_ids(df, taxonomy_dict, Taxonomy.BACTERIA)
    assert ids == ["P12345"]


def test_extract_characterized_ids_groups_by_taxonomy_header():
    # column 4 mimics CAZy's characterized table layout: taxonomy header rows
    # interspersed with GenBank-ID rows ("ID.version").
    col4 = pd.Series(["Bacteria", "P12345.1", "P12345.1", "Archaea", "Q99999.2"])
    col1 = pd.Series(["", "1.2.4.-", "1.2.4.-", "", "3.2.1.-"])
    table = pd.DataFrame({1: col1, 4: col4})

    ids, taxonomy_dict, activity_dict = extract_characterized_ids([None, table])

    assert ids == ["P12345.1", "Q99999.2"]
    assert taxonomy_dict == {"P12345.1": "B", "Q99999.2": "A"}
    assert activity_dict == {"P12345.1": "1.2.4.-", "Q99999.2": "3.2.1.-"}


class FakeHandle:
    """Stand-in for the object Bio.Entrez.efetch returns (used as a context manager)."""

    def __init__(self, text):
        self._text = text

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._text


def test_fetch_sequences_fasta_retries_past_incomplete_read():
    # Regression test: a real run hit http.client.IncompleteRead mid-fetch
    # (NCBI's connection dropped during a large chunked response) and the
    # original except-HTTPError-only clause let it crash the whole pipeline
    # instead of retrying like other transient network errors.
    calls = {"n": 0}

    def fake_efetch(db, id, rettype, retmode):
        calls["n"] += 1
        if calls["n"] == 1:
            raise http.client.IncompleteRead(b"partial")
        return FakeHandle(">P1\nMKV\n")

    with patch("candy.cazy.Entrez.efetch", side_effect=fake_efetch), patch("candy.cazy.time.sleep"):
        result = fetch_sequences_fasta(["P1"], "test@example.com")

    assert result == ">P1\nMKV\n"
    assert calls["n"] == 2


def test_fetch_sequences_fasta_gives_up_after_max_retries():
    def fake_efetch(db, id, rettype, retmode):
        raise http.client.IncompleteRead(b"")

    with patch("candy.cazy.Entrez.efetch", side_effect=fake_efetch), patch("candy.cazy.time.sleep"):
        result = fetch_sequences_fasta(["P1"], "test@example.com")

    assert result == ""  # gives up gracefully rather than raising


def test_fetch_characterized_sequences_retries_past_connection_error():
    calls = {"n": 0}

    def fake_efetch(db, id, rettype, retmode):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("connection reset")
        return FakeHandle(">P1.1 enzyme [Escherichia coli]\nMKV\n")

    with patch("candy.cazy.Entrez.efetch", side_effect=fake_efetch), patch("candy.cazy.time.sleep"):
        result = fetch_characterized_sequences(["P1.1"], {"P1.1": "B"}, Taxonomy.ALL, "test@example.com")

    assert "MKV" in result
    assert calls["n"] == 2
