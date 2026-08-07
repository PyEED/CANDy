"""FASTA parsing and header-formatting utilities.

CANDy encodes taxonomy directly into the FASTA header as
``{accession}_{organism}_{taxonomy_code}`` (e.g. ``P12345_Escherichia_coli_B``)
so that downstream stages (clustering, domain detection, tree annotation) can
recover the organism and kingdom from the sequence ID alone, without carrying
a side table around. ``split_header`` / the ``_`` convention is therefore load
bearing for the rest of the pipeline, exactly as it was in the original
notebook.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

_NON_WORD_RE = re.compile(r"\W+")
_MAX_ORGANISM_LEN = 100


@dataclass(frozen=True)
class FormattedRecord:
    """A sequence with its accession, organism and taxonomy code kept separate."""

    accession: str
    organism: str
    taxonomy_code: str
    sequence: str

    @property
    def header(self) -> str:
        return f"{self.accession}_{self.organism}_{self.taxonomy_code}"

    def to_fasta(self) -> str:
        return f">{self.header}\n{self.sequence}\n"


def count_sequences(fasta_path: str | Path) -> int:
    """Count the number of records in a FASTA file without fully parsing it."""
    count = 0
    with open(fasta_path) as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
    return count


def parse_fasta_to_dict(fasta_path: str | Path) -> dict[str, str]:
    """Return {record_id: sequence} for every record in a FASTA file."""
    with open(fasta_path) as handle:
        return {record.id: str(record.seq) for record in SeqIO.parse(handle, "fasta")}


def _extract_organism(description: str) -> str | None:
    """Pull the organism name out of an NCBI-style '... [Organism name]' description."""
    if "[" not in description:
        return None

    organism = description[description.find("[") + 1 : description.rfind("]")]

    # Handle nested brackets, e.g. "[[Candida] auris]" -> "Candida auris"
    if "[" in organism and "]" in organism:
        organism = organism[organism.find("[") + 1 : organism.find("]")] + organism[organism.find("]") + 1 :]

    organism = organism.replace(" ", "_")
    organism = _NON_WORD_RE.sub("", organism)
    if len(organism) > _MAX_ORGANISM_LEN:
        organism = organism[:_MAX_ORGANISM_LEN]
    return organism.rstrip("_")


def format_records(
    records: Iterable[SeqRecord], taxonomy_dict: Mapping[str, str]
) -> list[FormattedRecord]:
    """Deduplicate by sequence/ID, sanitize headers, and encode taxonomy.

    Mirrors the notebook's ``format_fasta``: records without a recognisable
    ``[Organism]`` tag in their description are dropped, sequences already
    seen (by exact string match) are skipped, and accessions containing ``_``
    have it stripped (since ``_`` is the header field separator).
    """
    seen_sequences: set[str] = set()
    seen_ids: set[str] = set()
    formatted: list[FormattedRecord] = []

    for record in records:
        sequence = str(record.seq)
        if sequence in seen_sequences:
            continue
        if record.id in seen_ids:
            continue

        organism = _extract_organism(record.description)
        if organism is None:
            # No organism annotation to key on; skip, same as the notebook.
            continue

        seen_sequences.add(sequence)
        seen_ids.add(record.id)

        accession = record.id.replace("_", "")
        formatted.append(
            FormattedRecord(
                accession=accession,
                organism=organism,
                taxonomy_code=taxonomy_dict.get(record.id, ""),
                sequence=sequence,
            )
        )

    return formatted


def format_fasta_file(
    input_path: str | Path, output_path: str | Path, taxonomy_dict: Mapping[str, str]
) -> int:
    """Format a FASTA file on disk and write the result. Returns the record count."""
    with open(input_path) as handle:
        records = list(SeqIO.parse(handle, "fasta"))

    formatted = format_records(records, taxonomy_dict)

    with open(output_path, "w") as out:
        for record in formatted:
            out.write(record.to_fasta())

    return len(formatted)


def write_fasta(records: Iterable[tuple[str, str]], output_path: str | Path) -> None:
    """Write an iterable of (header, sequence) pairs as FASTA."""
    with open(output_path, "w") as out:
        for header, sequence in records:
            out.write(f">{header}\n{sequence}\n")


def select_sequences_with_domains(
    fasta_path: str | Path, domain_architecture: Mapping[str, list], is_cazy_query: bool
) -> tuple[str, list[str]]:
    """Keep only sequences that have at least one detected domain.

    Used before MSA/phylogenetics, since undomained sequences add noise to
    the tree without contributing architectural information.

    .. note::
       The notebook recovered each record's bare protein ID via
       ``id[:id.find('.')+2]`` -- a formula that only produces the right
       accession because NCBI version suffixes are almost always a single
       digit (".1", ".2", ...); a double-digit version (".10"+) would be
       truncated wrong. The bare ID is already known directly from how
       ``domain_architecture`` was keyed, so it's reused here instead of
       re-deriving it from the header string.
    """
    ids_without_domains = [pid for pid, hits in domain_architecture.items() if not hits]
    ids_with_domains = {pid for pid, hits in domain_architecture.items() if hits}

    output = ""
    with open(fasta_path) as handle:
        for record in SeqIO.parse(handle, "fasta"):
            identifier = record.id.split("_")[0] if is_cazy_query else record.id
            if identifier in ids_with_domains:
                output += f">{record.id}\n{record.seq}\n"

    return output, ids_without_domains
