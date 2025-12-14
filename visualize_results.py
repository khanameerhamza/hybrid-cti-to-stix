"""
Visualization Utilities for TIRE Model Results
Creates visual representations of extracted entities and relations.
"""

import json
from pathlib import Path
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Note: NetworkX not available. Install with 'pip install networkx' for graph visualizations.")


def plot_entity_distribution(results_folder="./results", output_file="entity_distribution.png"):
    """Plot distribution of entity types across all documents."""
    
    # Collect entity counts
    entity_counts = Counter()
    
    results_path = Path(results_folder)
    for json_file in results_path.glob("*_results.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            entity_counts.update(data['entity_counts'])
    
    # Create bar plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    types = list(entity_counts.keys())
    counts = list(entity_counts.values())
    
    bars = ax.bar(types, counts, color='steelblue', alpha=0.7, edgecolor='black')
    
    ax.set_xlabel('Entity Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('Count', fontsize=12, fontweight='bold')
    ax.set_title('Entity Type Distribution Across All Documents', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    output_path = Path(results_folder) / output_file
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved entity distribution plot to: {output_path}")
    plt.close()


def plot_relation_distribution(results_folder="./results", output_file="relation_distribution.png"):
    """Plot distribution of relation types across all documents."""
    
    # Collect relation counts
    relation_counts = Counter()
    
    results_path = Path(results_folder)
    for json_file in results_path.glob("*_results.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            relation_counts.update(data['relation_counts'])
    
    # Create horizontal bar plot
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Sort by count
    sorted_items = sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)
    types = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]
    
    bars = ax.barh(types, counts, color='coral', alpha=0.7, edgecolor='black')
    
    ax.set_xlabel('Count', fontsize=12, fontweight='bold')
    ax.set_ylabel('Relation Type', fontsize=12, fontweight='bold')
    ax.set_title('Relation Type Distribution Across All Documents', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    output_path = Path(results_folder) / output_file
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved relation distribution plot to: {output_path}")
    plt.close()


def plot_document_statistics(results_folder="./results", output_file="document_statistics.png"):
    """Plot statistics for each document."""
    
    documents = {}
    results_path = Path(results_folder)
    
    for json_file in results_path.glob("*_results.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            doc_name = data['document_name'].replace('.txt', '')
            documents[doc_name] = {
                'sentences': data['total_sentences'],
                'entities': len(data['all_entities']),
                'relations': len(data['all_relations'])
            }
    
    # Sort by number of relations
    sorted_docs = sorted(documents.items(), key=lambda x: x[1]['relations'], reverse=True)
    sorted_docs = sorted_docs[:20]  # Top 20 documents
    
    doc_names = [item[0] for item in sorted_docs]
    entities = [item[1]['entities'] for item in sorted_docs]
    relations = [item[1]['relations'] for item in sorted_docs]
    
    # Create grouped bar plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    x = range(len(doc_names))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], entities, width, label='Entities', 
                    color='steelblue', alpha=0.7, edgecolor='black')
    bars2 = ax.bar([i + width/2 for i in x], relations, width, label='Relations', 
                    color='coral', alpha=0.7, edgecolor='black')
    
    ax.set_xlabel('Document', fontsize=12, fontweight='bold')
    ax.set_ylabel('Count', fontsize=12, fontweight='bold')
    ax.set_title('Top 20 Documents by Extracted Relations', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(doc_names, rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    output_path = Path(results_folder) / output_file
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved document statistics plot to: {output_path}")
    plt.close()


def plot_relation_network(results_folder="./results", document_name=None, 
                          output_file="relation_network.png", max_nodes=50):
    """
    Plot a network graph of entities and their relations.
    Requires networkx library.
    """
    if not NETWORKX_AVAILABLE:
        print("NetworkX is required for network visualization. Install with: pip install networkx")
        return
    
    # Load relations
    all_relations = []
    results_path = Path(results_folder)
    
    if document_name:
        # Load specific document
        json_file = results_path / f"{document_name.replace('.txt', '')}_results.json"
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_relations = data['all_relations']
    else:
        # Load all documents
        for json_file in results_path.glob("*_results.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_relations.extend(data['all_relations'][:10])  # Limit per document
    
    # Limit total nodes
    all_relations = all_relations[:max_nodes]
    
    # Build graph
    G = nx.DiGraph()
    
    # Color map for entity types
    entity_colors = {
        'HackOrg': '#ff6b6b',
        'Tool': '#4ecdc4',
        'Org': '#45b7d1',
        'Area': '#96ceb4',
        'Way': '#ffeaa7',
        'Purp': '#dfe6e9',
        'Time': '#74b9ff',
        'SecTeam': '#a29bfe',
        'Exp': '#fd79a8',
        'default': '#b2bec3'
    }
    
    node_colors = {}
    
    for rel in all_relations:
        head = rel['head']
        tail = rel['tail']
        
        # Add nodes with attributes
        G.add_node(head, entity_type=rel['head_type'])
        G.add_node(tail, entity_type=rel['tail_type'])
        
        # Add edge
        G.add_edge(head, tail, relation=rel['relation'])
        
        # Store colors
        node_colors[head] = entity_colors.get(rel['head_type'], entity_colors['default'])
        node_colors[tail] = entity_colors.get(rel['tail_type'], entity_colors['default'])
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Layout
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Draw nodes
    for node in G.nodes():
        nx.draw_networkx_nodes(G, pos, nodelist=[node], 
                              node_color=node_colors[node],
                              node_size=1000, alpha=0.7, 
                              edgecolors='black', linewidths=1.5)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, 
                          arrowstyle='->', width=1.5, alpha=0.5,
                          connectionstyle='arc3,rad=0.1')
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
    
    # Draw edge labels (relations)
    edge_labels = nx.get_edge_attributes(G, 'relation')
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=6)
    
    # Create legend
    legend_elements = [
        mpatches.Patch(color=color, label=entity_type, alpha=0.7)
        for entity_type, color in entity_colors.items()
        if entity_type != 'default' and any(
            node_colors.get(node) == color for node in G.nodes()
        )
    ]
    
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10, 
             title='Entity Types', title_fontsize=12)
    
    title = f"Relation Network Graph"
    if document_name:
        title += f" - {document_name}"
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    plt.tight_layout()
    
    output_path = Path(results_folder) / output_file
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved network graph to: {output_path}")
    plt.close()


def create_all_visualizations(results_folder="./results"):
    """Create all available visualizations."""
    
    print("\n" + "="*80)
    print("Creating Visualizations")
    print("="*80 + "\n")
    
    print("1. Entity Distribution...")
    plot_entity_distribution(results_folder)
    
    print("2. Relation Distribution...")
    plot_relation_distribution(results_folder)
    
    print("3. Document Statistics...")
    plot_document_statistics(results_folder)
    
    if NETWORKX_AVAILABLE:
        print("4. Relation Network Graph...")
        plot_relation_network(results_folder, max_nodes=30)
    
    print("\n✓ All visualizations created!")
    print(f"✓ Check the '{results_folder}' folder for PNG files")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Install matplotlib if needed
    try:
        import matplotlib
    except ImportError:
        print("Matplotlib is required. Install with: pip install matplotlib")
        exit(1)
    
    create_all_visualizations("./results")
