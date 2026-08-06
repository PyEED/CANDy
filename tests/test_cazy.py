import pandas as pd

from candy.cazy import extract_characterized_ids, extract_ncbi_ids, parse_family_table
from candy.config import Taxonomy

SAMPLE_FAMILY_TABLE = (
    "GH5\tBacteria\tEcoli\tP12345\tncbi\n"
    "GH5\tArchaea\tSacc\tP67890\tjgi\n"
    "GH5\tEukaryota\tYeast\tP11111\tncbi\n"
)


def test_parse_family_table_builds_taxonomy_dict():
    df, taxonomy_dict = parse_family_table(SAMPLE_FAMILY_TABLE)
    assert taxonomy_dict == {"P12345": "B", "P67890": "A", "P11111": "E"}
    assert len(df) == 3


def test_extract_ncbi_ids_excludes_jgi_sourced():
    df, taxonomy_dict = parse_family_table(SAMPLE_FAMILY_TABLE)
    ids = extract_ncbi_ids(df, taxonomy_dict, Taxonomy.ALL)
    assert ids == ["P12345", "P11111"]


def test_extract_ncbi_ids_filters_by_taxonomy():
    df, taxonomy_dict = parse_family_table(SAMPLE_FAMILY_TABLE)
    ids = extract_ncbi_ids(df, taxonomy_dict, Taxonomy.BACTERIA)
    assert ids == ["P12345"]


def test_extract_characterized_ids_groups_by_taxonomy_header():
    # column 4 mimics CAZy's characterized table layout: taxonomy header rows
    # interspersed with GenBank-ID rows ("ID.version").
    col4 = pd.Series(["Bacteria", "P12345.1", "P12345.1", "Archaea", "Q99999.2"])
    col1 = pd.Series(["", "1.2.4.-", "1.2.4.-", "", "3.2.1.-"])
    table = pd.DataFrame({1: col1, 4: col4})

    ids, taxonomy_dict, activity_dict = extract_characterized_ids([None, table])

    assert ids == ["P12345.1", "Q99999.2"]
    assert taxonomy_dict == {"P12345.1": "B", "Q99999.2": "A"}
    assert activity_dict == {"P12345.1": "1.2.4.-", "Q99999.2": "3.2.1.-"}
