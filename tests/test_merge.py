from candy.merge import _protein_id_for_merge, merge_characterized_sequences


def test_protein_id_for_merge_long_accession():
    assert _protein_id_for_merge("P12345_Org_B") == "P12345"


def test_protein_id_for_merge_short_prefix_joins_first_two_segments():
    assert _protein_id_for_merge("AW_12345_Org_B") == "AW_12345"


def test_protein_id_for_merge_no_underscore():
    assert _protein_id_for_merge("plainid") == "plainid"


def test_merge_excludes_clustered_duplicate_and_appends_characterized(tmp_path):
    clustered = tmp_path / "clustered.fasta"
    characterized = tmp_path / "characterized.fasta"
    output = tmp_path / "merged.fasta"

    clustered.write_text(">P12345_Org_B\nMKVAAA\n>P99999_Org2_E\nMKLBBB\n")
    # Headers from candy.cazy.fetch_characterized_sequences already end in
    # "_{taxcode}" -- the taxonomy code must not be duplicated on merge.
    characterized.write_text(">P12345_Escherichia_coli_B\nMKVREPLACED\n")

    merge_characterized_sequences(
        clustered,
        characterized,
        output,
        verified_ids=["P12345"],
        blast_choice={},
        blast_hit_sequences={},
    )

    content = output.read_text()
    assert "P99999" in content  # untouched, not characterized
    assert content.count("MKVAAA") == 0  # clustered copy of P12345 dropped
    assert "MKVREPLACED" in content  # characterized version appended
    assert ">P12345_Escherichia_coli_B" in content
    assert ">P12345_Escherichia_coli_B_B" not in content  # no duplicated taxcode


def test_merge_uses_blast_hit_sequence_when_available(tmp_path):
    clustered = tmp_path / "clustered.fasta"
    characterized = tmp_path / "characterized.fasta"
    output = tmp_path / "merged.fasta"

    clustered.write_text("")
    characterized.write_text(">P12345_Org_B\nORIGINAL_SEQ\n")

    merge_characterized_sequences(
        clustered,
        characterized,
        output,
        verified_ids=["P12345"],
        blast_choice={"P12345": "ACC1"},
        blast_hit_sequences={"ACC1": "BLAST_HOMOLOG_SEQ"},
    )

    content = output.read_text()
    assert "BLAST_HOMOLOG_SEQ" in content
    assert "ORIGINAL_SEQ" not in content
