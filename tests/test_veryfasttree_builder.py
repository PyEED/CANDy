import random

from candy.phylogenetics import get_tree_builder
from candy.phylogenetics.veryfasttree_builder import VeryFastTreeBuilder


def test_get_tree_builder_returns_veryfasttree_by_name():
    assert get_tree_builder("veryfasttree").name == "veryfasttree"


def _random_alignment(n_sequences=12, length=200, seed=42):
    random.seed(seed)
    amino_acids = "ACDEFGHIKLMNPQRSTVWY"
    base = "".join(random.choice(amino_acids) for _ in range(length))
    records = []
    for i in range(n_sequences):
        seq = list(base)
        for _ in range(10):
            pos = random.randrange(len(seq))
            seq[pos] = random.choice(amino_acids)
        records.append((f"seq{i}", "".join(seq)))
    return "".join(f">{name}\n{seq}\n" for name, seq in records)


def test_veryfasttree_builder_produces_a_tree_file(tmp_path):
    # Regression test: veryfasttree's default ext="AUTO" was found to crash
    # (access violation) with a realistically-sized alignment on at least one
    # Windows/AVX2 machine; VeryFastTreeBuilder must always pass an explicit
    # ext= to avoid that path. A tiny (~4 sequence) alignment reproduced the
    # same crash, so this uses a more realistic size to keep the regression
    # meaningful.
    alignment_fasta = tmp_path / "aligned.fasta"
    alignment_fasta.write_text(_random_alignment())
    output_newick = tmp_path / "tree.nwk"

    VeryFastTreeBuilder().build_tree(alignment_fasta, output_newick)

    tree_text = output_newick.read_text()
    assert tree_text.strip().endswith(";")
    for i in range(12):
        assert f"seq{i}" in tree_text
