"""
Example: Using Merged Entity and Relationship Data

This script demonstrates how to query and analyze the merged JSON outputs.
"""

import json
from pathlib import Path
from collections import Counter


def load_consolidated_data(file_path="./merged_final/all_documents_consolidated.json"):
    """Load the consolidated JSON file with all documents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        print("Please run merge_entity_relationship_data.py first!")
        return None


def example_1_find_all_tools_used_by_actor(data, actor_name):
    """Find all tools used by a specific threat actor."""
    print(f"\n{'='*80}")
    print(f"Example 1: Tools used by {actor_name}")
    print(f"{'='*80}")
    
    tools_found = []
    
    for doc_name, doc_data in data['documents'].items():
        # Check if this document is about the actor
        if actor_name.lower() not in doc_name.lower():
            continue
        
        # Find all 'uses' relationships where tail is a Tool
        relations = doc_data['relationships']['validated_relations']
        for rel in relations:
            if rel['relation'] == 'uses' and 'tool' in rel['tail_type'].lower():
                tools_found.append({
                    'tool': rel['tail'],
                    'context': rel['sentence_text'][:100] + "..."
                })
    
    if tools_found:
        print(f"\nFound {len(tools_found)} tools used by {actor_name}:")
        for i, tool_info in enumerate(tools_found[:10], 1):
            print(f"\n{i}. {tool_info['tool']}")
            print(f"   Context: {tool_info['context']}")
    else:
        print(f"No tools found for {actor_name}")


def example_2_find_targeted_organizations(data):
    """Find all organizations targeted across all documents."""
    print(f"\n{'='*80}")
    print(f"Example 2: Organizations Targeted by Threat Actors")
    print(f"{'='*80}")
    
    targets = []
    
    for doc_name, doc_data in data['documents'].items():
        relations = doc_data['relationships']['validated_relations']
        for rel in relations:
            if rel['relation'] == 'targets' and 'org' in rel['tail_type'].lower():
                targets.append({
                    'actor': rel['head'],
                    'target': rel['tail'],
                    'document': doc_name
                })
    
    # Count most targeted
    target_counts = Counter(t['target'] for t in targets)
    
    print(f"\nTotal targeting relationships found: {len(targets)}")
    print(f"\nMost frequently targeted organizations:")
    for target, count in target_counts.most_common(10):
        print(f"  {count:3d}x - {target}")
    
    # Show which actors target specific orgs
    print(f"\nExample: Who targets government agencies?")
    gov_targets = [t for t in targets if 'government' in t['target'].lower() or 'agency' in t['target'].lower()]
    actors = set(t['actor'] for t in gov_targets)
    print(f"  {len(actors)} threat actors target government: {', '.join(list(actors)[:5])}")


def example_3_find_entities_needing_relations(data):
    """Find entities that don't have relationship information yet."""
    print(f"\n{'='*80}")
    print(f"Example 3: Entities Needing Relationship Extraction")
    print(f"{'='*80}")
    
    all_missing = {}
    
    for doc_name, doc_data in data['documents'].items():
        missing = doc_data['relationships']['entities_needing_relationship_extraction']
        if missing:
            all_missing[doc_name] = missing
    
    print(f"\nDocuments with missing relationships: {len(all_missing)}")
    
    # Show top documents
    sorted_docs = sorted(all_missing.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"\nTop 5 documents with most missing relationships:")
    for doc_name, missing_entities in sorted_docs[:5]:
        print(f"\n{doc_name}: {len(missing_entities)} entities")
        for entity in missing_entities[:5]:
            print(f"  - {entity}")
        if len(missing_entities) > 5:
            print(f"  ... and {len(missing_entities) - 5} more")


def example_4_analyze_attack_patterns(data):
    """Analyze MITRE ATT&CK patterns across all documents."""
    print(f"\n{'='*80}")
    print(f"Example 4: MITRE ATT&CK Technique Analysis")
    print(f"{'='*80}")
    
    all_techniques = []
    
    for doc_name, doc_data in data['documents'].items():
        techniques = doc_data['attack_ttps']['techniques']
        for tech in techniques:
            all_techniques.append({
                'code': tech['code'],
                'name': tech['name'],
                'document': doc_name
            })
    
    # Count most common techniques
    technique_counts = Counter(f"{t['code']} - {t['name']}" for t in all_techniques)
    
    print(f"\nTotal technique mappings: {len(all_techniques)}")
    print(f"Unique techniques: {len(set(t['code'] for t in all_techniques))}")
    
    print(f"\nMost common MITRE ATT&CK techniques:")
    for technique, count in technique_counts.most_common(10):
        print(f"  {count:3d}x - {technique}")


def example_5_extract_iocs_for_actor(data, actor_name):
    """Extract all IOCs associated with a threat actor."""
    print(f"\n{'='*80}")
    print(f"Example 5: IOC Indicators for {actor_name}")
    print(f"{'='*80}")
    
    for doc_name, doc_data in data['documents'].items():
        if actor_name.lower() not in doc_name.lower():
            continue
        
        iocs = doc_data['ioc_indicators']
        
        print(f"\nIOCs from {doc_name}:")
        
        # Count total IOCs
        total = sum(len(v) if isinstance(v, list) else 0 for v in iocs.values())
        print(f"  Total IOCs: {total}")
        
        # Show each type
        ioc_types = ['ips', 'domains', 'urls', 'hashes', 'cves', 'file_paths']
        for ioc_type in ioc_types:
            items = iocs.get(ioc_type, [])
            if items and isinstance(items, list):
                print(f"\n  {ioc_type.upper()}: {len(items)}")
                for item in items[:5]:
                    print(f"    - {item}")
                if len(items) > 5:
                    print(f"    ... and {len(items) - 5} more")


