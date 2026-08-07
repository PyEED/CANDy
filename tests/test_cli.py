import re

from typer.testing import CliRunner

from candy.cli import _sanitize_jobname, _try_parse_family, app

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain_text(output: str) -> str:
    """Strip ANSI color codes and box-drawing characters from Typer's Rich-rendered output.

    Whether Rich colorizes its error panels depends on how it detects the
    terminal (observed to differ between a local shell and a CI runner, even
    on identical typer/rich versions) -- when it does, the color codes can
    land mid-word at a wrapped line boundary, splitting a phrase that should
    otherwise be a contiguous substring. Stripping them makes assertions
    robust to that regardless of environment.
    """
    text = _ANSI_RE.sub("", output)
    for border_char in "─│┌┐└┘":
        text = text.replace(border_char, " ")
    return " ".join(text.split())


def test_try_parse_family_no_subfamily():
    assert _try_parse_family("GH5") == ("GH", 5, None)


def test_try_parse_family_with_subfamily():
    assert _try_parse_family("GH5_1") == ("GH", 5, "1")


def test_try_parse_family_invalid_returns_none():
    assert _try_parse_family("not-a-family") is None


def test_sanitize_jobname_strips_whitespace_and_special_chars():
    assert _sanitize_jobname(" my job! ") == "myjob"


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "TARGET" in result.output or "target" in result.output.lower()


def test_cli_bare_invocation_is_candy_target_no_subcommand_needed():
    # `candy GH5` should work directly -- no `run` subcommand required.
    result = runner.invoke(app, ["not-a-real-family-and-not-a-file"])
    normalized = _plain_text(result.output)
    assert result.exit_code != 0
    assert "neither an existing FASTA file" in normalized
    assert "valid CAZy family code" in normalized


def test_cli_family_query_without_email_and_non_interactive_fails():
    result = runner.invoke(app, ["GH5"], input="")
    assert result.exit_code != 0
    assert "email" in result.output.lower()


def test_cli_fasta_target_autodetected(tmp_path, monkeypatch):
    fasta_path = tmp_path / "my_seqs.fasta"
    fasta_path.write_text(">a\nMKV\n")

    captured = {}

    def fake_run_pipeline(config):
        captured["config"] = config
        from candy.pipeline import PipelineResult

        return PipelineResult(
            jobname_dir=tmp_path / "out",
            database_path=tmp_path / "out" / "db.db",
            network_graphml_path=tmp_path / "out" / "net.graphml",
            domain_annotation_path=None,
            characterized_annotation_path=None,
            alignment_path=None,
            tree_path=None,
            sequence_count=1,
        )

    monkeypatch.setattr("candy.cli.run_pipeline", fake_run_pipeline)

    result = runner.invoke(app, [str(fasta_path)])

    assert result.exit_code == 0, result.output
    from candy.config import CustomFastaInput

    assert isinstance(captured["config"].input, CustomFastaInput)
    assert captured["config"].jobname == _sanitize_jobname(fasta_path.stem)


