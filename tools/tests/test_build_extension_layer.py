from scripts.build_extension_layer import resolve_components_by_tags


def test_resolve_components_by_tags_with_global_all():
    active_tags = ["lambdacomponents.all"]
    dependency_mappings = {
        "lambdacomponents.connector.aws": ["dep1"],
        "lambdacomponents.connector.gcp": ["dep2"],
        "lambdacomponents.exporter.clickhouse": ["dep3"],
    }
    included = resolve_components_by_tags(active_tags, dependency_mappings)
    assert set(included) == set(dependency_mappings.keys())


def test_resolve_components_by_tags_with_category_all():
    active_tags = ["lambdacomponents.connector.all"]
    dependency_mappings = {
        "lambdacomponents.connector.aws": ["dep1"],
        "lambdacomponents.connector.gcp": ["dep2"],
        "lambdacomponents.exporter.clickhouse": ["dep3"],
    }
    included = resolve_components_by_tags(active_tags, dependency_mappings)
    assert "lambdacomponents.connector.aws" in included
    assert "lambdacomponents.connector.gcp" in included
    assert "lambdacomponents.exporter.clickhouse" not in included


def test_resolve_components_by_tags_with_direct_match():
    active_tags = ["lambdacomponents.exporter.clickhouse"]
    dependency_mappings = {
        "lambdacomponents.connector.aws": ["dep1"],
        "lambdacomponents.exporter.clickhouse": ["dep3"],
    }
    included = resolve_components_by_tags(active_tags, dependency_mappings)
    assert included == ["lambdacomponents.exporter.clickhouse"]
