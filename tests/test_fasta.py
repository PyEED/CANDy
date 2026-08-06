from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq

from candy.fasta import (
    FormattedRecord,
    count_sequences,
    format_records,
    parse_fasta_to_dict,
    select_sequences_with_domains,
    write_fasta,
)


def make_record(id_, description, seq):
    record = SeqRecord(Seq(seq), id=id_)
    record.description = description
    return record


def test_count_sequences(tmp_path):
    path = tmp_path / "seqs.fasta"
    write_fasta([("a", "MKV"), ("b", "MKL")], path)
    assert count_sequences(path) == 2


def test_parse_fasta_to_dict_roundtrip(tmp_path):
    path = tmp_path / "seqs.fasta"
    write_fasta([("a", "MKV"), ("b", "MKL")], path)
    assert parse_fasta_to_dict(path) == {"a": "MKV", "b": "MKL"}


def test_format_records_extracts_organism_and_taxonomy():
    records = [make_record("P1", "P1 some enzyme [Escherichia coli]", "MKV")]
    formatted = format_records(records, {"P1": "B"})

    assert formatted == [
        FormattedRecord(accession="P1", organism="Escherichia_coli", taxonomy_code="B", sequence="MKV")
    ]
    assert formatted[0].header == "P1_Escherichia_coli_B"


def test_format_records_handles_nested_brackets():
    records = [make_record("P2", "P2 enzyme [[Candida] auris]", "MKL")]
    formatted = format_records(records, {"P2": "E"})
    assert formatted[0].organism == "Candida_auris"


def test_format_records_drops_sequences_without_organism_tag():
    records = [make_record("P3", "P3 enzyme, no bracket here", "MKL")]
    assert format_records(records, {"P3": "E"}) == []


def test_format_records_dedupes_by_sequence_and_id():
    records = [
        make_record("P4", "P4 enzyme [Homo sapiens]", "MKV"),
        make_record("P5", "P5 duplicate sequence [Mus musculus]", "MKV"),
        make_record("P4", "P4 duplicate id [Homo sapiens]", "MKV"),
    ]
    formatted = format_records(records, {"P4": "E", "P5": "E"})
    assert len(formatted) == 1
    assert formatted[0].accession == "P4"


def test_format_records_strips_underscore_from_accession():
    records = [make_record("AW_1234", "AW_1234 enzyme [Escherichia coli]", "MKV")]
    formatted = format_records(records, {"AW_1234": "B"})
    assert formatted[0].accession == "AW1234"


def test_format_records_truncates_long_organism_name():
    long_name = "X" * 150
    records = [make_record("P6", f"P6 enzyme [{long_name}]", "MKV")]
    formatted = format_records(records, {"P6": "B"})
    assert len(formatted[0].organism) == 100


def test_select_sequences_with_domains_keeps_only_domained_cazy_records(tmp_path):
    path = tmp_path / "in.fasta"
    write_fasta([("P1_Org_B", "MKV"), ("P2_Org_B", "MKL")], path)

    output, no_domains = select_sequences_with_domains(
        path, {"P1": [([1, 3], "Domain A")], "P2": []}, is_cazy_query=True
    )

    assert "P1_Org_B" in output
    assert "P2_Org_B" not in output
    assert no_domains == ["P2"]


def test_select_sequences_with_domains_custom_fasta_mode_uses_full_id(tmp_path):
    path = tmp_path / "in.fasta"
    write_fasta([("myheader", "MKV")], path)

    output, no_domains = select_sequences_with_domains(
        path, {"myheader": [([1, 3], "Domain A")]}, is_cazy_query=False
    )

    assert "myheader" in output
    assert no_domains == []
