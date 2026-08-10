"""Command-line entry point: `candy GH173` / `candy my_sequences.fasta`."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Optional

import typer

from candy.config import (
    DEFAULT_DATABASE_PREFERENCE,
    CAZyFamilyInput,
    ClusteringConfig,
    ClusteringSoftware,
    CurationConfig,
    CustomFastaInput,
    DomainCleaningConfig,
    PipelineConfig,
    Taxonomy,
    reorder_database_preference,
)
from candy.pipeline import run_pipeline

app = typer.Typer(
    help="CANDy: automated analysis of domain architectures in carbohydrate-active enzymes.",
    add_completion=False,
)

_FAMILY_RE = re.compile(r"^([A-Za-z]+)(\d+)(?:_(\d+))?$")
_SANITIZE_RE = re.compile(r"\W+")


def _try_parse_family(value: str) -> tuple[str, int, str | None] | None:
    match = _FAMILY_RE.match(value)
    if not match:
        return None
    enzyme_class, number, subfamily = match.groups()
    return enzyme_class, int(number), subfamily


def _sanitize_jobname(value: str) -> str:
    return _SANITIZE_RE.sub("", "".join(value.split()))


@app.command()
def main(
    target: str = typer.Argument(
        ..., help="CAZy family to query (e.g. 'GH173' or 'GH5_1'), or a path to a custom FASTA file."
    ),
    jobname: Optional[str] = typer.Option(
        None, help="Job name; results are written to output-dir/jobname. Defaults to TARGET."
    ),
    email: Optional[str] = typer.Option(
        None,
        envvar="CANDY_EMAIL",
        help="Email for NCBI Entrez (required for CAZy family queries, NCBI policy). "
        "Falls back to the CANDY_EMAIL environment variable, then an interactive prompt.",
    ),
    taxonomy: Taxonomy = typer.Option(Taxonomy.ALL, help="Taxonomic subset to restrict a family query to."),
    output_dir: Path = typer.Option(Path("."), help="Directory results are written under."),
    clustering_software: ClusteringSoftware = typer.Option(
        ClusteringSoftware.MMSEQS2, help="Sequence clustering backend."
    ),
    cluster_identity: int = typer.Option(85, help="Clustering identity cutoff, percent."),
    blast_identity: int = typer.Option(
        95, help="Minimum identity for the characterized-enzyme BLAST fallback, percent."
    ),
    max_domain_length: int = typer.Option(800, help="Maximum plausible domain length, amino acids."),
    overlap_percentage: int = typer.Option(
        20, help="Overlap threshold above which two hits are considered the same domain, percent."
    ),
    db_preference: Optional[str] = typer.Option(
        None,
        "--db-preference",
        help="Comma-separated InterPro member-database names to prioritize when two databases "
        "disagree on a domain boundary, e.g. 'PFAM,SMART'. Named databases move to the front in "
        "the given order; unlisted ones keep their default relative order after. Valid names: "
        + ", ".join(DEFAULT_DATABASE_PREFERENCE) + ".",
    ),
    build_tree: bool = typer.Option(False, "--tree/--no-tree", help="Run MSA + phylogenetics + iTOL export."),
    alignment_tool: Optional[str] = typer.Option(
        None,
        help="MSA backend: 'famsa' (default; bundled, no setup needed) or 'mafft' (must be installed "
        "separately and be on PATH -- not available via CANDy's conda environment.yml, which has no "
        "macOS arm64 build for it; see README).",
    ),
    tree_tool: Optional[str] = typer.Option(
        None,
        help="Phylogenetics backend: 'veryfasttree' or 'fasttree'. Defaults to 'veryfasttree', except "
        "on a Mac where it has no working native build (Apple Silicon, or Rosetta translation), where "
        "it defaults to 'fasttree' instead (needs the conda environment; see README).",
    ),
    curation_backend: str = typer.Option(
        "manual", help="Domain-name curation backend: 'manual' or 'gemini'."
    ),
    curation_api_key: Optional[str] = typer.Option(
        None, envvar="GOOGLE_API_KEY", help="API key for the curation backend, if it needs one."
    ),
    curation_model: Optional[str] = typer.Option(
        None,
        help="Model name for the curation backend, if it needs one (e.g. a Gemini model name). "
        "Defaults to the backend's own default. Useful to override without a code change if a "
        "provider deprecates/renames their default model.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run the CANDy pipeline end-to-end.

    TARGET is either a CAZy family code ('GH173', 'GH5_1', ...) or a path to
    a FASTA file -- whichever it looks like determines the input mode, e.g.:

        candy GH173 --email you@example.com --tree

        candy my_sequences.fasta --tree
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    target_path = Path(target)
    if target_path.is_file():
        pipeline_input: CAZyFamilyInput | CustomFastaInput = CustomFastaInput(fasta_path=target_path)
        default_jobname = target_path.stem
    else:
        parsed = _try_parse_family(target)
        if parsed is None:
            raise typer.BadParameter(
                f"'{target}' is neither an existing FASTA file nor a valid CAZy family code "
                "(expected e.g. 'GH5' or 'GH5_1')."
            )
        enzyme_class, family_number, subfamily = parsed

        if not email:
            if sys.stdin.isatty():
                email = typer.prompt("NCBI Entrez requires an email address")
            else:
                raise typer.BadParameter(
                    "An email is required for CAZy family queries (NCBI Entrez policy). "
                    "Pass --email, or set the CANDY_EMAIL environment variable."
                )

        pipeline_input = CAZyFamilyInput(
            enzyme_class=enzyme_class,
            family_number=family_number,
            subfamily=subfamily,
            email=email,
            taxonomy=taxonomy,
        )
        default_jobname = target

    if db_preference:
        try:
            database_preference = reorder_database_preference(db_preference.split(","))
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
    else:
        database_preference = list(DEFAULT_DATABASE_PREFERENCE)

    tool_kwargs = {}
    if alignment_tool:
        tool_kwargs["alignment_tool"] = alignment_tool
    if tree_tool:
        tool_kwargs["tree_tool"] = tree_tool

    config = PipelineConfig(
        input=pipeline_input,
        jobname=_sanitize_jobname(jobname or default_jobname),
        output_dir=output_dir,
        clustering=ClusteringConfig(software=clustering_software, identity_cutoff=cluster_identity),
        domain_cleaning=DomainCleaningConfig(
            max_domain_length=max_domain_length,
            overlap_percentage=overlap_percentage,
            database_preference=database_preference,
        ),
        curation=CurationConfig(backend=curation_backend, api_key=curation_api_key, model=curation_model),
        blast_identity_threshold=blast_identity,
        build_tree=build_tree,
        **tool_kwargs,
    )

    try:
        result = run_pipeline(config)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"\nDone. Results written to {result.jobname_dir}")
    typer.echo(f"  Database:              {result.database_path}")
    typer.echo(f"  Co-occurrence network: {result.network_graphml_path}")
    if result.tree_path:
        typer.echo(f"  Alignment:             {result.alignment_path}")
        typer.echo(f"  Tree:                  {result.tree_path}")
        typer.echo(f"  Domain annotation:     {result.domain_annotation_path}")
        if result.characterized_annotation_path:
            typer.echo(f"  Characterized annotation: {result.characterized_annotation_path}")


if __name__ == "__main__":
    app()
