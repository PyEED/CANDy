"""Protein domain co-occurrence network.

Builds a graph where nodes are domain names and edges connect domains that
appear adjacently within the same protein's architecture, so recurring
architectural patterns across a whole CAZy family become visible at a
glance. Exported as GraphML for Cytoscape, same as the original notebook.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path

import networkx as nx

ARCHITECTURE_SEPARATOR = "--"


def build_cooccurrence_network(domain_architectures: Mapping[str, str]) -> nx.Graph:
    """Build a domain co-occurrence graph from {protein_id: '--'-joined domain names}.

    Each node's ``size`` attribute is the number of times that domain occurs
    across all architectures; each edge's ``width`` is the minimum occurrence
    count of the two domains it connects.

    .. note::
       The original notebook only added a node via ``add_edge``, so a domain
       that only ever occurred alone (no co-occurring partner in any
       architecture) never appeared in the network at all. Here every
       observed domain gets a node, including isolated ones with no edges,
       since a domain's absence of co-occurrence is itself informative.
    """
    graph = nx.Graph()
    domain_counts: Counter[str] = Counter()

    for architecture in domain_architectures.values():
        domains = [d for d in architecture.split(ARCHITECTURE_SEPARATOR) if d]
        domain_counts.update(domains)
        graph.add_nodes_from(domains)
        for a, b in zip(domains, domains[1:]):
            graph.add_edge(a, b)

    for node in graph.nodes():
        graph.nodes[node]["size"] = domain_counts[node]

    for source, target in graph.edges():
        graph.edges[source, target]["width"] = min(domain_counts[source], domain_counts[target])

    return graph


def write_graphml(graph: nx.Graph, output_path: str | Path) -> None:
    nx.write_graphml(graph, output_path)


def plot_network(graph: nx.Graph, output_path: str | Path | None = None, *, title: str = "Domain Co-Occurrence Network"):
    """Render a simple spring-layout visualisation; returns the Matplotlib figure.

    Saves to ``output_path`` if given, otherwise leaves the figure for the
    caller to show/save (kept out of interactive display so this works
    headlessly in scripts and CI).
    """
    import matplotlib.pyplot as plt

    node_sizes = [graph.nodes[n].get("size", 1) * 100 for n in graph.nodes()]
    edge_widths = [graph.edges[e].get("width", 1) for e in graph.edges()]

    fig, ax = plt.subplots()
    pos = nx.spring_layout(graph, seed=42)
    nx.draw_networkx_nodes(graph, pos, node_size=node_sizes, node_color="skyblue", ax=ax)
    nx.draw_networkx_edges(graph, pos, width=edge_widths, edge_color="gray", alpha=0.7, ax=ax)
    nx.draw_networkx_labels(graph, pos, font_size=10, font_color="black", ax=ax)
    ax.set_title(title)
    ax.axis("off")

    if output_path is not None:
        fig.savefig(output_path, bbox_inches="tight")

    return fig
