# Entity-Relationship Merger Documentation

## Overview

This script merges entity extraction results from two different models:

1. **Entity Extraction Model** - Results in `results/merged/` folder
2. **Relationship Extraction Model** - Results in `relationship/` folder

## Purpose

The merger validates entities and relationships to create a comprehensive, accurate JSON output that:

- Contains all validated entities from the entity extraction model
- Includes only relationships where both entities are validated
- Identifies entities that need relationship extraction
- Removes noisy/invalid relationships
- Provides complete context from both models

## Input Structure

### Entity Extraction Files (results/merged/\*.txt.json)

```json
{
  "file": "Andariel.txt",
  "entities": {
    "intrusion_sets": ["Andariel", "Lazarus Group"],
    "malware": [],
    "tools": ["Tasklist", "netstat"],
    "campaigns": ["Operation Black Mine"],
    "nationalities": ["north korea"],
    "urls": [],
    "domains": [],
    "ips": [],
    "hashes": [],
    "emails": [],
    "file_paths": [],
    "cves": []
  },
  "attack": {
    "tactics": [],
    "techniques": [{ "code": "T1587", "name": "Exploits" }]
  },
  "provenance": {
    "ioc_file": "./results/ioc/Andariel.txt.txt.json",
    "kb_file": "./results/kb/Andariel.txt.json",
    "novel_file": "./results/novel/Andariel.txt.json",
    "ttp_file": "./results/attack_ttp/Andariel.txt.ttps.json"
  }
}
```

Additional files referenced in provenance:

- **ioc_file** - IOC indicators (IPs, domains, hashes, etc.)
- **kb_file** - Knowledge base matches (canonical names, external IDs)
- **novel_file** - Novel entities discovered
- **ttp_file** - MITRE ATT&CK tactics and techniques

### Relationship Extraction Files (relationship/\*\_results.json)

```json
{
  "document_name": "Andariel.txt",
  "total_sentences": 17,
  "all_entities": [
    {
      "text": "Andariel",
      "type": "HackOrg",
      "start": 2,
      "end": 4,
      "sentence_id": 1,
      "sentence_text": "..."
    }
  ],
  "all_relations": [
    {
      "head": "Andariel",
      "head_type": "HackOrg",
      "relation": "uses",
      "tail": "XAgent",
      "tail_type": "Tool",
      "sentence_id": 5,
      "sentence_text": "..."
    }
  ],
  "entity_counts": {...},
  "relation_counts": {...}
}
```

## Validation Rules

### Rule 1: Entity Validation

**If entity is in entity extraction results but NOT in relationship results:**

- Entity is included in final output
- Entity is flagged in `entities_needing_relationship_extraction`
- LLM should extract relationships for this entity

**Example:**

```json
"entities_needing_relationship_extraction": [
  "Operation Black Mine",  // In entity results but no relations found
  "Campaign Rifle"
]
```

### Rule 2: Relationship Validation

**If entity is in relationship results but NOT in entity extraction results:**

- Relationship is REJECTED
- Entity is not considered valid
- Prevents noisy/incorrect extractions

**Example - Rejected:**

```json
// This relation is rejected because "included" is not a valid entity
{
  "head": "Andariel has", // Valid entity
  "relation": "uses",
  "tail": "included" // NOT in entity extraction - REJECTED
}
```

### Rule 3: Entity Cleaning

Relationships often contain artifacts. The script cleans:

- Extra words: "Andariel has" → "Andariel"
- Punctuation: "agencies," → "agencies"
- Common words: "of", "the", "to", etc.

### Rule 4: Partial Matching

Allows fuzzy matching for entity validation:

- "Andariel" matches "Andariel has"
- "Operation Black Mine" matches "Black Mine"
- Accounts for tokenization differences

## Output Structure

### Individual Document Output (<document>\_merged.json)

```json
{
  "document_name": "Andariel.txt",
  "metadata": {
    "source_files": {
      "entity_extraction": "Andariel.txt.json",
      "relationship_extraction": "Andariel_results.json"
    },
    "extraction_timestamp": "...",
    "total_sentences": 17
  },
  "entities": {
    "summary": {
      "total_entities": 45,
      "unique_entity_texts": 32,
      "by_source": {
        "merged": 28,
        "kb": 15,
        "ioc": 2
      }
    },
    "detailed_list": [
      {
        "text": "Andariel",
        "type": "intrusion-set",
        "canonical": "Andariel",
        "external_id": "G0138",
        "source": "kb"
      },
      {
        "text": "Tasklist",
        "type": "tools",
        "source": "merged"
      }
    ],
    "by_type": {
      "intrusion_sets": ["Andariel", "Lazarus Group"],
      "tools": ["Tasklist", "netstat"],
      "campaigns": ["Operation Black Mine"],
      "nationalities": ["north korea"]
    }
  },
  "attack_ttps": {
    "tactics": [],
    "techniques": [{ "code": "T1587", "name": "Exploits", "score": null }]
  },
  "ioc_indicators": {
    "urls": [],
    "domains": [],
    "ips": [],
    "hashes": [],
    "cves": []
  },
  "relationships": {
    "summary": {
      "total_relations": 15,
      "unique_relation_types": 5,
      "relation_type_counts": {
        "uses": 8,
        "targets": 5,
        "associatedWith": 2
      },
      "entity_pair_patterns": {
        "HackOrg -> Tool": 8,
        "HackOrg -> Org": 5
      }
    },
    "validated_relations": [
      {
        "head": "Andariel",
        "head_type": "HackOrg",
        "relation": "uses",
        "tail": "Tasklist",
        "tail_type": "Tool",
        "sentence_id": 15,
        "sentence_text": "Andariel has used tasklist...",
        "validated": true
      }
    ],
    "entities_needing_relationship_extraction": [
      "Operation Black Mine",
      "Campaign Rifle"
    ]
  }
}
```

