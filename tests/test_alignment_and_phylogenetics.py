from unittest.mock import patch

from candy.alignment.mafft import MafftAligner
from candy.phylogenetics.fasttree import FastTreeBuilder


def test_mafft_aligner_invokes_binary_with_stdout_redirect(tmp_path):
    input_fasta = tmp_path / "in.fasta"
    output_fasta = tmp_path / "out.fasta"

    with patch("candy.alignment.mafft.require_binary", return_value="/usr/bin/mafft"), patch(
        "candy.alignment.mafft.run_tool"
    ) as mock_run:
        MafftAligner().align(input_fasta, output_fasta)

    args, kwargs = mock_run.call_args
    assert args[0] == ["/usr/bin/mafft", str(input_fasta)]
    assert kwargs["stdout_path"] == output_fasta


def test_fasttree_builder_falls_back_to_lowercase_binary_name(tmp_path):
    alignment = tmp_path / "aligned.fasta"
    output = tmp_path / "tree.nwk"

    def fake_find_binary(name):
        return "/usr/bin/fasttree" if name == "fasttree" else None

    with patch("candy.phylogenetics.fasttree.find_binary", side_effect=fake_find_binary), patch(
        "candy.phylogenetics.fasttree.run_tool"
    ) as mock_run:
        FastTreeBuilder().build_tree(alignment, output)

    args, kwargs = mock_run.call_args
    assert args[0] == ["/usr/bin/fasttree", str(alignment)]
    assert kwargs["stdout_path"] == output
