from candy.domains import (
    clean_domains,
    group_overlapping,
    map_positions_to_names,
    positions_overlap,
)

DEFAULT_PREFERENCE = ["SMART", "CDD", "PFAM", "SUPERFAMILY"]


def test_positions_overlap_no_overlap():
    assert positions_overlap([1, 50], [200, 250], 0.2) is False


def test_positions_overlap_full_containment():
    assert positions_overlap([1, 500], [100, 200], 0.2) is True


def test_positions_overlap_partial_above_threshold():
    # overlap region 80-100 = 20 residues; length1=100(0-100)->100 len; length2=100(80-180)
    assert positions_overlap([0, 100], [80, 180], 0.1) is True


def test_positions_overlap_partial_below_threshold():
    assert positions_overlap([0, 100], [95, 195], 0.5) is False


def test_positions_overlap_zero_length_domain_is_full_identity():
    assert positions_overlap([50, 50], [40, 60], 0.99) is True


def test_group_overlapping_separates_distinct_domains():
    positions = [[1, 100], [150, 300]]
    groups = group_overlapping(positions, 0.2)
    assert groups == [[1, 100], [150, 300]]


def test_group_overlapping_merges_overlapping_domains():
    positions = [[1, 100], [10, 110]]
    groups = group_overlapping(positions, 0.2)
    assert groups == [[[1, 100], [10, 110]]]


def test_map_positions_to_names_duplicate_position_keeps_last_hit():
    # Two databases report the identical span [1, 100] with different names.
    # Only one can survive the str(position) dict key collision; pairing by
    # loop index (not value.index()) means the *current* hit's name wins,
    # i.e. normal last-write-wins dict semantics rather than being stuck on
    # whichever hit happened to come first in the raw API response.
    position_dict = {"P1": [[1, 100], [1, 100]]}
    domain_name_list = {"P1": [["SMART", "Catalytic domain"], ["PFAM", "CBM"]]}

    result = map_positions_to_names(position_dict, domain_name_list)

    assert result["P1"] == {"[1, 100]": "CBM"}


def test_map_positions_to_names_distinct_positions():
    position_dict = {"P1": [[1, 100], [150, 300]]}
    domain_name_list = {"P1": [["SMART", "Catalytic domain"], ["PFAM", "CBM"]]}

    result = map_positions_to_names(position_dict, domain_name_list)

    assert result["P1"] == {"[1, 100]": "Catalytic domain", "[150, 300]": "CBM"}


def test_clean_domains_keeps_single_non_overlapping_domain():
    position_dict = {"P1": [[1, 100]]}
    position_to_name = {"P1": {"[1, 100]": "Catalytic domain"}}
    name_to_database = {"P1": {"Catalytic domain": "SMART"}}

    result = clean_domains(
        position_dict, position_to_name, name_to_database, DEFAULT_PREFERENCE, 0.2, 800
    )

    assert result["P1"] == [([1, 100], "Catalytic domain")]


def test_clean_domains_excludes_signal_peptide_and_transmembrane():
    position_dict = {"P1": [[1, 20], [30, 100]]}
    position_to_name = {"P1": {"[1, 20]": "Signal peptide", "[30, 100]": "Catalytic domain"}}
    name_to_database = {"P1": {"Signal peptide": "PHOBIUS", "Catalytic domain": "SMART"}}

    result = clean_domains(
        position_dict, position_to_name, name_to_database, DEFAULT_PREFERENCE, 0.2, 800
    )

    assert result["P1"] == [([30, 100], "Catalytic domain")]


def test_clean_domains_picks_highest_priority_database_for_overlapping_hits():
    # Same region called by both PFAM and SMART; SMART should win (rank 0).
    position_dict = {"P1": [[1, 100], [5, 105]]}
    position_to_name = {"P1": {"[1, 100]": "PFAM catalytic", "[5, 105]": "SMART catalytic"}}
    name_to_database = {"P1": {"PFAM catalytic": "PFAM", "SMART catalytic": "SMART"}}

    result = clean_domains(
        position_dict, position_to_name, name_to_database, DEFAULT_PREFERENCE, 0.2, 800
    )

    assert len(result["P1"]) == 1
    assert result["P1"][0][1] == "SMART catalytic"


def test_clean_domains_filters_domains_outside_length_bounds_in_grouped_case():
    # Overlapping group where one candidate is far too long (> max_domain_length).
    position_dict = {"P1": [[1, 1000], [5, 105]]}
    position_to_name = {"P1": {"[1, 1000]": "Bogus long hit", "[5, 105]": "Real domain"}}
    name_to_database = {"P1": {"Bogus long hit": "PFAM", "Real domain": "SMART"}}

    result = clean_domains(
        position_dict, position_to_name, name_to_database, DEFAULT_PREFERENCE, 0.2, max_domain_length=200
    )

    assert result["P1"] == [([5, 105], "Real domain")]


def test_clean_domains_no_domains_gives_empty_list():
    result = clean_domains({"P1": []}, {"P1": {}}, {"P1": {}}, DEFAULT_PREFERENCE, 0.2, 800)
    assert result["P1"] == []
