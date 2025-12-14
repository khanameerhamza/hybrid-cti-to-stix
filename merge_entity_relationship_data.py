"""
Merge Entity and Relationship Extraction Results

This script merges:
1. Entity extraction results from results/merged/ folder (and related folders)
2. Relationship extraction results from relationship/ folder

It validates entities and creates comprehensive JSON outputs for each document.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import re


def normalize_path(path):
    """Normalize file paths by removing incorrect prefixes."""
    if not path:
        return path
    
    # Remove incorrect path prefixes
    path = path.replace('/Users/khanhamza/STIXnet/', './')
    path = path.replace('\\Users\\khanhamza\\STIXnet\\', './')
    
    # Ensure it starts with ./results/
    if not path.startswith('./results/'):
        if 'results/' in path:
            path = './' + path[path.index('results/'):]
    
    return path


def load_json_file(file_path):
    """Load JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  Warning: File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"  Warning: JSON decode error in {file_path}: {e}")
        return None


def load_entity_data(merged_file_path):
    """
    Load entity data from merged file and all related files (ioc, kb, novel, ttp).
    """
    merged_data = load_json_file(merged_file_path)
    if not merged_data:
        return None
    
    entity_data = {
        'file_name': merged_data.get('file', ''),
        'entities': merged_data.get('entities', {}),
        'attack': merged_data.get('attack', {}),
        'ioc_data': {},
        'kb_data': {},
        'novel_data': {},
        'ttp_data': {}
    }
    
    # Get provenance paths
    provenance = merged_data.get('provenance', {})
    
    # Load IOC data
    ioc_file = normalize_path(provenance.get('ioc_file', ''))
    if ioc_file:
        ioc_data = load_json_file(ioc_file)
        if ioc_data:
            entity_data['ioc_data'] = ioc_data.get('iocs', {})
    
    # Load KB data
    kb_file = normalize_path(provenance.get('kb_file', ''))
    if kb_file:
        kb_data = load_json_file(kb_file)
        if kb_data:
            entity_data['kb_data'] = kb_data.get('kb_matches', {})
    
    # Load Novel data
    novel_file = normalize_path(provenance.get('novel_file', ''))
    if novel_file:
        novel_data = load_json_file(novel_file)
        if novel_data:
            entity_data['novel_data'] = novel_data.get('novel_entities', {})
    
    # Load TTP data
    ttp_file = normalize_path(provenance.get('ttp_file', ''))
    if ttp_file:
        ttp_data = load_json_file(ttp_file)
        if ttp_data:
            entity_data['ttp_data'] = ttp_data
    
    return entity_data


def normalize_entity_text(text):
    """Normalize entity text for comparison."""
    if not text:
        return ""
    return text.lower().strip()


def extract_unique_entities_from_results(entity_data):
    """
    Extract unique entities from the entity extraction results.
    Returns a set of normalized entity texts and a detailed entity list.
    """
    unique_entities = set()
    detailed_entities = []
    
    if not entity_data:
        return unique_entities, detailed_entities
    
    # Extract from main entities section
    entities_section = entity_data.get('entities', {})
    
    for entity_type, entity_list in entities_section.items():
        if isinstance(entity_list, list):
            for entity in entity_list:
                if entity:
                    normalized = normalize_entity_text(str(entity))
                    unique_entities.add(normalized)
                    detailed_entities.append({
                        'text': str(entity),
                        'type': entity_type,
                        'source': 'merged'
                    })
    
    # Extract from KB matches
    kb_data = entity_data.get('kb_data', {})
    if isinstance(kb_data, dict):
        matches = kb_data.get('matches', [])
        for match in matches:
            if isinstance(match, dict):
                text = match.get('text', '') or match.get('canonical', '')
                if text:
                    normalized = normalize_entity_text(text)
                    unique_entities.add(normalized)
                    detailed_entities.append({
                        'text': text,
                        'type': match.get('type', 'unknown'),
                        'canonical': match.get('canonical', ''),
                        'external_id': match.get('external_id', ''),
                        'source': 'kb'
                    })
    
    # Extract from IOC data
    ioc_data = entity_data.get('ioc_data', {})
    for ioc_type, ioc_list in ioc_data.items():
        if isinstance(ioc_list, list) and ioc_list:
            for ioc in ioc_list:
                if ioc:
                    normalized = normalize_entity_text(str(ioc))
                    unique_entities.add(normalized)
                    detailed_entities.append({
                        'text': str(ioc),
                        'type': ioc_type,
                        'source': 'ioc'
                    })
    
    return unique_entities, detailed_entities


