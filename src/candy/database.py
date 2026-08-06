"""SQLite result database, via SQLAlchemy.

The notebook listed SQLAlchemy as a dependency but never actually used it --
the database was built with raw ``sqlite3`` calls. This module replaces that
with real SQLAlchemy models.

While porting the insert logic, the original ``populate_database`` was found
to write ``(id, organism, characterized, taxonomy, sequence, ...)`` into a
table declared as ``(id, taxonomy, characterized, organism_name, sequence,
...)`` -- i.e. the ``taxonomy`` and ``organism_name`` columns were swapped, so
every exported database had organism names (e.g. "Escherichia_coli") stored
under the "taxonomy" column and kingdom codes (e.g. "Bacteria") under
"organism_name". Fixed here; flagged since anyone with tooling built against
the old (mislabeled) column semantics will need to adjust.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from sqlalchemy import String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

logger = logging.getLogger(__name__)

ARCHITECTURE_SEPARATOR = "--"

TAXONOMY_CODE_TO_NAME = {
    "B": "Bacteria",
    "A": "Archaea",
    "E": "Eukaryota",
    "V": "Viruses",
    "U": "Unclassified",
}


class Base(DeclarativeBase):
    pass


class ProteinSequenceRow(Base):
    __tablename__ = "protein_sequences"

    protein_sequence_id: Mapped[str] = mapped_column(String, primary_key=True)
    taxonomy: Mapped[str] = mapped_column(String, default="")
    characterized: Mapped[str] = mapped_column(String, default="")
    organism_name: Mapped[str] = mapped_column(String, default="")
    amino_acid_sequence: Mapped[str] = mapped_column(Text, default="")
    domain_architecture: Mapped[str] = mapped_column(Text, default="")
    domain_locations: Mapped[str] = mapped_column(Text, default="")
    domain_databases: Mapped[str] = mapped_column(Text, default="")


class DomainAssemblyRow(Base):
    __tablename__ = "domain_assemblies"

    protein_domain: Mapped[str] = mapped_column(Text, primary_key=True)
    protein_sequence_ids: Mapped[str] = mapped_column(Text, default="")


class DomainCurationRow(Base):
    __tablename__ = "domain_curation"

    domain_name: Mapped[str] = mapped_column(Text, primary_key=True)
    synonymous_domain_names: Mapped[str] = mapped_column(Text, default="")


def create_database(db_path: str | Path):
    """Create (or open) the SQLite database and return a SQLAlchemy engine."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


def populate_database(
    engine,
    proteins: Sequence,  # Bio.SeqRecord.SeqRecord, id formatted as "{accession}_{organism}_{taxcode}"
    characterized_ids: Mapping[str, str],
    domain_architecture: Mapping[str, Sequence[tuple[list[int], str]]],
    domain_to_database: Mapping[str, Mapping[str, str]],
    curated_domains: Mapping[str, Sequence[str]],
    *,
    is_cazy_query: bool,
) -> None:
    """Populate all three tables from the pipeline's intermediate results.

    ``domain_architecture`` and ``domain_to_database`` are the per-protein
    outputs of :func:`candy.domains.clean_domains` and
    :func:`candy.interpro.build_domain_tables` respectively. ``curated_domains``
    maps an umbrella domain name to the list of raw names folded into it.
    """
    name_to_umbrella = {
        raw_name: umbrella for umbrella, raw_names in curated_domains.items() for raw_name in raw_names
    }

    architecture_to_ids: dict[str, list[str]] = {}
    seen_ids: set[str] = set()
    rows: list[ProteinSequenceRow] = []

    for record in proteins:
        if is_cazy_query:
            protein_id = record.id.split("_")[0]
            organism = " ".join(record.id.split("_")[1:-1])
            taxonomy = TAXONOMY_CODE_TO_NAME.get(record.id[-1], "")
        else:
            protein_id = record.id
            organism = ""
            taxonomy = ""

        if protein_id in seen_ids:
            logger.warning("Skipping duplicate sequence ID: %s", protein_id)
            continue
        seen_ids.add(protein_id)

        domain_names = []
        domain_positions = []
        domain_databases = []
        for position, raw_name in domain_architecture.get(protein_id, []):
            domain_names.append(name_to_umbrella.get(raw_name, raw_name))
            domain_positions.append(str(position))
            domain_databases.append(domain_to_database.get(protein_id, {}).get(raw_name, ""))

        architecture = ARCHITECTURE_SEPARATOR.join(domain_names)
        architecture_to_ids.setdefault(architecture, []).append(protein_id)

        rows.append(
            ProteinSequenceRow(
                protein_sequence_id=protein_id,
                taxonomy=taxonomy,
                characterized="C" if protein_id in characterized_ids else "",
                organism_name=organism,
                amino_acid_sequence=str(record.seq),
                domain_architecture=architecture,
                domain_locations=ARCHITECTURE_SEPARATOR.join(domain_positions),
                domain_databases=ARCHITECTURE_SEPARATOR.join(domain_databases),
            )
        )

    with Session(engine) as session:
        session.add_all(rows)
        session.add_all(
            DomainAssemblyRow(protein_domain=architecture, protein_sequence_ids=", ".join(ids))
            for architecture, ids in architecture_to_ids.items()
        )
        session.add_all(
            DomainCurationRow(domain_name=umbrella, synonymous_domain_names=", ".join(raw_names))
            for umbrella, raw_names in curated_domains.items()
        )
        session.commit()


def read_protein_sequences(engine) -> list[ProteinSequenceRow]:
    with Session(engine) as session:
        return list(session.query(ProteinSequenceRow).all())
