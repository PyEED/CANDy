"""Command-line entry point: `candy run ...`."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import typer

from candy.config import (
    CAZyFamilyInput,
    ClusteringConfig,
    ClusteringSoftware,
    CurationConfig,
    CustomFastaInput,
    DomainCleaningConfig,
    PipelineConfig,
    Taxonomy,
)
from candy.pipeline import run_pipeline

app = typer.Typer(help="CANDy: automated analysis of domain architectures in carbohydrate-active enzymes.")

_FAMILY_RE = re.compile(r"^([A-Za-z]+)(\d+)(?:_(\d+))?$")


@app.callback()
def _main() -> None:
    """CANDy: automated analysis of domain architectures in carbohydrate-active enzymes.

    A no-op callback: Typer collapses a Typer() app with exactly one
    @app.command() into a single top-level command (dropping the command
    name entirely), which would silently break `candy run ...`. Registering
    this callback keeps `run` as a real, required subcommand.
    """


def _parse_family(family: str) -> tuple[str, int, str | None]:
    match = _FAMILY_RE.match(family)
    if not match:
        raise typer.BadParameter(
            f"Could not parse '{family}' as a CAZy family (expected e.g. 'GH5' or 'GH5_1')."
        )
    enzyme_class, number, subfamily = match.groups()
    return enzyme_class, int(number), subfamily


@app.command()
def run(
    jobname: str = typer.Option(..., help="Job name; results are written to output-dir/jobname."),
    family: Optional[str] = typer.Option(
        None, help="CAZy family to query, e.g. 'GH5' or 'GH5_1'. Mutually exclusive with --fasta."
    ),
    fasta: Optional[Path] = typer.Option(
        None, exists=True, help="Custom FASTA file to analyse instead of querying CAZy."
    ),
    email: Optional[str] = typer.Option(None, help="Email for NCBI Entrez. Required with --family."),
    taxonomy: Taxonomy = typer.Option(Taxonomy.ALL, help="Taxonomic subset to restrict a --family query to."),
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
    build_tree: bool = typer.Option(False, "--tree/--no-tree", help="Run MSA + phylogenetics + iTOL export."),
    curation_backend: str = typer.Option(
        "manual", help="Domain-name curation backend: 'manual' or 'gemini'."
    ),
    curation_api_key: Optional[str] = typer.Option(
        None, envvar="GOOGLE_API_KEY", help="API key for the curation backend, if it needs one."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run the CANDy pipeline end-to-end."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")

    if (family is None) == (fasta is None):
        raise typer.BadParameter("Specify exactly one of --family or --fasta.")

    if family is not None:
        if not email:
            raise typer.BadParameter("--email is required when using --family (NCBI Entrez requires it).")
        enzyme_class, family_number, subfamily = _parse_family(family)
        pipeline_input = CAZyFamilyInput(
            enzyme_class=enzyme_class,
            family_number=family_number,
            subfamily=subfamily,
            email=email,
            taxonomy=taxonomy,
        )
    else:
        pipeline_input = CustomFastaInput(fasta_path=fasta)

    config = PipelineConfig(
        input=pipeline_input,
        jobname=jobname,
        output_dir=output_dir,
        clustering=ClusteringConfig(software=clustering_software, identity_cutoff=cluster_identity),
        domain_cleaning=DomainCleaningConfig(
            max_domain_length=max_domain_length, overlap_percentage=overlap_percentage
        ),
        curation=CurationConfig(backend=curation_backend, api_key=curation_api_key),
        blast_identity_threshold=blast_identity,
        build_tree=build_tree,
    )

    result = run_pipeline(config)

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