def clean_relationship_entity(text):
    """Clean up entity text from relationship extraction (remove extra words/tokens)."""
    if not text:
        return ""
    
    # Remove common artifacts
    text = text.strip()
    
    # Remove trailing punctuation and common words that shouldn't be part of entities
    text = re.sub(r'\s+(has|is|are|was|were|have|had|to|the|a|an|and|or|of|in|on|at|for|with|by)\s*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(has|is|are|was|were|have|had|to|the|a|an|and|or|of|in|on|at|for|with|by)\s+', '', text, flags=re.IGNORECASE)
    
    return text.strip()


def is_valid_entity(entity_text, min_length=2):
    """Check if entity text is valid (not just punctuation or short garbage)."""
    if not entity_text:
        return False
    
    cleaned = clean_relationship_entity(entity_text)
    if len(cleaned) < min_length:
        return False
    
    # Reject if it's just punctuation or common words
    if cleaned.lower() in ['of', 'to', 'the', 'a', 'an', 'and', 'or', 'has', 'is']:
        return False
    
    return True


def filter_and_validate_relations(relationship_data, valid_entities_normalized):
    """
    Filter relationships based on entity validation.
    Keep only relations where both head and tail entities are in the validated entity set.
    Extract from the sentences structure to get maximum details.
    """
    if not relationship_data:
        return [], [], {}
    
    validated_relations = []
    missing_entities = set()
    sentence_contexts = {}
    
    # Extract from sentences array structure (has more details)
    sentences = relationship_data.get('sentences', [])
    
    for sentence in sentences:
        sentence_id = sentence.get('sentence_id', 0)
        sentence_text = sentence.get('text', '')
        relations = sentence.get('relations', [])
        
        # Skip sentences without relations
        if not relations:
            continue
        
        # Process each relation in this sentence
        has_valid_relation = False
        for relation in relations:
            head = relation.get('head', '')
            tail = relation.get('tail', '')
            
            # Clean entity text
            head_cleaned = clean_relationship_entity(head)
            tail_cleaned = clean_relationship_entity(tail)
            
            # Check if valid
            if not is_valid_entity(head_cleaned) or not is_valid_entity(tail_cleaned):
                continue
            
            # Normalize for comparison
            head_normalized = normalize_entity_text(head_cleaned)
            tail_normalized = normalize_entity_text(tail_cleaned)
            
            # Check if both entities exist in validated set (partial match)
            head_found = any(head_normalized in valid_ent or valid_ent in head_normalized 
                            for valid_ent in valid_entities_normalized)
            tail_found = any(tail_normalized in valid_ent or valid_ent in tail_normalized 
                            for valid_ent in valid_entities_normalized)
            
            if head_found and tail_found:
                has_valid_relation = True
                
                # Keep this relation (without sentence text)
                validated_relations.append({
                    'head': head_cleaned,
                    'head_type': relation.get('head_type', ''),
                    'relation': relation.get('relation', ''),
                    'tail': tail_cleaned,
                    'tail_type': relation.get('tail_type', ''),
                    'sentence_id': sentence_id
                })
            else:
                # Track missing entities
                if not head_found:
                    missing_entities.add(head_cleaned)
                if not tail_found:
                    missing_entities.add(tail_cleaned)
        
        # Store sentence context only if it has valid relations
        if has_valid_relation and sentence_id and sentence_text:
            sentence_contexts[sentence_id] = sentence_text
    
    return validated_relations, list(missing_entities), sentence_contexts


def deduplicate_relations(relations):
    """Remove exact duplicate relations (same head, relation, tail, and types)."""
    seen = set()
    unique_relations = []
    
    for rel in relations:
        # Create key for deduplication - include relation type to keep bidirectional relations
        key = (
            rel['head'].lower(),
            rel['head_type'].lower(),
            rel['relation'].lower(),
            rel['tail'].lower(),
            rel['tail_type'].lower()
        )
        
        if key not in seen:
            seen.add(key)
            unique_relations.append(rel)
    
    return unique_relations


def create_relation_summary(relations):
    """Create summary statistics for relations."""
    if not relations:
        return {}
    
    relation_types = defaultdict(int)
    entity_pair_types = defaultdict(int)
    
    for rel in relations:
        relation_types[rel['relation']] += 1
        pair_key = f"{rel['head_type']} -> {rel['tail_type']}"
        entity_pair_types[pair_key] += 1
    
    return {
        'total_relations': len(relations),
        'unique_relation_types': len(relation_types),
        'relation_type_counts': dict(relation_types),
        'entity_pair_patterns': dict(entity_pair_types)
    }