### Consolidated Output (all_documents_consolidated.json)

Contains all documents in a single file:

```json
{
  "metadata": {
    "total_documents": 49,
    "description": "Consolidated entity and relationship extraction from all CTI documents"
  },
  "documents": {
    "Andariel.txt": {
      /* full document data */
    },
    "APT28.txt": {
      /* full document data */
    }
    // ... all documents
  }
}
```

## Usage

### Run the Merger

```bash
python merge_entity_relationship_data.py
```

### Output Files

```
merged_final/
├── _merge_summary.json                    # Processing statistics
├── all_documents_consolidated.json        # All documents in one file
├── Andariel_merged.json                   # Individual merged results
├── APT28_merged.json
├── APT29_merged.json
└── ... (one per document)
```

### Processing Statistics

The `_merge_summary.json` contains:

```json
{
  "total_documents": 49,
  "processed_successfully": 47,
  "failed": 2,
  "documents": [
    {
      "name": "Andariel",
      "status": "success",
      "entities": 45,
      "relations": 15,
      "missing_entities": 3
    }
  ]
}
```

## Key Features

### ✅ Entity Validation

- Only validated entities from entity extraction model
- Cross-references with KB, IOC, and novel entity sources
- Tracks canonical names and external IDs

### ✅ Relationship Filtering

- Removes relationships with invalid entities
- Cleans entity text (removes artifacts)
- Deduplicates relationships
- Maintains sentence context

### ✅ Missing Entity Detection

- Identifies entities without relationships
- Flags them for additional extraction
- Helps improve coverage

### ✅ Comprehensive Context

- Includes attack TTPs (MITRE ATT&CK)
- IOC indicators (IPs, domains, hashes)
- Knowledge base mappings
- Full sentence context for relations

### ✅ Multiple Output Formats

- Individual document JSONs (detailed)
- Consolidated JSON (all documents)
- Summary statistics

## Analysis Examples

### Query Validated Relations

```python
import json

# Load merged document
with open('merged_final/APT28_merged.json') as f:
    data = json.load(f)

# Get all tools used
tools_used = [r for r in data['relationships']['validated_relations']
              if r['relation'] == 'uses' and r['tail_type'] == 'Tool']

print(f"Found {len(tools_used)} tools")
for rel in tools_used:
    print(f"  {rel['head']} uses {rel['tail']}")
```

### Find Entities Needing Relations

```python
# Load consolidated data
with open('merged_final/all_documents_consolidated.json') as f:
    all_data = json.load(f)

# Find all entities needing relationship extraction
for doc_name, doc_data in all_data['documents'].items():
    missing = doc_data['relationships']['entities_needing_relationship_extraction']
    if missing:
        print(f"\n{doc_name}: {len(missing)} entities need relations")
        for entity in missing[:5]:
            print(f"  - {entity}")
```

### Get Entity Statistics

```python
# Load merged document
with open('merged_final/APT28_merged.json') as f:
    data = json.load(f)

# Entity summary
summary = data['entities']['summary']
print(f"Total entities: {summary['total_entities']}")
print(f"From merged: {summary['by_source']['merged']}")
print(f"From KB: {summary['by_source']['kb']}")
print(f"From IOC: {summary['by_source']['ioc']}")

# Relation summary
rel_summary = data['relationships']['summary']
print(f"\nTotal relations: {rel_summary['total_relations']}")
print(f"Relation types: {rel_summary['unique_relation_types']}")
```

## Benefits

1. **Accuracy** - Only validated entities and relationships
2. **Completeness** - All entity sources (merged, KB, IOC, novel)
3. **Context** - Sentence-level context for relationships
4. **Actionable** - Identifies missing relationships
5. **Structured** - Consistent JSON format for all documents
6. **Scalable** - Processes all documents automatically

## Next Steps

### Use with LLM

Pass the `entities_needing_relationship_extraction` list to an LLM to extract missing relationships:

```python
missing_entities = data['relationships']['entities_needing_relationship_extraction']
prompt = f"Extract relationships for these entities: {', '.join(missing_entities)}"
```

### Build Knowledge Graph

Use validated relations to build a graph:

```python
for rel in validated_relations:
    graph.add_edge(rel['head'], rel['tail'],
                   relation=rel['relation'],
                   sentence=rel['sentence_text'])
```

### Export to Database

Load into Neo4j, ArangoDB, or other graph database:

```cypher
// Neo4j import
CREATE (a:Entity {name: $head, type: $head_type})
CREATE (b:Entity {name: $tail, type: $tail_type})
CREATE (a)-[r:RELATION {type: $relation}]->(b)
```
