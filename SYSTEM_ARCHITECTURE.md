# Visual System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INPUT: CTI DOCUMENTS                                │
│                    (APT28.txt, APT29.txt, etc.)                              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   ENTITY EXTRACTION       │   │  RELATIONSHIP EXTRACTION  │
│   (Pre-existing Model)    │   │  (TIRE Model)             │
└──────────┬────────────────┘   └──────────┬────────────────┘
           │                               │
           ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│  results/                 │   │  relationship/            │
│  ├── merged/              │   │  ├── APT28_results.json   │
│  │   └── APT28.txt.json  │   │  ├── APT29_results.json   │
│  ├── ioc/                 │   │  └── ...                  │
│  ├── kb/                  │   └───────────────────────────┘
│  ├── novel/               │
│  └── attack_ttp/          │
└──────────┬────────────────┘
           │
           └───────────────────────┐
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │  merge_entity_relationship_data.py│
                    │                                   │
                    │  VALIDATION RULES:                │
                    │  1. Entity in Entity Model only   │
                    │     → Flag for LLM extraction     │
                    │  2. Entity in Relation Model only │
                    │     → REJECT relationship         │
                    │                                   │
                    │  PROCESSING:                      │
                    │  ✓ Load all entity sources        │
                    │  ✓ Load all relationships         │
                    │  ✓ Validate entities              │
                    │  ✓ Filter relationships           │
                    │  ✓ Clean entity text              │
                    │  ✓ Deduplicate relations          │
                    │  ✓ Identify missing relations     │
                    └───────────┬──────────────────────┘
                                │
                                ▼
                    ┌───────────────────────────────────┐
                    │       OUTPUT: merged_final/       │
                    │                                   │
                    │  Individual Files:                │
                    │  ├── APT28_merged.json            │
                    │  ├── APT29_merged.json            │
                    │  └── ...                          │
                    │                                   │
                    │  Consolidated:                    │
                    │  └── all_documents_consolidated.json│
                    │                                   │
                    │  Summary:                         │
                    │  └── _merge_summary.json          │
                    └───────────┬───────────────────────┘
                                │
                                ▼
        ┌───────────────────────┴────────────────────────┐
        │                                                 │
        ▼                                                 ▼
┌──────────────────────┐                    ┌──────────────────────┐
│   USE CASES          │                    │   ANALYSIS           │
│                      │                    │                      │
│  • Knowledge Graphs  │                    │  • Query entities    │
│  • LLM Integration   │                    │  • Find patterns     │
│  • Threat Intel      │                    │  • Compare actors    │
│  • IOC Extraction    │                    │  • Extract TTPs      │
│  • Database Import   │                    │  • Build graphs      │
└──────────────────────┘                    └──────────────────────┘
```

## Data Flow Detail

```
Entity Extraction Results                 Relationship Results
        │                                         │
        │  entities: {                            │  all_relations: [
        │    intrusion_sets: ["APT28"]            │    {
        │    tools: ["XAgent", "Mimikatz"]        │      head: "APT28",
        │    campaigns: ["Pawn Storm"]            │      relation: "uses",
        │  }                                       │      tail: "XAgent"
        │  iocs: {                                 │    },
        │    ips: ["1.2.3.4"]                      │    {
        │    domains: ["evil.com"]                 │      head: "APT28",
        │  }                                       │      relation: "uses",
        │  attack_ttps: {                          │      tail: "bad_tool"  ← NOT IN ENTITIES!
        │    techniques: ["T1566"]                 │    }
        │  }                                       │  ]
        │                                         │
        └────────────┬────────────────────────────┘
                     │
                     ▼
              MERGE & VALIDATE
                     │
                     ├─→ Validate "APT28" ✓
                     ├─→ Validate "XAgent" ✓
                     ├─→ Validate "bad_tool" ✗ (REJECT relation)
                     ├─→ Check "Pawn Storm" → NO RELATIONS FOUND
                     │   → Add to entities_needing_relationship_extraction
                     │
                     ▼
              MERGED OUTPUT
              {
                entities: {
                  detailed_list: [
                    {text: "APT28", type: "intrusion-set", source: "kb"},
                    {text: "XAgent", type: "tools", source: "merged"},
                    {text: "Pawn Storm", type: "campaigns", source: "merged"}
                  ]
                },
                ioc_indicators: {
                  ips: ["1.2.3.4"],
                  domains: ["evil.com"]
                },
                attack_ttps: {
                  techniques: [{code: "T1566", name: "Phishing"}]
                },
                relationships: {
                  validated_relations: [
                    {
                      head: "APT28",
                      relation: "uses",
                      tail: "XAgent",
                      validated: true
                    }
                    // "bad_tool" relation REJECTED
                  ],
                  entities_needing_relationship_extraction: [
                    "Pawn Storm"  // Has no relations yet
                  ]
                }
              }
