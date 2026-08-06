from pathlib import Path
from types import SimpleNamespace
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


def test_mmseqs2_runs_individual_steps_and_copies_result(tmp_path):
    from candy.clustering.mmseqs2 import Mmseqs2Clusterer

    config = ClusteringConfig(identity_cutoff=85, mmseqs_min_coverage=90, mmseqs_cov_mode=0)
    input_fasta = tmp_path / "in.fasta"
    input_fasta.write_text(">seq\nMKV\n")
    output_fasta = tmp_path / "out.fasta"

    calls = []

    def fake_run_tool(args, **kwargs):
        calls.append(args)
        cwd = Path(kwargs["cwd"])
        # mimic convert2fasta writing the final representative-sequence FASTA
        if args[1] == "convert2fasta":
            (cwd / "cluster_rep_seq.fasta").write_text(">rep\nMKV\n")
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    with patch("candy.clustering.mmseqs2.resolve_mmseqs2_binary", return_value="/usr/bin/mmseqs"), patch(
        "candy.clustering.mmseqs2.run_tool", side_effect=fake_run_tool
    ):
        Mmseqs2Clusterer().cluster(input_fasta, output_fasta, config)

    subcommands = [call[1] for call in calls]
    assert subcommands == ["createdb", "cluster", "result2repseq", "convert2fasta"]
    # only the shell-dependent `cluster` step uses the shell-capable binary;
    # everything else runs the plain binary directly (no shell involved)
    assert calls[0][0] == "/usr/bin/mmseqs"  # createdb
    assert calls[1][0] == "/usr/bin/mmseqs"  # cluster (shell binary, same path here since no .bat)
    assert calls[0][2] == "input.fasta"  # relative filename, not an absolute path with spaces

    cluster_call = calls[1]
    assert "--min-seq-id" in cluster_call and cluster_call[cluster_call.index("--min-seq-id") + 1] == "0.85"
    assert output_fasta.read_text() == ">rep\nMKV\n"


def test_mmseqs2_uses_plain_exe_directly_for_non_shell_steps_on_windows(tmp_path):
    """The cluster step goes through mmseqs.bat; createdb/result2repseq/convert2fasta bypass it."""
    from candy.clustering.mmseqs2 import Mmseqs2Clusterer

    bat_path = tmp_path / "mmseqs" / "mmseqs.bat"
    exe_path = tmp_path / "mmseqs" / "bin" / "mmseqs.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("fake exe")
    bat_path.write_text("fake bat")

    config = ClusteringConfig(identity_cutoff=85)
    input_fasta = tmp_path / "in.fasta"
    input_fasta.write_text(">seq\nMKV\n")
    output_fasta = tmp_path / "out.fasta"

    calls = []

    def fake_run_tool(args, **kwargs):
        calls.append(args)
        cwd = Path(kwargs["cwd"])
        if args[1] == "convert2fasta":
            (cwd / "cluster_rep_seq.fasta").write_text(">rep\nMKV\n")
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    with patch("candy.clustering.mmseqs2.resolve_mmseqs2_binary", return_value=str(bat_path)), patch(
        "candy.clustering.mmseqs2.platform.system", return_value="Windows"
    ), patch("candy.clustering.mmseqs2.run_tool", side_effect=fake_run_tool):
        Mmseqs2Clusterer().cluster(input_fasta, output_fasta, config)

    binaries_used = [call[0] for call in calls]
    assert binaries_used == [str(exe_path), str(bat_path), str(exe_path), str(exe_path)]


def test_mmseqs2_raises_clear_error_when_output_missing_despite_success_exit_code(tmp_path):
    """Regression test: mmseqs.bat always exits 0 on Windows even on internal failure."""
    from candy.clustering.mmseqs2 import Mmseqs2Clusterer
    from candy.external_tools import ExternalToolError

    config = ClusteringConfig(identity_cutoff=85)
    input_fasta = tmp_path / "in.fasta"
    input_fasta.write_text(">seq\nMKV\n")
    output_fasta = tmp_path / "out.fasta"

    def fake_run_tool(args, **kwargs):
        # everything "succeeded" (no exception) but never actually produced output
        return SimpleNamespace(stdout="some diagnostic output", stderr="", returncode=0)

    with patch("candy.clustering.mmseqs2.resolve_mmseqs2_binary", return_value="/usr/bin/mmseqs"), patch(
        "candy.clustering.mmseqs2.run_tool", side_effect=fake_run_tool
    ):
        try:
            Mmseqs2Clusterer().cluster(input_fasta, output_fasta, config)
            assert False, "expected ExternalToolError"
        except ExternalToolError as exc:
            assert "did not produce the expected output" in str(exc)
            assert "some diagnostic output" in str(exc)
