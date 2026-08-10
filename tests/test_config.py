from unittest.mock import patch

import pytest

from candy.config import (
    DEFAULT_DATABASE_PREFERENCE,
    CAZyFamilyInput,
    PipelineConfig,
    Taxonomy,
    default_tree_tool,
    reorder_database_preference,
)


def test_reorder_moves_named_databases_to_front_in_given_order():
    result = reorder_database_preference(["PFAM", "SMART"])
    assert result[0] == "PFAM"
    assert result[1] == "SMART"
    assert set(result) == set(DEFAULT_DATABASE_PREFERENCE)
    assert len(result) == len(DEFAULT_DATABASE_PREFERENCE)


def test_reorder_keeps_relative_order_of_unlisted_databases():
    result = reorder_database_preference(["PROSITE"])
    unlisted = [name for name in result if name != "PROSITE"]
    assert unlisted == [name for name in DEFAULT_DATABASE_PREFERENCE if name != "PROSITE"]


def test_reorder_is_case_insensitive_and_strips_whitespace():
    result = reorder_database_preference([" pfam ", "Smart"])
    assert result[:2] == ["PFAM", "SMART"]


def test_reorder_empty_priority_returns_default_order():
    assert reorder_database_preference([]) == DEFAULT_DATABASE_PREFERENCE


def test_reorder_deduplicates_repeated_names():
    result = reorder_database_preference(["PFAM", "PFAM"])
    assert result.count("PFAM") == 1
    assert len(result) == len(DEFAULT_DATABASE_PREFERENCE)


def test_reorder_raises_on_unknown_database_name():
    with pytest.raises(ValueError, match="Unknown database name"):
        reorder_database_preference(["NOTAREALDB"])


def test_default_tree_tool_is_fasttree_when_veryfasttree_has_no_wheel():
    with patch("candy.config.is_macos_without_native_veryfasttree_wheel", return_value=True):
        assert default_tree_tool() == "fasttree"


def test_default_tree_tool_is_veryfasttree_otherwise():
    with patch("candy.config.is_macos_without_native_veryfasttree_wheel", return_value=False):
        assert default_tree_tool() == "veryfasttree"


def test_pipeline_config_tree_tool_defaults_via_platform_detection():
    # PipelineConfig() should pick up the platform-aware default automatically,
    # not just a fixed literal -- Python API users benefit without needing to
    # know about this quirk at all.
    with patch("candy.config.is_macos_without_native_veryfasttree_wheel", return_value=True):
        config = PipelineConfig(
            input=CAZyFamilyInput(enzyme_class="GH", family_number=5, email="a@b.com", taxonomy=Taxonomy.ALL),
            jobname="job",
            output_dir=".",
        )
    assert config.tree_tool == "fasttree"


def test_pipeline_config_tree_tool_explicit_value_overrides_default():
    with patch("candy.config.is_macos_without_native_veryfasttree_wheel", return_value=True):
        config = PipelineConfig(
            input=CAZyFamilyInput(enzyme_class="GH", family_number=5, email="a@b.com", taxonomy=Taxonomy.ALL),
            jobname="job",
            output_dir=".",
            tree_tool="veryfasttree",
        )
    assert config.tree_tool == "veryfasttree"