```

## Validation Logic Flow

```
For each Relationship:
    │
    ├─→ Clean entity text
    │   "APT28 has" → "APT28"
    │   "agencies," → "agencies"
    │
    ├─→ Check if HEAD entity exists in validated entity set
    │   │
    │   ├─→ YES: Continue
    │   └─→ NO: REJECT relationship, track missing entity
    │
    ├─→ Check if TAIL entity exists in validated entity set
    │   │
    │   ├─→ YES: Continue
    │   └─→ NO: REJECT relationship, track missing entity
    │
    └─→ Both entities validated?
        │
        ├─→ YES: Add to validated_relations
        └─→ NO: Discard relationship

For each Entity in Entity Extraction:
    │
    └─→ Check if entity has any relationships
        │
        ├─→ YES: Entity is complete
        └─→ NO: Add to entities_needing_relationship_extraction
```

## Output JSON Structure

```
<document>_merged.json
│
├── metadata
│   ├── source_files
│   ├── extraction_timestamp
│   └── total_sentences
│
├── entities
│   ├── summary
│   │   ├── total_entities
│   │   ├── unique_entity_texts
│   │   └── by_source {merged, kb, ioc}
│   │
│   ├── detailed_list [array]
│   │   ├── {text, type, source}
│   │   ├── {text, type, canonical, external_id, source}
│   │   └── ...
│   │
│   └── by_type
│       ├── intrusion_sets: [...]
│       ├── tools: [...]
│       ├── campaigns: [...]
│       └── ...
│
├── attack_ttps
│   ├── tactics: [...]
│   └── techniques: [{code, name, score}]
│
├── ioc_indicators
│   ├── ips: [...]
│   ├── domains: [...]
│   ├── hashes: [...]
│   ├── cves: [...]
│   └── ...
│
└── relationships
    ├── summary
    │   ├── total_relations
    │   ├── unique_relation_types
    │   ├── relation_type_counts: {...}
    │   └── entity_pair_patterns: {...}
    │
    ├── validated_relations [array]
    │   ├── {head, head_type, relation, tail, tail_type,
    │   │    sentence_id, sentence_text, validated}
    │   └── ...
    │
    └── entities_needing_relationship_extraction [array]
        ├── "Operation Pawn Storm"
        ├── "Campaign X"
        └── ...
```

## Processing Statistics

```
Input:
  • 49 CTI documents
  • ~800 sentences total
  • 2 extraction models (Entity + Relationship)

Processing:
  • Load ~49 entity JSONs (merged + ioc + kb + novel + ttp)
  • Load ~49 relationship JSONs
  • Cross-validate ~2000 entities
  • Filter ~1500 relationships
  • Identify ~300 missing relationships

Output:
  • 49 individual merged JSONs (~50-100 KB each)
  • 1 consolidated JSON (~3-5 MB)
  • 1 summary JSON
  • ~30-50 validated entities per document
  • ~10-20 validated relationships per document
  • ~3-5 entities needing relationships per document
```

## Example: APT28 Processing

```
INPUT FILES:
  results/merged/APT28.txt.json
  results/ioc/APT28.txt.txt.json
  results/kb/APT28.txt.json
  results/novel/APT28.txt.json
  results/attack_ttp/APT28.txt.ttps.json
  relationship/APT28_results.json

ENTITIES EXTRACTED:
  From merged: APT28, XAgent, Mimikatz, US Government
  From kb: APT28 (G0028), Fancy Bear, Sofacy
  From ioc: evil.com, 192.168.1.1
  From ttp: T1566 (Phishing), T1059 (Command Execution)

  Total: 45 entities

RELATIONSHIPS EXTRACTED:
  Total in relationship JSON: 67
  After validation: 18
  Rejected: 49 (invalid entities, noise)

MISSING RELATIONSHIPS:
  "Operation Pawn Storm" - no relations found
  "Fancy Bear" - no relations found
  "Sofacy" - no relations found

OUTPUT:
  merged_final/APT28_merged.json
    • 45 validated entities
    • 18 validated relationships
    • 3 entities needing relationship extraction
    • Full IOC and TTP coverage
```

---

This visual guide shows the complete data flow from raw CTI documents through entity extraction, relationship extraction, validation, and final merged output!



After having put the csv's of mitre's open source Knowledge Base, the dataset of Stixnet downloaded, installing all the requirements and training the models(Highly recommend to use GPU for training).
run the implementation using the following commands:

For batch processing with the Dataset being in the main directory in a folder named Data:
(base) khanhamza@Ameers-MacBook-Air new_version 2 copy % python main_pipeline.py

Note: the project directory was named "new_version 2 copy" in my system.


For single cti report processing i had a web app developed which you can run with the following command:
(base) khanhamza@Ameers-MacBook-Air new_version 2 % streamlit run app.py






