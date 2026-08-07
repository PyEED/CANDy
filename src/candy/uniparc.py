"""Filter sequences down to those with a UniParc entry.

InterPro's domain databases key off UniParc, so a sequence without a UniParc
entry can never get a domain annotation. Filtering these out early avoids
wasting the (slower, rate-limited) domain-detection step on sequences that
are guaranteed to come back empty.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

from Bio import SeqIO

from candy.interpro import match_lookup

logger = logging.getLogger(__name__)


def filter_available_in_uniparc(proteins: Mapping[str, str]) -> tuple[list[str], list[str]]:
    """Return (ids with a UniParc entry, ids without one) for ``{id: sequence}``."""
    matches, unmatched = match_lookup(proteins)
    available_ids = list(matches.keys())

    logger.info(
        "%d of %d sequences have a UniParc entry and will be included.",
        len(available_ids),
        len(available_ids) + len(unmatched),
    )
    if unmatched:
        logger.info("%d sequences have no UniParc entry and will be excluded.", len(unmatched))

    return available_ids, unmatched


def write_verified_fasta(input_path: str | Path, output_path: str | Path, available_ids: set[str]) -> int:
    """Write only records whose id is in ``available_ids`` and aren't marked 'partial'.

    Returns the number of sequences written.
    """
    written = 0
    partial_count = 0

    with open(input_path) as handle, open(output_path, "w") as out:
        for record in SeqIO.parse(handle, "fasta"):
            if "partial" in record.description:
                partial_count += 1
                continue
            if record.id in available_ids:
                out.write(f">{record.description}\n{record.seq}\n")
                written += 1

    if partial_count:
        logger.info("%d partial sequences excluded from the analysis.", partial_count)

    return written
