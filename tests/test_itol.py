from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from candy.itol import (
    _protein_id_for_matching,
    build_characterized_style_annotation,
    build_domain_annotation,
)


def make_record(id_, seq="MKVLAMKVLAMKVLA"):
    return SeqRecord(Seq(seq), id=id_)


def test_protein_id_for_matching_cazy_style_header():
    assert _protein_id_for_matching("P12345_Escherichia_coli_B") == "P12345"


def test_protein_id_for_matching_short_prefix_before_underscore():
    assert _protein_id_for_matching("AW_12345") == "AW_12345"


def test_protein_id_for_matching_no_underscore_used_verbatim():
    assert _protein_id_for_matching("customheader") == "customheader"


def test_build_domain_annotation_assigns_shapes_colors_and_data_line():
    domain_architecture = {"P12345": [([1, 10], "Catalytic domain")]}
    curated_domains = {"Catalytic domain": ["Catalytic domain"]}
    records = [make_record("P12345_Escherichia_coli_B")]

    result = build_domain_annotation("myjob", domain_architecture, curated_domains, records)

    assert "DATASET_DOMAINS" in result
    assert "LEGEND_LABELS\t\tCatalytic domain" in result
    assert "P12345_Escherichia_coli_B\t15\tRE|1|10|#BF0F0F|Catalytic domain" in result


def test_build_domain_annotation_uses_umbrella_name():
    domain_architecture = {"P12345": [([1, 10], "raw name")]}
    curated_domains = {"Umbrella": ["raw name"]}
    records = [make_record("P12345_Org_B")]

    result = build_domain_annotation("myjob", domain_architecture, curated_domains, records)
    data_section = result.split("\nDATA\n")[1]
    assert "Umbrella" in data_section
    assert "raw name" not in data_section


def test_build_characterized_style_annotation_skips_ids_without_ec_number(tmp_path):
    tree_path = tmp_path / "tree.nwk"
    tree_path.write_text("(P12345_Org_B:0.1,P67890_Org_B:0.1);")

    result = build_characterized_style_annotation(
        tree_path,
        characterized_ids=["P12345", "P67890"],
        ec_numbers={"P12345": "3.2.1.4"},
        legend_title="GH5",
    )

    data_section = result.split("\nDATA\n")[1]
    assert "P12345_Org_B label node" in data_section
    assert "P67890_Org_B" not in data_section


def test_build_characterized_style_annotation_multiple_ec_numbers_uses_first(tmp_path):
    tree_path = tmp_path / "tree.nwk"
    tree_path.write_text("(P12345_Org_B:0.1,P67890_Org_B:0.1);")

    result = build_characterized_style_annotation(
        tree_path,
        characterized_ids=["P12345"],
        ec_numbers={"P12345": "3.2.1.4 3.2.1.20"},
        legend_title="GH5",
    )
    header_and_legend = result.split("\nDATA\n")[0]
    assert "3.2.1.4" in header_and_legend
    assert "3.2.1.20" not in header_and_legend
