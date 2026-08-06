"""Integration-style tests for the pipeline orchestrator.

External services (InterPro, NCBI/CAZy) and external CLI tools (MAFFT,
FastTree, CD-HIT/MMseqs2) are mocked at their lowest-level boundary so these
tests exercise the *wiring* between candy's modules -- correct data flow and
argument order between stages -- without needing network access or any
bioinformatics tools installed.
"""

import xml.etree.ElementTree as ET
from unittest.mock import patch

import pandas as pd

from candy.config import CAZyFamilyInput, ClusteringConfig, CustomFastaInput, PipelineConfig, Taxonomy
from candy.pipeline import run_pipeline


class StubCurationBackend:
    name = "stub"

    def curate(self, domain_names, *, family=None):
        return {name: [name] for name in domain_names}


def _fake_match_xml(md5_list):
    root = ET.Element("response")
    results = ET.SubElement(root, "results")
    for md5 in md5_list:
        match = ET.SubElement(results, "match")
        ET.SubElement(match, "proteinMD5").text = md5
        hit = ET.SubElement(match, "hit")
        hit.text = "SMART,domain,SM00000,x,x,x,1-50-Y"
    return root


def test_run_pipeline_custom_fasta_mode_without_tree(tmp_path):
    fasta_path = tmp_path / "input.fasta"
    fasta_path.write_text(">Protein1\nMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLA\n")

    config = PipelineConfig(
        input=CustomFastaInput(fasta_path=fasta_path),
        jobname="testjob",
        output_dir=tmp_path / "out",
        build_tree=False,
    )

    with patch("candy.interpro._query_md5_batch", side_effect=lambda batch: _fake_match_xml(batch)), patch(
        "candy.interpro._fetch_entry_name", return_value="Catalytic domain"
    ), patch("candy.pipeline.get_curation_backend", return_value=StubCurationBackend()):
        result = run_pipeline(config)

    assert result.database_path.exists()
    assert result.network_graphml_path.exists()
    assert result.domain_annotation_path is None  # build_tree=False
    assert result.tree_path is None
    assert result.sequence_count == 1


def test_run_pipeline_custom_fasta_mode_with_tree(tmp_path):
    fasta_path = tmp_path / "input.fasta"
    fasta_path.write_text(">Protein1\nMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLA\n")

    config = PipelineConfig(
        input=CustomFastaInput(fasta_path=fasta_path),
        jobname="testjob2",
        output_dir=tmp_path / "out",
        build_tree=True,
    )

    def fake_align(self, input_fasta, output_fasta):
        output_fasta.write_text(input_fasta.read_text())
        return output_fasta

    def fake_build_tree(self, alignment_fasta, output_newick):
        output_newick.write_text("(Protein1:0.1);")
        return output_newick

    with patch("candy.interpro._query_md5_batch", side_effect=lambda batch: _fake_match_xml(batch)), patch(
        "candy.interpro._fetch_entry_name", return_value="Catalytic domain"
    ), patch("candy.pipeline.get_curation_backend", return_value=StubCurationBackend()), patch(
        "candy.alignment.mafft.MafftAligner.align", fake_align
    ), patch("candy.phylogenetics.fasttree.FastTreeBuilder.build_tree", fake_build_tree):
        result = run_pipeline(config)

    assert result.tree_path.exists()
    assert result.domain_annotation_path.exists()
    assert result.characterized_annotation_path is None  # custom FASTA mode has no characterized enzymes
    assert "DATASET_DOMAINS" in result.domain_annotation_path.read_text()


class FakeHandle:
    """Stand-in for the object Bio.Entrez.efetch returns (used as a context manager)."""

    def __init__(self, text):
        self._text = text

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._text


class IdentityClusterer:
    name = "identity"

    def cluster(self, input_fasta, output_fasta, config):
        output_fasta.write_text(input_fasta.read_text())
        return output_fasta


def test_run_pipeline_cazy_query_mode_end_to_end(tmp_path):
    fasta_by_id = {
        "P12345.1": ">P12345.1 alpha-glucosidase [Escherichia coli]\nMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLAMKVLA\n",
    }

    def fake_efetch(db, id, rettype, retmode):
        return FakeHandle("".join(fasta_by_id[i] for i in id.split(",")))

    family_page_text = "GH5\tBacteria\tEcoli\tP12345.1\tncbi\n"
    characterized_table = pd.DataFrame(
        {1: ["", "3.2.1.4"], 4: ["Bacteria", "P12345.1"]}
    )

    config = PipelineConfig(
        input=CAZyFamilyInput(enzyme_class="GH", family_number=5, email="test@example.com", taxonomy=Taxonomy.ALL),
        jobname="cazytestjob",
        output_dir=tmp_path / "out",
        clustering=ClusteringConfig(identity_cutoff=85),
        build_tree=False,
    )

    with patch("candy.cazy.fetch_family_page", return_value=family_page_text), patch(
        "candy.cazy.fetch_characterized_page", return_value=[None, characterized_table]
    ), patch("candy.cazy.Entrez.efetch", side_effect=fake_efetch), patch(
        "candy.interpro._query_md5_batch", side_effect=lambda batch: _fake_match_xml(batch)
    ), patch("candy.interpro._fetch_entry_name", return_value="Catalytic domain"), patch(
        "candy.pipeline.get_curation_backend", return_value=StubCurationBackend()
    ), patch("candy.pipeline.get_clusterer", return_value=IdentityClusterer()):
        result = run_pipeline(config)

    assert result.database_path.exists()
    assert result.sequence_count == 1

    import sqlite3

    conn = sqlite3.connect(result.database_path)
    rows = conn.execute("SELECT protein_sequence_id, taxonomy, organism_name, characterized FROM protein_sequences").fetchall()
    conn.close()

    assert rows == [("P12345.1", "Bacteria", "Escherichia coli", "C")]
