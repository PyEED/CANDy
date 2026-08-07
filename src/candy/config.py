"""Explicit, testable run configuration.

The original Colab notebook collected these parameters through ``ipywidgets``
dropdowns and blocking ``input()`` calls, and threaded them through the
pipeline as module-level globals (``family``, ``go``, ``jobname``, ...) that
later cells silently depended on. Here they are collected into plain
dataclasses that can be constructed directly (Python API), parsed from CLI
flags, or built in a test without touching stdin.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Taxonomy(str, Enum):
    ALL = "All"
    ARCHAEA = "Archaea"
    BACTERIA = "Bacteria"
    EUKARYOTA = "Eukaryota"
    VIRUSES = "Viruses"
    UNCLASSIFIED = "Unclassified"

    @property
    def code(self) -> str:
        """Single-letter code used throughout CAZy/CANDy output, e.g. 'B' for Bacteria."""
        return {
            Taxonomy.ALL: "All",
            Taxonomy.ARCHAEA: "A",
            Taxonomy.BACTERIA: "B",
            Taxonomy.EUKARYOTA: "E",
            Taxonomy.VIRUSES: "V",
            Taxonomy.UNCLASSIFIED: "U",
        }[self]


class ClusteringSoftware(str, Enum):
    CDHIT = "cd-hit"
    MMSEQS2 = "mmseqs2"


# Default ranking (lower = higher priority) used to resolve overlapping domain
# annotations sourced from different InterPro member databases. Mirrors the
# notebook's default so results are reproducible across the rewrite.
DEFAULT_DATABASE_PREFERENCE: list[str] = [
    "SMART",
    "CDD",
    "PFAM",
    "SUPERFAMILY",
    "NCBIFAM",
    "PANTHER",
    "GENE3D",
    "PIRSF",
    "HAMAP",
    "PRINTS",
    "SFLD",
    "PROFILE",
    "PROSITE",
]


def reorder_database_preference(
    priority: Sequence[str], base: Sequence[str] = DEFAULT_DATABASE_PREFERENCE
) -> list[str]:
    """Move the named databases (in the given order) to the front of ``base``.

    Databases not named in ``priority`` keep their existing relative order,
    appended after the ones that were moved -- so callers only need to name
    the databases they actually want to reprioritize, not repeat the full
    13-item list every time.

    Raises:
        ValueError: if ``priority`` contains a name not present in ``base``.
    """
    normalized_priority = [name.strip().upper() for name in priority]
    valid = set(base)
    unknown = [name for name in normalized_priority if name not in valid]
    if unknown:
        raise ValueError(
            f"Unknown database name(s): {', '.join(unknown)}. Valid names: {', '.join(base)}."
        )

    front: list[str] = []
    seen: set[str] = set()
    for name in normalized_priority:
        if name not in seen:
            front.append(name)
            seen.add(name)

    rest = [name for name in base if name not in seen]
    return front + rest


@dataclass
class CAZyFamilyInput:
    """Query a CAZy family/subfamily directly (input option 1 in the notebook)."""

    enzyme_class: str  # "GH", "GT", "PL", "CE", "AA"
    family_number: int
    email: str
    subfamily: str | None = None
    taxonomy: Taxonomy = Taxonomy.ALL

    @property
    def family(self) -> str:
        base = f"{self.enzyme_class}{self.family_number}"
        return f"{base}_{self.subfamily}" if self.subfamily else base


@dataclass
class CustomFastaInput:
    """Analyse a user-supplied FASTA file directly (input option 2 in the notebook)."""

    fasta_path: Path

    def __post_init__(self) -> None:
        self.fasta_path = Path(self.fasta_path)


@dataclass
class ClusteringConfig:
    software: ClusteringSoftware = ClusteringSoftware.MMSEQS2
    identity_cutoff: int = 85  # percent

    # CD-HIT specific
    cdhit_min_short_coverage: int = 90  # -aS, percent
    cdhit_min_long_coverage: int = 90  # -aL, percent

    # MMseqs2 specific
    mmseqs_cov_mode: int = 0
    mmseqs_min_coverage: int = 90  # percent


@dataclass
class DomainCleaningConfig:
    max_domain_length: int = 800  # amino acids
    overlap_percentage: int = 20
    database_preference: list[str] = field(
        default_factory=lambda: list(DEFAULT_DATABASE_PREFERENCE)
    )


@dataclass
class CurationConfig:
    """Which backend resolves synonymous domain names into one umbrella name."""

    backend: str = "manual"  # "manual" | "gemini" | any registered CurationBackend name
    api_key: str | None = None
    model: str | None = None  # backend-specific model name; None uses the backend's default


@dataclass
class PipelineConfig:
    input: CAZyFamilyInput | CustomFastaInput
    jobname: str
    output_dir: Path

    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    domain_cleaning: DomainCleaningConfig = field(default_factory=DomainCleaningConfig)
    curation: CurationConfig = field(default_factory=CurationConfig)

    blast_identity_threshold: int = 95  # percent; used only for the characterized-enzyme
    # BLAST fallback when a characterized sequence has no UniParc entry.

    build_tree: bool = False
    alignment_tool: str = "famsa"
    tree_tool: str = "veryfasttree"

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)

    @property
    def is_cazy_query(self) -> bool:
        return isinstance(self.input, CAZyFamilyInput)