def merge_document_data(merged_file_path, relationship_data, relationship_filename):
    """
    Merge entity and relationship data for a single document.
    """
    print(f"\nProcessing: {os.path.basename(merged_file_path)}")
    
    # Load entity data
    entity_data = load_entity_data(merged_file_path)
    if not entity_data:
        print(f"  ✗ Failed to load entity data")
        return None
    
    # Relationship data is now passed in
    if not relationship_data:
         relationship_data = {'all_relations': [], 'sentences': []}

    # Extract unique entities from entity extraction
    valid_entities_normalized, detailed_entities = extract_unique_entities_from_results(entity_data)
    
    # --- FIX: Also extract entities from Relationship Data (TIRE) ---
    # TIRE is a joint extractor, so it finds entities too. We should trust them.
    if relationship_data and 'all_entities' in relationship_data:
        for entity in relationship_data['all_entities']:
            text = entity.get('text')
            if text and is_valid_entity(text):
                normalized = normalize_entity_text(text)
                if normalized not in valid_entities_normalized:
                    valid_entities_normalized.add(normalized)
                    detailed_entities.append({
                        'text': text,
                        'type': entity.get('type', 'Unknown'),
                        'source': 'relationship_extraction'
                    })
    
    print(f"  Entities from extraction (inc. TIRE): {len(detailed_entities)}")
    print(f"  Unique entity texts: {len(valid_entities_normalized)}")
    
    # Filter and validate relationships
    validated_relations, missing_entities, sentence_contexts = filter_and_validate_relations(
        relationship_data, 
        valid_entities_normalized
    )

    # If no sentences with relations found, include all sentences for context
    if not sentence_contexts and relationship_data.get('sentences'):
        for sent in relationship_data['sentences']:
            s_id = sent.get('sentence_id')
            s_text = sent.get('text')
            if s_id and s_text:
                sentence_contexts[s_id] = s_text
    
    print(f"  Total relations extracted: {len(relationship_data.get('all_relations', []))}")
    print(f"  Validated relations: {len(validated_relations)}")
    print(f"  Missing entities: {len(missing_entities)}")
    
    # Deduplicate relations
    unique_relations = deduplicate_relations(validated_relations)
    print(f"  Unique relations after deduplication: {len(unique_relations)}")
    
    # Create merged output
    merged_output = {
        'document_name': entity_data['file_name'],
        'metadata': {
            'source_files': {
                'entity_extraction': os.path.basename(merged_file_path),
                'relationship_extraction': relationship_filename
            },
            'extraction_timestamp': relationship_data.get('document_name', ''),
            'total_sentences': relationship_data.get('total_sentences', 0)
        },
        'entities': {
            'summary': {
                'total_entities': len(detailed_entities),
                'unique_entity_texts': len(valid_entities_normalized),
                'by_source': {
                    'merged': len([e for e in detailed_entities if e['source'] == 'merged']),
                    'kb': len([e for e in detailed_entities if e['source'] == 'kb']),
                    'ioc': len([e for e in detailed_entities if e['source'] == 'ioc'])
                }
            },
            'detailed_list': detailed_entities,
            'by_type': entity_data['entities']
        },
        'attack_ttps': {
            'tactics': entity_data['attack'].get('tactics', []),
            'techniques': entity_data['attack'].get('techniques', [])
        },
        'ioc_indicators': entity_data['ioc_data'],
        'sentences': sentence_contexts,
        'relationships': {
            'summary': create_relation_summary(unique_relations),
            'validated_relations': unique_relations,
            'entities_needing_relationship_extraction': missing_entities
        }
    }
    
    return merged_output


