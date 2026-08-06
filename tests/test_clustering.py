from unittest.mock import patch

from candy.config import ClusteringConfig, ClusteringSoftware
from candy.clustering import get_clusterer


def test_get_clusterer_returns_expected_implementation():
    assert get_clusterer(ClusteringSoftware.CDHIT).name == "cd-hit"
    assert get_clusterer(ClusteringSoftware.MMSEQS2).name == "mmseqs2"


def test_cdhit_builds_expected_command(tmp_path):
    from candy.clustering.cdhit import CdHitClusterer

    config = ClusteringConfig(identity_cutoff=85, cdhit_min_short_coverage=90, cdhit_min_long_coverage=90)
    input_fasta = tmp_path / "in.fasta"
    output_fasta = tmp_path / "out.fasta"

    with patch("candy.clustering.cdhit.require_binary", return_value="/usr/bin/cd-hit"), patch(
        "candy.clustering.cdhit.run_tool"
    ) as mock_run:
        CdHitClusterer().cluster(input_fasta, output_fasta, config)

    args = mock_run.call_args[0][0]
    assert args[0] == "/usr/bin/cd-hit"
    assert "-c" in args and args[args.index("-c") + 1] == "0.85"
    assert "-aL" in args and args[args.index("-aL") + 1] == "0.9"
    assert "-aS" in args and args[args.index("-aS") + 1] == "0.9"
    assert "-i" in args and args[args.index("-i") + 1] == str(input_fasta)
    assert "-o" in args and args[args.index("-o") + 1] == str(output_fasta)


def test_mmseqs2_builds_expected_command_and_copies_result(tmp_path):
    from candy.clustering.mmseqs2 import Mmseqs2Clusterer

    config = ClusteringConfig(identity_cutoff=85, mmseqs_min_coverage=90, mmseqs_cov_mode=0)
    input_fasta = tmp_path / "in.fasta"
    output_fasta = tmp_path / "out.fasta"

    def fake_run_tool(args, **kwargs):
        # mimic mmseqs2 easy-cluster writing its representative-sequence output
        prefix = args[3]
        with open(f"{prefix}_rep_seq.fasta", "w") as f:
            f.write(">rep\nMKV\n")

    with patch("candy.clustering.mmseqs2.require_binary", return_value="/usr/bin/mmseqs"), patch(
        "candy.clustering.mmseqs2.run_tool", side_effect=fake_run_tool
    ) as mock_run:
        Mmseqs2Clusterer().cluster(input_fasta, output_fasta, config)

    args = mock_run.call_args[0][0]
    assert args[0] == "/usr/bin/mmseqs"
    assert args[1] == "easy-cluster"
    assert "--min-seq-id" in args and args[args.index("--min-seq-id") + 1] == "0.85"
    assert output_fasta.read_text() == ">rep\nMKV\n"
