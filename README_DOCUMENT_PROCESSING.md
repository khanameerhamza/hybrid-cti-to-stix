# TIRE Model - Document Processing System

This system processes cyber threat intelligence documents, extracting entities and relationships sentence by sentence using the TIRE model.

## Files Overview

- **`run_tire.py`** - Core TIRE model implementation (loads model and makes predictions)
- **`process_documents.py`** - Batch document processing script (main implementation)
- **`example_single_document.py`** - Example script for processing a single document
- **`config.json`** - Model configuration (entity types, relation types, etc.)
- **`model_weights.pth`** - Trained model weights
- **`Data/`** - Folder containing cyber threat intelligence documents (.txt files)

## Quick Start

### 1. Process All Documents

To process all documents in the `Data` folder:

```bash
python process_documents.py
```

This will:

- Split each document into sentences
- Extract entities and relationships from each sentence
- Save results as JSON files in the `results/` folder
- Create a summary file with aggregate statistics
- Generate a CSV file with all extracted relations

### 2. Process a Single Document (Example)

To test with a single document:

```bash
python example_single_document.py
```

Edit the `DOCUMENT_PATH` variable in the script to test different documents.

### 3. Use the Model Directly

```python
from run_tire import load_model_from_zip, predict

# Load model
model, config = load_model_from_zip(".")

# Process a sentence
text = "APT28 uses XAgent malware to target government networks."
entities, relations = predict(text, model, config)

print("Entities:", entities)
print("Relations:", relations)
```

## Output Format

### Individual Document Results (`{document_name}_results.json`)

```json
{
  "document_name": "APT28.txt",
  "total_sentences": 45,
  "sentences": [
    {
      "sentence_id": 1,
      "text": "APT28 is a threat group...",
      "entities": [...],
      "relations": [...],
      "entity_count": 5,
      "relation_count": 3
    }
  ],
  "all_entities": [
    {
      "text": "APT28",
      "type": "HackOrg",
      "start": 0,
      "end": 5,
      "sentence_id": 1,
      "sentence_text": "..."
    }
  ],
  "all_relations": [
    {
      "head": "APT28",
      "head_type": "HackOrg",
      "relation": "uses",
      "tail": "XAgent",
      "tail_type": "Tool",
      "sentence_id": 1,
      "sentence_text": "..."
    }
  ],
  "entity_counts": {
    "HackOrg": 15,
    "Tool": 8,
    "Org": 12
  },
  "relation_counts": {
    "uses": 10,
    "targets": 8,
    "associatedWith": 3
  }
}
```

### Aggregate Summary (`_all_documents_summary.json`)

Contains statistics across all processed documents:

- Total documents, sentences, entities, relations
- Per-document breakdown
- Aggregate entity and relation type counts

### Relations CSV (`extracted_relations.csv`)

A flat CSV file with all relations for easy analysis:

| document  | sentence_id | head_entity | head_type | relation | tail_entity | tail_type | sentence      |
| --------- | ----------- | ----------- | --------- | -------- | ----------- | --------- | ------------- |
| APT28.txt | 1           | APT28       | HackOrg   | uses     | XAgent      | Tool      | APT28 uses... |

## Entity Types

The model recognizes these entity types:

- **HackOrg** - Hacking organizations/threat actors
- **Tool** - Malware, software tools
- **Org** - Target organizations
- **Area** - Geographic locations
- **Time** - Temporal expressions
- **Way** - Attack methods/techniques
- **Purp** - Purpose/motivation
- **Features** - Technical features
- **OffAct** - Offensive actions
- **SecTeam** - Security teams
- **Exp** - Exploits/vulnerabilities
- **SamFile** - Sample files

## Relation Types

The model extracts these relationships:

- **uses** - Entity uses a tool/technique
- **targets** - Entity targets an organization/system
- **locatedAt** - Geographic location
- **hasAttackTime** - Temporal information
- **associatedWith** - Association between entities
- **discovers** - Discovery relationship
- **monitors** - Monitoring relationship
- **motivates** - Motivation relationship
- And more...

## Advanced Usage

### Custom Output Folder

```python
from process_documents import process_all_documents, load_model_from_zip

model, config = load_model_from_zip(".")
process_all_documents(
    data_folder="./Data",
    output_folder="./custom_results",
    model=model,
    config=config
)
```

### Debug Mode

Enable detailed output to see tokenization and prediction details:

```python
process_all_documents(
    data_folder="./Data",
    output_folder="./results",
    model=model,
    config=config,
    debug=True  # Enable debug output
)
```

### Process Specific Documents

```python
from process_documents import process_document, load_model_from_zip

model, config = load_model_from_zip(".")

# Process specific documents
documents = ["APT28.txt", "APT29.txt", "Dragonfly.txt"]
for doc in documents:
    results = process_document(f"./Data/{doc}", model, config)
    # Do something with results
```

## Use Cases for Extracted Relations

The structured JSON and CSV outputs are ideal for:

1. **Knowledge Graph Construction** - Build a graph database of threat intelligence
2. **Threat Intelligence Analysis** - Analyze attack patterns and TTPs
3. **Attribution Analysis** - Link threat actors to tools and targets
4. **Timeline Construction** - Build temporal attack sequences
5. **IOC Extraction** - Extract indicators of compromise
6. **Report Generation** - Automated threat intelligence reports
7. **Machine Learning** - Training data for further ML models
8. **Visualization** - Create network graphs of threat relationships

## Example Analysis Queries

With the JSON output, you can easily query:

```python
import json

# Load results
with open('results/APT28_results.json') as f:
    data = json.load(f)

# Find all tools used by APT28
tools = [r for r in data['all_relations']
         if r['relation'] == 'uses' and r['tail_type'] == 'Tool']

# Find all targeted organizations
targets = [r for r in data['all_relations']
           if r['relation'] == 'targets' and r['tail_type'] == 'Org']

# Get most common relationships
from collections import Counter
rel_counts = Counter(r['relation'] for r in data['all_relations'])
print(rel_counts.most_common(5))
```

## Troubleshooting

### Missing Dependencies

Install required packages:

```bash
pip install torch transformers torchcrf
```

### Memory Issues

If processing large documents causes memory issues:

1. Process documents one at a time
2. Reduce batch size (if applicable)
3. Use CPU instead of GPU for inference

### Sentence Splitting Issues

The sentence splitter handles most cases, but you may need to adjust for:

- Domain-specific abbreviations
- Unusual punctuation patterns

Edit the `split_into_sentences()` function in `process_documents.py` to customize.

## Performance

- Processing time: ~0.5-2 seconds per sentence (CPU)
- Typical document: 20-50 sentences
- Expected throughput: 1-2 minutes per document

## License & Citation

If you use this system, please cite the original TIRE model paper and acknowledge the creators.
