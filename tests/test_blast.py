from types import SimpleNamespace
from unittest.mock import patch

from candy.blast import resolve_characterized_via_blast


def make_blast_record(query_length, alignments):
    return SimpleNamespace(query_length=query_length, alignments=alignments)


def make_alignment(accession, hsps):
    return SimpleNamespace(accession=accession, hsps=hsps)


def make_hsp(identities, sbjct):
    return SimpleNamespace(identities=identities, sbjct=sbjct)


def write_fasta(path, records):
    with open(path, "w") as f:
        for header, seq in records:
            f.write(f">{header}\n{seq}\n")


def test_resolve_characterized_via_blast_picks_best_uniparc_hit(tmp_path):
    fasta_path = tmp_path / "characterized.fasta"
    write_fasta(fasta_path, [("P1_Escherichia_coli_B", "MKVLA")])

    blast_records = [
        make_blast_record(
            query_length=100,
            alignments=[
                make_alignment("ACC1", [make_hsp(identities=96, sbjct="MKV")]),  # 96%
                make_alignment("ACC2", [make_hsp(identities=98, sbjct="MKL")]),  # 98%, higher
            ],
        )
    ]

    with patch("candy.blast.NCBIWWW.qblast", return_value=object()), patch(
        "candy.blast.NCBIXML.parse", return_value=iter(blast_records)
    ), patch("candy.blast.match_lookup", return_value=({"ACC1": object(), "ACC2": object()}, [])):
        chosen, sequences = resolve_characterized_via_blast(fasta_path, ["P1"], identity_threshold=95)

    assert chosen == {"P1": "ACC2"}
    assert sequences == {"ACC2": "MKL"}


def test_resolve_characterized_via_blast_skips_id_with_no_hits_above_threshold(tmp_path):
    fasta_path = tmp_path / "characterized.fasta"
    write_fasta(fasta_path, [("P1_Org_B", "MKVLA")])

    blast_records = [make_blast_record(query_length=100, alignments=[])]

    with patch("candy.blast.NCBIWWW.qblast", return_value=object()), patch(
        "candy.blast.NCBIXML.parse", return_value=iter(blast_records)
    ):
        chosen, sequences = resolve_characterized_via_blast(fasta_path, ["P1"], identity_threshold=95)

    assert chosen == {}
    assert sequences == {}


def test_resolve_characterized_via_blast_does_not_leak_state_between_ids(tmp_path):
    # Regression test for the original notebook's bug: a later sequence with
    # zero hits of its own must not pick up an earlier sequence's UniParc
    # match and crash (or silently succeed) via shared accumulated state.
    fasta_path = tmp_path / "characterized.fasta"
    write_fasta(fasta_path, [("P1_Org_B", "MKVLA"), ("P2_Org_B", "AAAAA")])

    call_count = {"n": 0}

    def fake_parse(handle):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return iter([make_blast_record(100, [make_alignment("ACC1", [make_hsp(99, "MKV")])])])
        return iter([make_blast_record(100, [])])  # second id: no hits at all

    with patch("candy.blast.NCBIWWW.qblast", return_value=object()), patch(
        "candy.blast.NCBIXML.parse", side_effect=fake_parse
    ), patch("candy.blast.match_lookup", return_value=({"ACC1": object()}, [])):
        chosen, sequences = resolve_characterized_via_blast(fasta_path, ["P1", "P2"], identity_threshold=95)

    assert chosen == {"P1": "ACC1"}
    assert "P2" not in chosen
