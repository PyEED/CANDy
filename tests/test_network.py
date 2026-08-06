from candy.network import build_cooccurrence_network


def test_build_cooccurrence_network_counts_and_edges():
    architectures = {
        "P1": "CBM--Catalytic domain",
        "P2": "CBM--Catalytic domain",
        "P3": "Catalytic domain",
    }

    graph = build_cooccurrence_network(architectures)

    assert set(graph.nodes()) == {"CBM", "Catalytic domain"}
    assert graph.nodes["Catalytic domain"]["size"] == 3
    assert graph.nodes["CBM"]["size"] == 2
    assert graph.has_edge("CBM", "Catalytic domain")
    assert graph.edges["CBM", "Catalytic domain"]["width"] == 2


def test_build_cooccurrence_network_ignores_empty_architecture():
    graph = build_cooccurrence_network({"P1": ""})
    assert len(graph.nodes()) == 0


def test_build_cooccurrence_network_single_domain_no_edges():
    graph = build_cooccurrence_network({"P1": "Catalytic domain"})
    assert set(graph.nodes()) == {"Catalytic domain"}
    assert len(graph.edges()) == 0
