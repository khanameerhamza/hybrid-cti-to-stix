# 🚀 QUICK START - Entity & Relationship Merger

## TL;DR

**One command to run:**

```bash
python merge_entity_relationship_data.py
```

**Output location:**

```
merged_final/all_documents_consolidated.json  ← Single file with everything!
```

---

## 📋 What It Does

Merges two model outputs:

1. **Entity Extraction** (`results/merged/`) - Entities, IOCs, TTPs
2. **Relationship Extraction** (`relationship/`) - Entity relationships

**Result:** Clean, validated JSON with entities + relationships

---

## ✅ Validation Rules (Simple Version)

| Scenario                          | Action                                |
| --------------------------------- | ------------------------------------- |
| Entity in **both** models         | ✓ Keep entity + relationships         |
| Entity **only** in entity model   | ✓ Keep entity, flag "needs relations" |
| Entity **only** in relation model | ✗ Reject (noise)                      |

---

## 📁 Output Files

```
merged_final/
├── all_documents_consolidated.json  ← All 49 docs in one file
├── APT28_merged.json               ← Individual doc results
├── APT29_merged.json
└── _merge_summary.json             ← Processing stats
```

---

## 🔍 Quick Queries

### Load All Data

```python
import json
with open('merged_final/all_documents_consolidated.json') as f:
    data = json.load(f)
```

### Find Tools Used by APT28

```python
doc = data['documents']['APT28.txt']
tools = [r['tail'] for r in doc['relationships']['validated_relations']
         if r['relation'] == 'uses' and 'Tool' in r['tail_type']]
print(tools)
```

### Get All IOCs

```python
iocs = doc['ioc_indicators']
print(f"IPs: {iocs['ips']}")
print(f"Domains: {iocs['domains']}")
print(f"Hashes: {iocs['hashes']}")
```

### Find Missing Relationships

```python
missing = doc['relationships']['entities_needing_relationship_extraction']
print(f"Entities needing relations: {missing}")
```

### Get MITRE ATT&CK TTPs

```python
for tech in doc['attack_ttps']['techniques']:
    print(f"{tech['code']}: {tech['name']}")
```

---

## 📊 JSON Structure (Simplified)

```json
{
  "documents": {
    "APT28.txt": {
      "entities": {
        "summary": { "total_entities": 45 },
        "detailed_list": [{ "text": "APT28", "type": "intrusion-set" }],
        "by_type": {
          "intrusion_sets": ["APT28"],
          "tools": ["XAgent", "Mimikatz"]
        }
      },
      "ioc_indicators": {
        "ips": ["1.2.3.4"],
        "domains": ["evil.com"]
      },
      "attack_ttps": {
        "techniques": [{ "code": "T1566", "name": "Phishing" }]
      },
      "relationships": {
        "validated_relations": [
          {
            "head": "APT28",
            "relation": "uses",
            "tail": "XAgent",
            "sentence_text": "APT28 uses XAgent malware..."
          }
        ],
        "entities_needing_relationship_extraction": ["Operation Pawn Storm"]
      }
    }
  }
}
```

---

## 🎯 Use Cases

| Task                | How                                                 |
| ------------------- | --------------------------------------------------- |
| **Knowledge Graph** | Use `validated_relations` to build nodes & edges    |
| **LLM Extraction**  | Use `entities_needing_relationship_extraction` list |
| **IOC Feed**        | Use `ioc_indicators` section                        |
| **TTP Mapping**     | Use `attack_ttps` section                           |
| **Threat Analysis** | Query relationships by type                         |

---

## 🔧 Configuration

Edit these in `merge_entity_relationship_data.py` if needed:

```python
RESULTS_FOLDER = "./results"           # Entity extraction location
RELATIONSHIP_FOLDER = "./relationship"  # Relationship extraction location
OUTPUT_FOLDER = "./merged_final"       # Output location
```

---

## 📈 Expected Results

| Metric                        | Value        |
| ----------------------------- | ------------ |
| Documents processed           | 49           |
| Entities per doc              | 30-50        |
| Relationships per doc         | 10-20        |
| Missing relationships per doc | 3-5          |
| Processing time               | ~1-2 minutes |

---

## 🆘 Troubleshooting

| Problem                 | Solution                                                   |
| ----------------------- | ---------------------------------------------------------- |
| "File not found"        | Check paths in script config                               |
| "No merged files"       | Run entity extraction first                                |
| "No relationship files" | Check file naming: `APT28.txt.json` → `APT28_results.json` |
| Too few relations       | Adjust `min_length` in validation logic                    |

---

## 📚 Documentation

- **WORKFLOW_README.md** - Complete workflow
- **MERGE_DOCUMENTATION.md** - Technical details
- **SYSTEM_ARCHITECTURE.md** - Visual diagrams
- **example_using_merged_data.py** - 8 usage examples

---

## ✨ Key Features

- ✅ **Validates** entities from multiple sources
- ✅ **Filters** noisy relationships
- ✅ **Identifies** missing relationships
- ✅ **Includes** IOCs and TTPs
- ✅ **Preserves** sentence context
- ✅ **Deduplicates** relations
- ✅ **Structures** consistent JSON

---

## 🎉 That's It!

**Run this:**

```bash
python merge_entity_relationship_data.py
```

**Get this:**

- ✓ 49 merged JSON files
- ✓ 1 consolidated JSON
- ✓ Validated entities + relationships
- ✓ IOCs + TTPs
- ✓ Ready for knowledge graphs

**Happy analyzing! 🛡️**
