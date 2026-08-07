"""Pluggable sequence-clustering backends.

CANDy reduces redundancy in the input set before domain detection, since it
cares about domain *architectures* rather than exact sequence identity, so a
fairly permissive clustering cutoff is typically used. Both tools the
published notebook offered (CD-HIT and MMseqs2) are kept as interchangeable
:class:`Clusterer` implementations; adding another tool later only means
implementing this protocol.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from candy.config import ClusteringConfig, ClusteringSoftware


class Clusterer(Protocol):
    name: str

    def cluster(self, input_fasta: Path, output_fasta: Path, config: ClusteringConfig) -> Path:
        """Cluster ``input_fasta`` and write representative sequences to ``output_fasta``."""
        ...


def get_clusterer(software: ClusteringSoftware) -> Clusterer:
    if software == ClusteringSoftware.CDHIT:
        from candy.clustering.cdhit import CdHitClusterer

        return CdHitClusterer()
    if software == ClusteringSoftware.MMSEQS2:
        from candy.clustering.mmseqs2 import Mmseqs2Clusterer

        return Mmseqs2Clusterer()
    raise ValueError(f"Unknown clustering software: {software}")