def process_all_documents(results_folder, relationship_folder, output_folder):
    """
    Process all documents and create merged JSON files.
    """
    print("\n" + "="*80)
    print("MERGING ENTITY AND RELATIONSHIP EXTRACTION RESULTS")
    print("="*80)
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all merged files
    merged_path = Path(results_folder) / 'merged'
    merged_files = sorted(list(merged_path.glob("*.txt.json")))
    
    if not merged_files:
        print(f"\n✗ No files found in {merged_path}")
        return
    
    print(f"\nFound {len(merged_files)} documents to process")
    
    # Track statistics
    all_docs_summary = {
        'total_documents': len(merged_files),
        'processed_successfully': 0,
        'failed': 0,
        'documents': []
    }
    
    # Process each document
    for merged_file in merged_files:
        # Determine corresponding relationship file
        base_name = merged_file.stem.replace('.txt', '')  # Remove .txt from .txt.json
        relationship_file = Path(relationship_folder) / f"{base_name}_results.json"
        
        relationship_data = None
        relationship_filename = "MISSING"
        
        if relationship_file.exists():
            relationship_data = load_json_file(str(relationship_file))
            relationship_filename = relationship_file.name
        else:
            print(f"\n⚠ Relationship file not found for {base_name}. Proceeding with entities only.")
            
            # Fallback: Try to load sentences from raw text
            raw_text_file = Path("Data") / f"{base_name}.txt"
            sentences = []
            if raw_text_file.exists():
                try:
                    text = raw_text_file.read_text(encoding='utf-8')
                    # Simple sentence splitting
                    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
                    for i, s in enumerate(raw_sentences):
                        if s.strip():
                            sentences.append({
                                "sentence_id": i+1,
                                "text": s.strip(),
                                "relations": []
                            })
                except Exception as e:
                    print(f"  Warning: Could not read raw text file: {e}")

            relationship_data = {
                'document_name': base_name,
                'total_sentences': len(sentences),
                'sentences': sentences,
                'all_relations': []
            }

        try:
            # Merge data
            merged_data = merge_document_data(str(merged_file), relationship_data, relationship_filename)
            
            if merged_data:
                # Save output
                output_file = Path(output_folder) / f"{base_name}_merged.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(merged_data, f, indent=2, ensure_ascii=False)
                
                print(f"  ✓ Saved to: {output_file.name}")
                
                all_docs_summary['processed_successfully'] += 1
                all_docs_summary['documents'].append({
                    'name': base_name,
                    'status': 'success',
                    'entities': merged_data['entities']['summary']['total_entities'],
                    'relations': merged_data['relationships']['summary']['total_relations'],
                    'missing_entities': len(merged_data['relationships']['entities_needing_relationship_extraction'])
                })
            else:
                all_docs_summary['failed'] += 1
                all_docs_summary['documents'].append({
                    'name': base_name,
                    'status': 'failed',
                    'reason': 'merge_failed'
                })
        
        except Exception as e:
            print(f"  ✗ Error processing {base_name}: {str(e)}")
            all_docs_summary['failed'] += 1
            all_docs_summary['documents'].append({
                'name': base_name,
                'status': 'failed',
                'reason': str(e)
            })
    
    # Save summary
    summary_file = Path(output_folder) / "_merge_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_docs_summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("MERGE COMPLETE!")
    print("="*80)
    print(f"Successfully processed: {all_docs_summary['processed_successfully']}")
    print(f"Failed: {all_docs_summary['failed']}")
    print(f"Output folder: {output_folder}")
    print(f"Summary file: {summary_file.name}")
    print("="*80 + "\n")


def create_consolidated_output(output_folder):
    """
    Create a single consolidated JSON with all documents.
    """
    print("\nCreating consolidated JSON file...")
    
    output_path = Path(output_folder)
    merged_files = sorted(list(output_path.glob("*_merged.json")))
    
    if not merged_files:
        print("  No merged files found to consolidate")
        return
    
    consolidated = {
        'metadata': {
            'total_documents': len(merged_files),
            'description': 'Consolidated entity and relationship extraction from all CTI documents'
        },
        'documents': {}
    }
    
    for merged_file in merged_files:
        data = load_json_file(str(merged_file))
        if data:
            doc_name = data['document_name']
            consolidated['documents'][doc_name] = data
    
    # Save consolidated file
    consolidated_file = output_path / "all_documents_consolidated.json"
    with open(consolidated_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Created consolidated file: {consolidated_file.name}")
    print(f"  Contains {len(consolidated['documents'])} documents")


if __name__ == "__main__":
    # Configuration
    RESULTS_FOLDER = "./results"
    RELATIONSHIP_FOLDER = "./relationship"
    OUTPUT_FOLDER = "./merged_final"
    
    # Process all documents
    process_all_documents(RESULTS_FOLDER, RELATIONSHIP_FOLDER, OUTPUT_FOLDER)
    
    # Create consolidated output
    create_consolidated_output(OUTPUT_FOLDER)
    
    print("\n✓ All processing complete!")
    print(f"✓ Individual merged files: {OUTPUT_FOLDER}/<document>_merged.json")
    print(f"✓ Consolidated file: {OUTPUT_FOLDER}/all_documents_consolidated.json")