def test_cli_family_target_autodetected_with_email_flag(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(config):
        captured["config"] = config
        from candy.pipeline import PipelineResult

        return PipelineResult(
            jobname_dir=tmp_path / "out",
            database_path=tmp_path / "out" / "db.db",
            network_graphml_path=tmp_path / "out" / "net.graphml",
            domain_annotation_path=None,
            characterized_annotation_path=None,
            alignment_path=None,
            tree_path=None,
            sequence_count=1,
        )

    monkeypatch.setattr("candy.cli.run_pipeline", fake_run_pipeline)

    result = runner.invoke(app, ["GH173", "--email", "you@example.com"])

    assert result.exit_code == 0, result.output
    from candy.config import CAZyFamilyInput

    config_input = captured["config"].input
    assert isinstance(config_input, CAZyFamilyInput)
    assert config_input.family == "GH173"
    assert config_input.email == "you@example.com"
    assert captured["config"].jobname == "GH173"


def test_cli_email_falls_back_to_env_var(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(config):
        captured["config"] = config
        from candy.pipeline import PipelineResult

        return PipelineResult(
            jobname_dir=tmp_path / "out",
            database_path=tmp_path / "out" / "db.db",
            network_graphml_path=tmp_path / "out" / "net.graphml",
            domain_annotation_path=None,
            characterized_annotation_path=None,
            alignment_path=None,
            tree_path=None,
            sequence_count=1,
        )

    monkeypatch.setattr("candy.cli.run_pipeline", fake_run_pipeline)
    monkeypatch.setenv("CANDY_EMAIL", "env@example.com")

    result = runner.invoke(app, ["GH173"])

    assert result.exit_code == 0, result.output
    assert captured["config"].input.email == "env@example.com"


def test_cli_explicit_jobname_overrides_default(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(config):
        captured["config"] = config
        from candy.pipeline import PipelineResult

        return PipelineResult(
            jobname_dir=tmp_path / "out",
            database_path=tmp_path / "out" / "db.db",
            network_graphml_path=tmp_path / "out" / "net.graphml",
            domain_annotation_path=None,
            characterized_annotation_path=None,
            alignment_path=None,
            tree_path=None,
            sequence_count=1,
        )

    monkeypatch.setattr("candy.cli.run_pipeline", fake_run_pipeline)

    result = runner.invoke(app, ["GH173", "--email", "you@example.com", "--jobname", "custom_name"])

    assert result.exit_code == 0, result.output
    assert captured["config"].jobname == "custom_name"


def _fake_pipeline_result(tmp_path):
    from candy.pipeline import PipelineResult

    return PipelineResult(
        jobname_dir=tmp_path / "out",
        database_path=tmp_path / "out" / "db.db",
        network_graphml_path=tmp_path / "out" / "net.graphml",
        domain_annotation_path=None,
        characterized_annotation_path=None,
        alignment_path=None,
        tree_path=None,
        sequence_count=1,
    )


def test_cli_db_preference_reorders_default(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(config):
        captured["config"] = config
        return _fake_pipeline_result(tmp_path)

    monkeypatch.setattr("candy.cli.run_pipeline", fake_run_pipeline)

    result = runner.invoke(
        app, ["GH173", "--email", "you@example.com", "--db-preference", "PFAM,SMART"]
    )

    assert result.exit_code == 0, result.output
    preference = captured["config"].domain_cleaning.database_preference
    assert preference[:2] == ["PFAM", "SMART"]
    assert "CDD" in preference  # untouched entries still present


def test_cli_db_preference_unknown_name_is_a_clean_error(tmp_path, monkeypatch):
    monkeypatch.setattr("candy.cli.run_pipeline", lambda config: _fake_pipeline_result(tmp_path))

    result = runner.invoke(
        app, ["GH173", "--email", "you@example.com", "--db-preference", "NOTAREALDB"]
    )

    assert result.exit_code != 0
    assert "Unknown database name" in _plain_text(result.output)


def test_cli_pipeline_value_error_is_reported_cleanly_without_a_traceback(monkeypatch):
    # Regression test: a ValueError from run_pipeline (e.g. an unknown CAZy
    # family) used to propagate as a raw traceback. It should now print a
    # one-line "Error: ..." message and exit non-zero, no traceback.
    def fake_run_pipeline(config):
        raise ValueError("CAZy family 'GH999' not found (... returned 404). Check the family code.")

    monkeypatch.setattr("candy.cli.run_pipeline", fake_run_pipeline)

    result = runner.invoke(app, ["GH999", "--email", "you@example.com"])

    assert result.exit_code == 1
    assert "Error: CAZy family 'GH999' not found" in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_cli_no_db_preference_uses_default_order(tmp_path, monkeypatch):
    from candy.config import DEFAULT_DATABASE_PREFERENCE

    captured = {}

    def fake_run_pipeline(config):
        captured["config"] = config
        return _fake_pipeline_result(tmp_path)

    monkeypatch.setattr("candy.cli.run_pipeline", fake_run_pipeline)

    result = runner.invoke(app, ["GH173", "--email", "you@example.com"])

    assert result.exit_code == 0, result.output
    assert captured["config"].domain_cleaning.database_preference == DEFAULT_DATABASE_PREFERENCE
