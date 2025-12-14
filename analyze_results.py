"""
Analysis Utilities for TIRE Model Results
This script provides helper functions to analyze and query extracted relations.
"""

import json
import os
from pathlib import Path
from collections import Counter, defaultdict
import csv

class RelationAnalyzer:
    """Analyze extracted relations from processed documents."""
    
    def __init__(self, results_folder="./results"):
        """
        Initialize analyzer with results folder.
        
        Args:
            results_folder: Path to folder containing JSON results
        """
        self.results_folder = results_folder
        self.documents = {}
        self.load_results()
    
    def load_results(self):
        """Load all JSON result files."""
        results_path = Path(self.results_folder)
        
        for json_file in results_path.glob("*_results.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                doc_name = data['document_name']
                self.documents[doc_name] = data
        
        print(f"Loaded {len(self.documents)} documents")
    
    def get_all_relations(self):
        """Get all relations from all documents."""
        all_relations = []
        for doc_name, doc_data in self.documents.items():
            all_relations.extend(doc_data['all_relations'])
        return all_relations
    
    def get_all_entities(self):
        """Get all entities from all documents."""
        all_entities = []
        for doc_name, doc_data in self.documents.items():
            all_entities.extend(doc_data['all_entities'])
        return all_entities
    
    def find_relations_by_type(self, relation_type):
        """Find all relations of a specific type."""
        relations = []
        for doc_name, doc_data in self.documents.items():
            for rel in doc_data['all_relations']:
                if rel['relation'] == relation_type:
                    relations.append({
                        'document': doc_name,
                        **rel
                    })
        return relations
    
    def find_relations_with_entity(self, entity_text, position='any'):
        """
        Find relations involving a specific entity.
        
        Args:
            entity_text: Text of the entity to search for
            position: 'head', 'tail', or 'any'
        """
        relations = []
        for doc_name, doc_data in self.documents.items():
            for rel in doc_data['all_relations']:
                match = False
                if position == 'any':
                    match = entity_text.lower() in rel['head'].lower() or \
                            entity_text.lower() in rel['tail'].lower()
                elif position == 'head':
                    match = entity_text.lower() in rel['head'].lower()
                elif position == 'tail':
                    match = entity_text.lower() in rel['tail'].lower()
                
                if match:
                    relations.append({
                        'document': doc_name,
                        **rel
                    })
        return relations
    
    def get_relation_statistics(self):
        """Get statistics about relations across all documents."""
        all_relations = self.get_all_relations()
        
        stats = {
            'total_relations': len(all_relations),
            'relation_type_counts': Counter(r['relation'] for r in all_relations),
            'head_type_counts': Counter(r['head_type'] for r in all_relations),
            'tail_type_counts': Counter(r['tail_type'] for r in all_relations),
            'relation_patterns': Counter(
                f"{r['head_type']} --[{r['relation']}]--> {r['tail_type']}"
                for r in all_relations
            )
        }
        
        return stats
    
    def get_entity_statistics(self):
        """Get statistics about entities across all documents."""
        all_entities = self.get_all_entities()
        
        stats = {
            'total_entities': len(all_entities),
            'entity_type_counts': Counter(e['type'] for e in all_entities),
            'unique_entities': len(set(e['text'].lower() for e in all_entities)),
            'most_common_entities': Counter(e['text'] for e in all_entities).most_common(20)
        }
        
        return stats
    
    def build_knowledge_graph(self):
        """
        Build a knowledge graph representation from all relations.
        Returns nodes and edges suitable for graph visualization.
        """
        nodes = {}
        edges = []
        
        for doc_name, doc_data in self.documents.items():
            for rel in doc_data['all_relations']:
                # Add nodes
                head_id = f"{rel['head']}_{rel['head_type']}"
                tail_id = f"{rel['tail']}_{rel['tail_type']}"
                
                if head_id not in nodes:
                    nodes[head_id] = {
                        'id': head_id,
                        'label': rel['head'],
                        'type': rel['head_type']
                    }
                
                if tail_id not in nodes:
                    nodes[tail_id] = {
                        'id': tail_id,
                        'label': rel['tail'],
                        'type': rel['tail_type']
                    }
                
                # Add edge
                edges.append({
                    'source': head_id,
                    'target': tail_id,
                    'relation': rel['relation'],
                    'document': doc_name,
                    'sentence_id': rel['sentence_id']
                })
        
        return {
            'nodes': list(nodes.values()),
            'edges': edges
        }
    
    def export_to_neo4j_cypher(self, output_file="neo4j_import.cypher"):
        """
        Export relations as Neo4j Cypher queries for knowledge graph import.
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("// TIRE Model - Knowledge Graph Import for Neo4j\n")
            f.write("// Generated Cypher queries to create nodes and relationships\n\n")
            
            # Create nodes
            f.write("// Create Entity Nodes\n")
            all_entities = self.get_all_entities()
            unique_entities = {}
            
            for entity in all_entities:
                key = (entity['text'], entity['type'])
                if key not in unique_entities:
                    unique_entities[key] = entity
            
            for (text, etype), entity in unique_entities.items():
                safe_text = text.replace("'", "\\'")
                f.write(f"MERGE (n:{etype} {{name: '{safe_text}'}})\n")
            
            f.write("\n// Create Relationships\n")
            all_relations = self.get_all_relations()
            
            for rel in all_relations:
                head = rel['head'].replace("'", "\\'")
                tail = rel['tail'].replace("'", "\\'")
                rel_type = rel['relation'].upper()
                
                f.write(
                    f"MATCH (a:{rel['head_type']} {{name: '{head}'}}), "
                    f"(b:{rel['tail_type']} {{name: '{tail}'}})\n"
                    f"MERGE (a)-[:{rel_type}]->(b);\n\n"
                )
        
        print(f"Exported Neo4j Cypher queries to: {output_file}")
    
    def print_summary(self):
        """Print a comprehensive summary of extracted data."""
        print("\n" + "="*80)
        print("TIRE MODEL EXTRACTION SUMMARY")
        print("="*80)
        
        # Document statistics
        print(f"\nDocuments Processed: {len(self.documents)}")
        total_sentences = sum(d['total_sentences'] for d in self.documents.values())
        print(f"Total Sentences: {total_sentences}")
        
        # Entity statistics
        entity_stats = self.get_entity_statistics()
        print(f"\nTotal Entities Extracted: {entity_stats['total_entities']}")
        print(f"Unique Entities: {entity_stats['unique_entities']}")
        
        print("\nTop Entity Types:")
        for entity_type, count in entity_stats['entity_type_counts'].most_common(10):
            print(f"  {entity_type}: {count}")
        
        print("\nMost Common Entities:")
        for entity, count in entity_stats['most_common_entities'][:10]:
            print(f"  {entity}: {count}")
        
        # Relation statistics
        rel_stats = self.get_relation_statistics()
        print(f"\nTotal Relations Extracted: {rel_stats['total_relations']}")
        
        print("\nRelation Types:")
        for rel_type, count in rel_stats['relation_type_counts'].most_common():
            print(f"  {rel_type}: {count}")
        
        print("\nTop Relation Patterns:")
        for pattern, count in rel_stats['relation_patterns'].most_common(10):
            print(f"  {pattern}: {count}")
        
        print("="*80 + "\n")


def example_queries():
    """Example queries using the RelationAnalyzer."""
    
    analyzer = RelationAnalyzer("./results")
    
    print("\n" + "="*80)
    print("EXAMPLE QUERIES")
    print("="*80)
    
    # Query 1: Find all 'uses' relations
    print("\n1. Finding all 'uses' relationships...")
    uses_relations = analyzer.find_relations_by_type('uses')
    print(f"Found {len(uses_relations)} 'uses' relationships")
    for rel in uses_relations[:5]:
        print(f"  • {rel['head']} uses {rel['tail']} (in {rel['document']})")
    
    # Query 2: Find relations with specific entity
    print("\n2. Finding relations involving 'APT28'...")
    apt28_relations = analyzer.find_relations_with_entity('APT28', position='any')
    print(f"Found {len(apt28_relations)} relations involving APT28")
    for rel in apt28_relations[:5]:
        print(f"  • {rel['head']} --[{rel['relation']}]--> {rel['tail']}")
    
    # Query 3: Get all tools used
    print("\n3. Finding all tools (tail entities with type 'Tool')...")
    all_relations = analyzer.get_all_relations()
    tools = set(r['tail'] for r in all_relations if r['tail_type'] == 'Tool')
    print(f"Found {len(tools)} unique tools:")
    for tool in list(tools)[:10]:
        print(f"  • {tool}")
    
    # Query 4: Build knowledge graph
    print("\n4. Building knowledge graph...")
    kg = analyzer.build_knowledge_graph()
    print(f"Knowledge Graph: {len(kg['nodes'])} nodes, {len(kg['edges'])} edges")
    
    # Save knowledge graph
    with open('./results/knowledge_graph.json', 'w', encoding='utf-8') as f:
        json.dump(kg, f, indent=2, ensure_ascii=False)
    print("  Saved to: knowledge_graph.json")
    
    # Query 5: Statistics
    print("\n5. Overall Statistics:")
    analyzer.print_summary()


if __name__ == "__main__":
    print("\nTIRE Model - Relation Analysis Utilities")
    print("="*80)
    
    # Run example queries
    example_queries()
    
    # Export for Neo4j
    print("\n6. Exporting to Neo4j format...")
    analyzer = RelationAnalyzer("./results")
    analyzer.export_to_neo4j_cypher("./results/neo4j_import.cypher")
    
    print("\n✓ Analysis complete!")
