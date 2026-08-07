"""Merge clustered sequences with characterized enzymes into one FASTA file.

Characterized (experimentally studied) enzymes must always be present in
the final analysis, even if clustering discarded them as redundant. This
drops any clustered copy of a characterized sequence and re-adds the
characterized version instead (using its BLAST-homolog stand-in sequence
when the original had no UniParc entry, see :mod:`candy.blast`), so each
characterized enzyme appears exactly once, correctly annotated.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from Bio import SeqIO


def _protein_id_for_merge(record_id: str) -> str:
    """Recover the bare protein ID from a FASTA record id for merge-matching purposes.

    Ported as-is from the notebook's characterized-enzyme merge cell, which
    used a subtly different rule than the one in ``itol.py``: any ``_`` found
    at position 0-2 joins the first two underscore-separated segments, and
    only a literal absence of ``_`` falls back to the id verbatim.
    """
    first_underscore = record_id.find("_")
    if first_underscore > 2:
        return record_id.split("_")[0]
    if first_underscore != -1:
        parts = record_id.split("_")
        return f"{parts[0]}_{parts[1]}"
    return record_id


def merge_characterized_sequences(
    clustered_fasta: str | Path,
    characterized_fasta: str | Path,
    output_fasta: str | Path,
    verified_ids: Sequence[str],
    blast_choice: Mapping[str, str],
    blast_hit_sequences: Mapping[str, str],
) -> Path:
    """Write ``output_fasta`` = clustered sequences (minus characterized duplicates) + characterized sequences."""
    verified_id_set = set(verified_ids)

    with open(output_fasta, "w") as out:
        with open(clustered_fasta) as handle:
            for record in SeqIO.parse(handle, "fasta"):
                if _protein_id_for_merge(record.id) not in verified_id_set:
                    SeqIO.write(record, out, "fasta")

        characterized_output = ""
        with open(characterized_fasta) as handle:
            for record in SeqIO.parse(handle, "fasta"):
                protein_id = _protein_id_for_merge(record.id)
                if protein_id not in verified_id_set:
                    continue

                accession = protein_id.replace("_", "")
                if record.id.find("_") > 2:
                    description = "_".join(record.id.split("_", 1)[1:])
                else:
                    description = "_".join(record.id.split("_", 2)[2:])

                if protein_id in blast_choice:
                    sequence = blast_hit_sequences[blast_choice[protein_id]]
                else:
                    sequence = str(record.seq)

                # `description` (everything after the accession) already ends
                # in "_{taxcode}", since candy.cazy.fetch_characterized_sequences
                # writes characterized-enzyme headers as accession_organism_taxcode.
                # The original notebook re-appended `taxonomydict[proteinidentifier]`
                # here regardless, duplicating the code (e.g. "..._coli_B_B") and
                # corrupting the organism name derived from it downstream.
                characterized_output += f">{accession}_{description}\n{sequence}\n"

        out.write(characterized_output)

    return Path(output_fasta)
