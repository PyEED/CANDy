"""BLAST fallback for characterized enzymes without a UniParc entry.

Characterized (experimentally studied) enzymes from CAZy are always
included in the analysis even if they weren't picked up by clustering.
Some of them, however, don't have a UniParc entry, so InterPro can't
annotate them directly; this module BLASTs those sequences against ``nr``
to find a close homolog that *does* have a UniParc entry, and uses that
homolog as a stand-in for domain detection.

.. note::
   The original notebook accumulated BLAST hits from *every* characterized
   sequence processed so far into one shared dict, then re-ran the UniParc
   check against that whole accumulated dict on each iteration -- wasteful
   (repeated, growing InterPro queries), and worse, it could pick up
   UniParc-available accessions left over from a *different* characterized
   sequence's hits while the current sequence had none of its own, at which
   point ``max()`` was called on an empty dict and crashed. This version
   scopes each sequence's BLAST candidates and UniParc check to itself.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from Bio import SeqIO
from Bio.Blast import NCBIWWW, NCBIXML

from candy.interpro import match_lookup

logger = logging.getLogger(__name__)

_EXPECT_THRESHOLD = 5.0
_WORD_SIZE = 6


def _blast_candidates(sequence, identity_threshold: float) -> dict[str, tuple[float, str]]:
    """BLASTP a sequence against nr; returns {accession: (percent_identity, hit_sequence)}."""
    result_handle = NCBIWWW.qblast("blastp", "nr", sequence, expect=_EXPECT_THRESHOLD, word_size=_WORD_SIZE)

    candidates: dict[str, tuple[float, str]] = {}
    for blast_record in NCBIXML.parse(result_handle):
        query_length = blast_record.query_length
        for alignment in blast_record.alignments:
            for hsp in alignment.hsps:
                identity = hsp.identities / query_length * 100
                if identity >= identity_threshold:
                    candidates[alignment.accession] = (round(identity, 2), hsp.sbjct)
    return candidates


def resolve_characterized_via_blast(
    characterized_fasta: str | Path,
    ids_without_uniparc: Sequence[str],
    identity_threshold: float,
) -> tuple[dict[str, str], dict[str, str]]:
    """Find a UniParc-available BLAST homolog for each characterized sequence lacking one.

    Returns ``(chosen_hit_by_id, hit_sequences)``: for each resolved
    characterized ``protein_id``, ``chosen_hit_by_id[protein_id]`` is the
    accession of the best matching homolog, and ``hit_sequences[accession]``
    is that homolog's sequence (to be used in place of the characterized
    sequence for domain detection).
    """
    ids_without_uniparc = set(ids_without_uniparc)
    chosen_hit_by_id: dict[str, str] = {}
    hit_sequences: dict[str, str] = {}

    with open(characterized_fasta) as handle:
        records = list(SeqIO.parse(handle, "fasta"))

    for record in records:
        protein_id = record.id.split("_")[0]
        if protein_id not in ids_without_uniparc:
            continue

        logger.info("Doing a BLASTP search for %s.", protein_id)
        candidates = _blast_candidates(record.seq, identity_threshold)

        if not candidates:
            logger.warning(
                "No BLAST hits above %.0f%% identity for %s; the sequence will be excluded.",
                identity_threshold, protein_id,
            )
            continue

        candidate_sequences = {accession: seq for accession, (_, seq) in candidates.items()}
        matches, _ = match_lookup(candidate_sequences)

        in_uniparc = {
            accession: identity
            for accession, (identity, _) in candidates.items()
            if accession in matches
        }
        if not in_uniparc:
            logger.warning(
                "No UniParc-available BLAST match found for %s; the sequence will be excluded.", protein_id
            )
            continue

        best_accession = max(in_uniparc, key=in_uniparc.get)
        chosen_hit_by_id[protein_id] = best_accession
        hit_sequences[best_accession] = candidates[best_accession][1]
        logger.info(
            "For characterized sequence %s, %s (%.2f%% identical) will be used for domain detection.",
            protein_id, best_accession, in_uniparc[best_accession],
        )

    return chosen_hit_by_id, hit_sequences
