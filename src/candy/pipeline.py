"""End-to-end orchestration of the CANDy pipeline.

Replaces the notebook's implicit, cell-execution-order state (a `go` boolean
gating which cells ran, module-level globals like `family`/`blastchar`
threaded silently between cells) with one explicit function per input mode,
sharing the same downstream stages (domain detection onward).

Digging through the notebook to write this orchestrator surfaced that the
two input modes are *far* less symmetric than they first appear: for a
custom FASTA file, CAZy extraction, UniParc filtering, formatting,
clustering, and characterized-enzyme merging are all skipped entirely --
the uploaded file goes straight into InterPro domain detection. That's
preserved here as two genuinely different code paths that reconverge at
domain detection, rather than threading a boolean through one path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from Bio import SeqIO

from candy import cazy, database, domains, fasta, interpro, itol, merge, network, uniparc
from candy.alignment import get_alignment_tool
from candy.blast import resolve_characterized_via_blast
from candy.clustering import get_clusterer
from candy.config import CAZyFamilyInput, CustomFastaInput, PipelineConfig, Taxonomy
from candy.curation import get_curation_backend
from candy.phylogenetics import get_tree_builder

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    jobname_dir: Path
    database_path: Path
    network_graphml_path: Path
    domain_annotation_path: Path | None
    characterized_annotation_path: Path | None
    alignment_path: Path | None
    tree_path: Path | None
    sequence_count: int


def _accession_with_version(record_id: str) -> str:
    """Recover 'ACCESSION.VERSION' from a header, e.g. 'P12345.1' from 'P12345.1_Org_B'."""
    dot = record_id.find(".")
    return record_id[: dot + 2] if dot != -1 else record_id


def _prepare_domain_detection_input(
    fasta_path: Path,
    is_cazy_query: bool,
    blast_choice: dict[str, str],
    blast_hit_sequences: dict[str, str],
) -> dict[str, str]:
    proteins: dict[str, str] = {}
    with open(fasta_path) as handle:
        for record in SeqIO.parse(handle, "fasta"):
            seq_id = record.id.split("_")[0] if is_cazy_query else record.id
            proteins[seq_id] = (
                blast_hit_sequences[blast_choice[seq_id]] if seq_id in blast_choice else str(record.seq)
            )
    return proteins


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    jobname_dir = config.output_dir / config.jobname
    jobname_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(config.input, CAZyFamilyInput):
        sequences_fasta, taxonomy_dict, characterized_ids, blast_choice, blast_hit_sequences, ec_numbers = (
            _prepare_cazy_query(config, jobname_dir)
        )
        is_cazy_query = True
    elif isinstance(config.input, CustomFastaInput):
        sequences_fasta = config.input.fasta_path
        taxonomy_dict, characterized_ids, blast_choice, blast_hit_sequences, ec_numbers = {}, set(), {}, {}, {}
        is_cazy_query = False
    else:
        raise TypeError(f"Unsupported input type: {type(config.input)}")

    # --- Stage 6: InterPro domain detection ---
    proteins = _prepare_domain_detection_input(sequences_fasta, is_cazy_query, blast_choice, blast_hit_sequences)
    matches, _unmatched = interpro.detect_domains(proteins)
    resolved = interpro.resolve_domain_names(matches)
    position_dict, domain_name_list, name_to_database = interpro.build_domain_tables(resolved)

    # --- Stage 7: resolve overlapping domain hits into a clean architecture ---
    position_to_name = domains.map_positions_to_names(position_dict, domain_name_list)
    domain_architecture = domains.clean_domains(
        position_dict,
        position_to_name,
        name_to_database,
        config.domain_cleaning.database_preference,
        config.domain_cleaning.overlap_percentage / 100,
        config.domain_cleaning.max_domain_length,
    )

    # --- Stage 8: curate synonymous domain names ---
    raw_domain_names = sorted({name for hits in domain_architecture.values() for _, name in hits})
    curation_kwargs = {} if config.curation.backend == "manual" else {"api_key": config.curation.api_key}
    curation_backend = get_curation_backend(config.curation.backend, **curation_kwargs)
    family_label = config.input.family if is_cazy_query else None
    curated_domains = curation_backend.curate(raw_domain_names, family=family_label)

    # --- Stage 9: build the result database ---
    with open(sequences_fasta) as handle:
        protein_records = list(SeqIO.parse(handle, "fasta"))

    db_path = jobname_dir / f"{config.jobname}_db.db"
    engine = database.create_database(db_path)
    database.populate_database(
        engine,
        protein_records,
        characterized_ids=characterized_ids,
        domain_architecture=domain_architecture,
        domain_to_database=name_to_database,
        curated_domains=curated_domains,
        is_cazy_query=is_cazy_query,
    )

    # --- Stage 10: domain co-occurrence network ---
    db_rows = database.read_protein_sequences(engine)
    architectures = {row.protein_sequence_id: row.domain_architecture for row in db_rows}
    graph = network.build_cooccurrence_network(architectures)
    graphml_path = jobname_dir / f"{config.jobname}_domain_cooccurence_network.graphml"
    network.write_graphml(graph, graphml_path)

    alignment_path: Path | None = None
    tree_path: Path | None = None
    domain_annotation_path: Path | None = None
    characterized_annotation_path: Path | None = None

    if config.build_tree:
        # --- Stage 10.5: drop sequences with no detected domain before MSA/PTI ---
        selected_fasta_text, ids_without_domains = fasta.select_sequences_with_domains(
            sequences_fasta, domain_architecture, is_cazy_query
        )
        if ids_without_domains:
            logger.info("Excluding %d sequences with no detected domain from MSA/PTI.", len(ids_without_domains))
        selected_fasta = jobname_dir / f"CAZy_{config.jobname}_inclchar_selected.fasta"
        selected_fasta.write_text(selected_fasta_text)

        # --- Stage 11: MSA ---
        alignment_tool = get_alignment_tool(config.alignment_tool)
        alignment_path = jobname_dir / f"CAZy_{config.jobname}_aligned.fasta"
        alignment_tool.align(selected_fasta, alignment_path)

        # --- Stage 12: phylogenetic tree ---
        tree_builder = get_tree_builder(config.tree_tool)
        tree_path = jobname_dir / f"CAZy_{config.jobname}_phyltree.nwk"
        tree_builder.build_tree(alignment_path, tree_path)

        # --- Stage 13: iTOL annotation files ---
        with open(selected_fasta) as handle:
            selected_records = list(SeqIO.parse(handle, "fasta"))

        domain_annotation_path = jobname_dir / f"iTOL_annotation_CAZy_{config.jobname}.txt"
        domain_annotation_path.write_text(
            itol.build_domain_annotation(config.jobname, domain_architecture, curated_domains, selected_records)
        )

        if is_cazy_query:
            characterized_annotation_path = jobname_dir / f"iTOL_annotation_CAZy_{config.jobname}_characterized.txt"
            characterized_annotation_path.write_text(
                itol.build_characterized_style_annotation(
                    tree_path, sorted(characterized_ids), ec_numbers, family_label
                )
            )

    return PipelineResult(
        jobname_dir=jobname_dir,
        database_path=db_path,
        network_graphml_path=graphml_path,
        domain_annotation_path=domain_annotation_path,
        characterized_annotation_path=characterized_annotation_path,
        alignment_path=alignment_path,
        tree_path=tree_path,
        sequence_count=len(protein_records),
    )


def _prepare_cazy_query(
    config: PipelineConfig, jobname_dir: Path
) -> tuple[Path, dict[str, str], set[str], dict[str, str], dict[str, str], dict[str, str]]:
    cazy_input: CAZyFamilyInput = config.input
    family = cazy_input.family
    taxonomy = cazy_input.taxonomy

    # --- Stage 1: extract CAZy family sequences ---
    fasta_text, taxonomy_dict = cazy.extract_family_sequences(family, taxonomy, cazy_input.email)
    raw_fasta = jobname_dir / f"CAZy_{family}_{taxonomy.value}_FASTA_sequences.fasta"
    raw_fasta.write_text(fasta_text)

    # --- Stage 2: exclude sequences without a UniParc entry ---
    proteins = fasta.parse_fasta_to_dict(raw_fasta)
    available_ids, _unavailable_ids = uniparc.filter_available_in_uniparc(proteins)
    verified_fasta = jobname_dir / f"CAZy_{family}_{taxonomy.value}_Verified_FASTA_sequences.fasta"
    uniparc.write_verified_fasta(raw_fasta, verified_fasta, set(available_ids))

    # --- Stage 3: format FASTA (dedupe, sanitize headers, encode taxonomy) ---
    formatted_fasta = jobname_dir / f"CAZy_{family}_{taxonomy.value}_FASTA_sequences_formatted.fasta"
    fasta.format_fasta_file(verified_fasta, formatted_fasta, taxonomy_dict)

    # --- Stage 4: clustering ---
    clusterer = get_clusterer(config.clustering.software)
    cutoff_label = f"{config.clustering.identity_cutoff}pct"
    clustered_fasta = jobname_dir / f"CAZy_{family}_{taxonomy.value}_formatted_{cutoff_label}.fasta"
    clusterer.cluster(formatted_fasta, clustered_fasta, config.clustering)

    # --- Stage 5: include characterized sequences ---
    characterized_tables = cazy.fetch_characterized_page(family)
    char_ids, char_taxonomy_dict, ec_numbers = cazy.extract_characterized_ids(characterized_tables)
    characterized_fasta_text = cazy.fetch_characterized_sequences(
        char_ids, char_taxonomy_dict, taxonomy, cazy_input.email
    )
    characterized_fasta = jobname_dir / f"Characterized_{family}_{taxonomy.value}_FASTA_sequences.fasta"
    characterized_fasta.write_text(characterized_fasta_text)

    available_id_set = set(available_ids)
    verified_ids: list[str] = []
    ids_without_uniparc: list[str] = []
    with open(characterized_fasta) as handle:
        for record in SeqIO.parse(handle, "fasta"):
            accession = _accession_with_version(record.id)
            if accession in available_id_set:
                verified_ids.append(accession)
            else:
                ids_without_uniparc.append(accession)

    blast_choice, blast_hit_sequences = resolve_characterized_via_blast(
        characterized_fasta, ids_without_uniparc, config.blast_identity_threshold
    )
    verified_ids.extend(blast_choice.keys())

    merged_fasta = jobname_dir / f"CAZy_{family}_{taxonomy.value}_{config.clustering.identity_cutoff}pct_inclchar.fasta"
    merge.merge_characterized_sequences(
        clustered_fasta,
        characterized_fasta,
        merged_fasta,
        verified_ids,
        blast_choice,
        blast_hit_sequences,
    )

    return merged_fasta, taxonomy_dict, set(verified_ids), blast_choice, blast_hit_sequences, ec_numbers
