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


def test_fasttree_builder_uses_resolved_binary(tmp_path):
    # Binary resolution itself (PATH, cache, auto-download/compile) is
    # tested in tests/test_fasttree_download.py; this just verifies
    # FastTreeBuilder wires the resolved path through to run_tool correctly.
    alignment = tmp_path / "aligned.fasta"
    output = tmp_path / "tree.nwk"

    with patch(
        "candy.phylogenetics.fasttree.resolve_fasttree_binary", return_value="/usr/bin/fasttree"
    ), patch("candy.phylogenetics.fasttree.run_tool") as mock_run:
        FastTreeBuilder().build_tree(alignment, output)

    args, kwargs = mock_run.call_args
    assert args[0] == ["/usr/bin/fasttree", str(alignment)]
    assert kwargs["stdout_path"] == output
