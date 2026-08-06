"""Pluggable phylogenetic tree-building backends."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TreeBuilder(Protocol):
    name: str

    def build_tree(self, alignment_fasta: Path, output_newick: Path) -> Path:
        """Build a tree from an aligned FASTA file, writing Newick to ``output_newick``."""
        ...


def get_tree_builder(name: str) -> TreeBuilder:
    if name == "fasttree":
        from candy.phylogenetics.fasttree import FastTreeBuilder

        return FastTreeBuilder()
    raise ValueError(f"Unknown tree builder: {name}")
