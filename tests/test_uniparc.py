from candy.uniparc import write_verified_fasta


def test_write_verified_fasta_keeps_only_available_non_partial(tmp_path):
    input_path = tmp_path / "in.fasta"
    output_path = tmp_path / "out.fasta"
    input_path.write_text(
        ">P1 complete sequence\nMKV\n"
        ">P2 partial sequence\nMKL\n"
        ">P3 complete sequence\nMKA\n"
    )

    written = write_verified_fasta(input_path, output_path, available_ids={"P1", "P2"})

    assert written == 1
    content = output_path.read_text()
    assert "P1" in content
    assert "P2" not in content
    assert "P3" not in content
