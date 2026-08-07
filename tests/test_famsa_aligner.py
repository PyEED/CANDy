from candy.alignment import get_alignment_tool
from candy.alignment.famsa import FamsaAligner


def test_get_alignment_tool_returns_famsa_by_name():
    assert get_alignment_tool("famsa").name == "famsa"


def test_famsa_aligner_produces_equal_length_aligned_records(tmp_path):
    input_fasta = tmp_path / "in.fasta"
    output_fasta = tmp_path / "out.fasta"
    input_fasta.write_text(
        ">a\nMKVLAMKVLA\n"
        ">b\nMKVLPMKVLAEXTRA\n"
        ">c\nMKVAAMKVLA\n"
    )

    FamsaAligner().align(input_fasta, output_fasta)

    from Bio import SeqIO

    records = list(SeqIO.parse(output_fasta, "fasta"))
    ids = {r.id for r in records}
    lengths = {len(r.seq) for r in records}

    assert ids == {"a", "b", "c"}
    assert len(lengths) == 1  # all aligned records share one length
