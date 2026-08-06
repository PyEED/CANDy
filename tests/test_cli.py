from typer.testing import CliRunner

from candy.cli import _parse_family, app

runner = CliRunner()


def test_parse_family_no_subfamily():
    assert _parse_family("GH5") == ("GH", 5, None)


def test_parse_family_with_subfamily():
    assert _parse_family("GH5_1") == ("GH", 5, "1")


def test_parse_family_invalid_raises():
    import typer

    try:
        _parse_family("not-a-family")
        assert False, "expected BadParameter"
    except typer.BadParameter:
        pass


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output.lower()


def test_cli_run_help():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--family" in result.output
    assert "--fasta" in result.output


def test_cli_run_requires_family_or_fasta():
    result = runner.invoke(app, ["run", "--jobname", "test"])
    assert result.exit_code != 0


def test_cli_run_rejects_both_family_and_fasta(tmp_path):
    fasta_path = tmp_path / "in.fasta"
    fasta_path.write_text(">a\nMKV\n")
    result = runner.invoke(
        app, ["run", "--jobname", "test", "--family", "GH5", "--fasta", str(fasta_path), "--email", "a@b.com"]
    )
    assert result.exit_code != 0


def test_cli_run_family_without_email_fails():
    result = runner.invoke(app, ["run", "--jobname", "test", "--family", "GH5"])
    assert result.exit_code != 0