def example_6_relationship_type_distribution(data):
    """Analyze distribution of relationship types."""
    print(f"\n{'='*80}")
    print(f"Example 6: Relationship Type Distribution")
    print(f"{'='*80}")
    
    all_relations = []
    
    for doc_name, doc_data in data['documents'].items():
        relations = doc_data['relationships']['validated_relations']
        all_relations.extend([r['relation'] for r in relations])
    
    relation_counts = Counter(all_relations)
    
    print(f"\nTotal relationships: {len(all_relations)}")
    print(f"Unique relationship types: {len(relation_counts)}")
    
    print(f"\nRelationship type distribution:")
    for rel_type, count in relation_counts.most_common():
        percentage = (count / len(all_relations)) * 100
        print(f"  {rel_type:20s}: {count:4d} ({percentage:5.1f}%)")


def example_7_build_simple_knowledge_graph(data, max_nodes=20):
    """Build a simple knowledge graph representation."""
    print(f"\n{'='*80}")
    print(f"Example 7: Knowledge Graph Construction (Sample)")
    print(f"{'='*80}")
    
    nodes = set()
    edges = []
    
    # Take first document as example
    first_doc = list(data['documents'].values())[0]
    relations = first_doc['relationships']['validated_relations']
    
    for rel in relations[:max_nodes]:
        nodes.add((rel['head'], rel['head_type']))
        nodes.add((rel['tail'], rel['tail_type']))
        edges.append({
            'source': rel['head'],
            'target': rel['tail'],
            'relation': rel['relation']
        })
    
    print(f"\nSample Knowledge Graph from: {first_doc['document_name']}")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    
    print(f"\nSample nodes:")
    for entity, etype in list(nodes)[:10]:
        print(f"  - {entity} ({etype})")
    
    print(f"\nSample edges:")
    for edge in edges[:10]:
        print(f"  - {edge['source']} --[{edge['relation']}]--> {edge['target']}")


def example_8_compare_documents(data, doc1_name, doc2_name):
    """Compare two documents to find similarities."""
    print(f"\n{'='*80}")
    print(f"Example 8: Comparing {doc1_name} and {doc2_name}")
    print(f"{'='*80}")
    
    # Find matching documents
    doc1 = None
    doc2 = None
    
    for doc_name, doc_data in data['documents'].items():
        if doc1_name.lower() in doc_name.lower():
            doc1 = doc_data
        if doc2_name.lower() in doc_name.lower():
            doc2 = doc_data
    
    if not doc1 or not doc2:
        print("One or both documents not found")
        return
    
    # Compare entities
    entities1 = set(e['text'].lower() for e in doc1['entities']['detailed_list'])
    entities2 = set(e['text'].lower() for e in doc2['entities']['detailed_list'])
    
    common_entities = entities1 & entities2
    
    print(f"\nEntity comparison:")
    print(f"  {doc1['document_name']}: {len(entities1)} entities")
    print(f"  {doc2['document_name']}: {len(entities2)} entities")
    print(f"  Common entities: {len(common_entities)}")
    
    if common_entities:
        print(f"\nSample common entities:")
        for entity in list(common_entities)[:10]:
            print(f"  - {entity}")
    
    # Compare TTPs
    ttps1 = set(t['code'] for t in doc1['attack_ttps']['techniques'])
    ttps2 = set(t['code'] for t in doc2['attack_ttps']['techniques'])
    
    common_ttps = ttps1 & ttps2
    
    print(f"\nTTP comparison:")
    print(f"  {doc1['document_name']}: {len(ttps1)} techniques")
    print(f"  {doc2['document_name']}: {len(ttps2)} techniques")
    print(f"  Common techniques: {len(common_ttps)}")
    
    if common_ttps:
        print(f"  Shared TTPs: {', '.join(common_ttps)}")


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("MERGED DATA ANALYSIS EXAMPLES")
    print("="*80)
    
    # Load data
    print("\nLoading consolidated data...")
    data = load_consolidated_data()
    
    if not data:
        return
    
    print(f"Loaded {data['metadata']['total_documents']} documents")
    
    # Run examples
    example_1_find_all_tools_used_by_actor(data, "APT28")
    example_2_find_targeted_organizations(data)
    example_3_find_entities_needing_relations(data)
    example_4_analyze_attack_patterns(data)
    example_5_extract_iocs_for_actor(data, "APT28")
    example_6_relationship_type_distribution(data)
    example_7_build_simple_knowledge_graph(data)
    example_8_compare_documents(data, "APT28", "APT29")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE!")
    print("="*80)
    print("\nThese examples show how to:")
    print("  ✓ Query specific threat actors")
    print("  ✓ Find relationships and patterns")
    print("  ✓ Extract IOCs and TTPs")
    print("  ✓ Build knowledge graphs")
    print("  ✓ Compare threat actors")
    print("\nModify these examples for your specific use case!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
