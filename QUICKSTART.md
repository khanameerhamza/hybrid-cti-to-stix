# Quick Start Guide - TIRE Document Processing

## Step-by-Step Instructions

### 1. Install Dependencies

```bash
pip install torch transformers pytorch-crf matplotlib networkx pandas
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### 2. Verify Your Setup

Make sure you have these files in your folder:

- ✅ `config.json` - Model configuration
- ✅ `model_weights.pth` - Trained model weights
- ✅ `Data/` folder - Contains .txt documents to process
- ✅ `run_tire.py` - Core model code
- ✅ `process_documents.py` - Main processing script

### 3. Run the Processing

#### Option A: Process All Documents (Recommended)

```bash
python process_documents.py
```

This will:

- Process all .txt files in the `Data/` folder
- Create a `results/` folder with JSON outputs
- Generate a summary file and CSV export

**Expected Output:**

```
results/
├── _all_documents_summary.json
├── extracted_relations.csv
├── APT28_results.json
├── APT29_results.json
├── ALLANITE_results.json
└── ... (one JSON per document)
```

#### Option B: Test with Single Document First

```bash
python example_single_document.py
```

This processes just one document (ALLANITE.txt by default) to verify everything works.

### 4. Analyze Results (Optional)

```bash
python analyze_results.py
```

This will:

- Show statistics about extracted entities and relations
- Create a knowledge graph JSON
- Export Neo4j import file

### 5. Create Visualizations (Optional)

```bash
python visualize_results.py
```

This creates:

- Entity distribution bar chart
- Relation distribution chart
- Document statistics comparison
- Network graph visualization

## Expected Processing Time

- **Small documents (10-20 sentences)**: ~20-40 seconds
- **Medium documents (30-50 sentences)**: ~1-2 minutes
- **All 49 documents**: ~30-60 minutes (depending on your CPU)

## Troubleshooting

### Issue: Module not found

**Solution:** Install missing dependencies

```bash
pip install torch transformers pytorch-crf
```

### Issue: Out of memory

**Solution:** Process documents one at a time:

```python
from process_documents import process_document, load_model_from_zip

model, config = load_model_from_zip(".")
result = process_document("./Data/APT28.txt", model, config)
```

### Issue: Sentence splitting problems

**Solution:** Edit the `split_into_sentences()` function in `process_documents.py` to handle your specific document format.

### Issue: Slow processing

**Solution:** This is normal on CPU. Each sentence takes 0.5-2 seconds. If you have a CUDA GPU, the model will automatically use it for faster processing.

## What You Get

### 1. Individual Document Results (`{name}_results.json`)

Complete extraction for each document:

- All sentences split from the document
- Entities found in each sentence
- Relations extracted from each sentence
- Aggregate counts and statistics

### 2. Relations CSV (`extracted_relations.csv`)

A flat file with all relations for easy analysis in Excel/Pandas:

```csv
document,sentence_id,head_entity,head_type,relation,tail_entity,tail_type,sentence
APT28.txt,1,APT28,HackOrg,uses,XAgent,Tool,"APT28 uses XAgent..."
```

### 3. Summary File (`_all_documents_summary.json`)

Overview of all processed documents:

- Total counts across all documents
- Per-document breakdown
- Aggregate statistics

## Next Steps

1. **Load into Database**: Use the JSON files to populate a graph database (Neo4j, ArangoDB)
2. **Build Knowledge Graph**: Use the `knowledge_graph.json` file created by `analyze_results.py`
3. **Query Relations**: Use pandas to analyze the CSV file
4. **Visualize**: Use the network graph outputs to create threat intelligence diagrams

## Example Analysis with Pandas

```python
import pandas as pd

# Load all relations
df = pd.read_csv('results/extracted_relations.csv')

# Find all tools used by APT28
apt28_tools = df[(df['head_entity'].str.contains('APT28')) &
                  (df['relation'] == 'uses') &
                  (df['tail_type'] == 'Tool')]

print(apt28_tools[['head_entity', 'relation', 'tail_entity']])

# Count most common relations
print(df['relation'].value_counts())

# Find all targeted organizations
targets = df[df['relation'] == 'targets']
print(targets[['head_entity', 'tail_entity']].head(10))
```

## Support

For issues or questions:

1. Check the main README: `README_DOCUMENT_PROCESSING.md`
2. Review the example scripts
3. Enable debug mode: Set `DEBUG_MODE = True` in scripts

---

**Happy Threat Intelligence Extraction! 🔍🛡️**
