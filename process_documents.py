"""
Document Processing Script for TIRE Model
Processes cyber threat documents, extracts entities and relationships sentence by sentence.
"""

import os
import json
import re
from pathlib import Path
from run_tire import load_model_from_zip, predict
import torch

def split_into_sentences(text):
    """
    Split text into sentences using regex.
    Handles common abbreviations and edge cases.
    """
    # Replace common abbreviations to avoid splitting on them
    text = text.replace("U.S.", "US")
    text = text.replace("e.g.", "eg")
    text = text.replace("i.e.", "ie")
    
    # Split on sentence boundaries (., !, ?)
    # Look ahead to ensure there's a space or end of string after punctuation
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    
    # Clean up sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences

def process_document(file_path, model, config, debug=False):
    """
    Process a single document: split into sentences and extract entities/relations.
    
    Args:
        file_path: Path to the document file
        model: Loaded TIRE model
        config: Model configuration
        debug: Enable debug output
    
    Returns:
        Dictionary containing document results
    """
    print(f"\n{'='*80}")
    print(f"Processing: {os.path.basename(file_path)}")
    print(f"{'='*80}")
    
    # Read document
    with open(file_path, 'r', encoding='utf-8') as f:
        document_text = f.read()
    
    # Split into sentences
    sentences = split_into_sentences(document_text)
    print(f"Found {len(sentences)} sentences in document.")
    
    # Store results
    document_results = {
        "document_name": os.path.basename(file_path),
        "total_sentences": len(sentences),
        "sentences": [],
        "all_entities": [],
        "all_relations": [],
        "entity_counts": {},
        "relation_counts": {}
    }
    
    # Process each sentence
    for idx, sentence in enumerate(sentences):
        if debug:
            print(f"\n--- Sentence {idx + 1}/{len(sentences)} ---")
            print(f"Text: {sentence[:100]}..." if len(sentence) > 100 else f"Text: {sentence}")
        
        try:
            # Get predictions for this sentence
            entities, relations = predict(sentence, model, config, debug=False)
            
            # Store sentence-level results
            sentence_result = {
                "sentence_id": idx + 1,
                "text": sentence,
                "entities": entities,
                "relations": relations,
                "entity_count": len(entities),
                "relation_count": len(relations)
            }
            
            document_results["sentences"].append(sentence_result)
            
            # Aggregate entities (with sentence context)
            for entity in entities:
                entity_with_context = {
                    **entity,
                    "sentence_id": idx + 1,
                    "sentence_text": sentence
                }
                document_results["all_entities"].append(entity_with_context)
                
                # Count entity types
                entity_type = entity['type']
                document_results["entity_counts"][entity_type] = \
                    document_results["entity_counts"].get(entity_type, 0) + 1
            
            # Aggregate relations (with sentence context)
            for relation in relations:
                relation_with_context = {
                    **relation,
                    "sentence_id": idx + 1,
                    "sentence_text": sentence
                }
                document_results["all_relations"].append(relation_with_context)
                
                # Count relation types
                relation_type = relation['relation']
                document_results["relation_counts"][relation_type] = \
                    document_results["relation_counts"].get(relation_type, 0) + 1
            
            if not debug:
                # Show progress
                if (idx + 1) % 10 == 0:
                    print(f"  Processed {idx + 1}/{len(sentences)} sentences...")
        
        except Exception as e:
            print(f"  Error processing sentence {idx + 1}: {str(e)}")
            # Store error information
            sentence_result = {
                "sentence_id": idx + 1,
                "text": sentence,
                "error": str(e),
                "entities": [],
                "relations": []
            }
            document_results["sentences"].append(sentence_result)
    
    # Summary statistics
    print(f"\nDocument Processing Summary:")
    print(f"  Total Entities: {len(document_results['all_entities'])}")
    print(f"  Total Relations: {len(document_results['all_relations'])}")
    print(f"  Entity Types: {dict(document_results['entity_counts'])}")
    print(f"  Relation Types: {dict(document_results['relation_counts'])}")
    
    return document_results

def process_all_documents(data_folder, output_folder, model, config, debug=False):
    """
    Process all .txt files in the data folder.
    
    Args:
        data_folder: Path to folder containing .txt documents
        output_folder: Path to save JSON results
        model: Loaded TIRE model
        config: Model configuration
        debug: Enable debug output
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all .txt files
    data_path = Path(data_folder)
    txt_files = sorted(list(data_path.glob("*.txt")))
    
    if not txt_files:
        print(f"No .txt files found in {data_folder}")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(txt_files)} documents to process")
    print(f"{'='*80}")
    
    # Store aggregate statistics across all documents
    all_documents_summary = {
        "total_documents": len(txt_files),
        "documents": [],
        "aggregate_stats": {
            "total_sentences": 0,
            "total_entities": 0,
            "total_relations": 0,
            "entity_type_counts": {},
            "relation_type_counts": {}
        }
    }
    
    # Process each document
    for idx, file_path in enumerate(txt_files):
        try:
            # Process document
            doc_results = process_document(str(file_path), model, config, debug)
            
            # Save individual document results
            output_filename = f"{Path(file_path).stem}_results.json"
            output_path = os.path.join(output_folder, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(doc_results, f, indent=2, ensure_ascii=False)
            
            print(f"  Saved results to: {output_filename}")
            
            # Update aggregate statistics
            all_documents_summary["documents"].append({
                "name": doc_results["document_name"],
                "sentences": doc_results["total_sentences"],
                "entities": len(doc_results["all_entities"]),
                "relations": len(doc_results["all_relations"]),
                "output_file": output_filename
            })
            
            all_documents_summary["aggregate_stats"]["total_sentences"] += doc_results["total_sentences"]
            all_documents_summary["aggregate_stats"]["total_entities"] += len(doc_results["all_entities"])
            all_documents_summary["aggregate_stats"]["total_relations"] += len(doc_results["all_relations"])
            
            # Aggregate entity counts
            for entity_type, count in doc_results["entity_counts"].items():
                all_documents_summary["aggregate_stats"]["entity_type_counts"][entity_type] = \
                    all_documents_summary["aggregate_stats"]["entity_type_counts"].get(entity_type, 0) + count
            
            # Aggregate relation counts
            for relation_type, count in doc_results["relation_counts"].items():
                all_documents_summary["aggregate_stats"]["relation_type_counts"][relation_type] = \
                    all_documents_summary["aggregate_stats"]["relation_type_counts"].get(relation_type, 0) + count
        
        except Exception as e:
            print(f"ERROR processing {file_path.name}: {str(e)}")
            all_documents_summary["documents"].append({
                "name": file_path.name,
                "error": str(e)
            })
    
    # Save aggregate summary
    summary_path = os.path.join(output_folder, "_all_documents_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_documents_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print("PROCESSING COMPLETE!")
    print(f"{'='*80}")
    print(f"Total Documents Processed: {len(txt_files)}")
    print(f"Total Sentences: {all_documents_summary['aggregate_stats']['total_sentences']}")
    print(f"Total Entities Extracted: {all_documents_summary['aggregate_stats']['total_entities']}")
    print(f"Total Relations Extracted: {all_documents_summary['aggregate_stats']['total_relations']}")
    print(f"\nResults saved to: {output_folder}")
    print(f"Summary file: _all_documents_summary.json")
    print(f"{'='*80}\n")

def create_relations_csv(output_folder, csv_filename="extracted_relations.csv"):
    """
    Create a CSV file with all relations from all processed documents.
    This format is useful for further analysis and visualization.
    """
    import csv
    
    # Collect all relations from JSON files
    all_relations = []
    output_path = Path(output_folder)
    
    for json_file in output_path.glob("*_results.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            document_name = data['document_name']
            
            for relation in data['all_relations']:
                all_relations.append({
                    'document': document_name,
                    'sentence_id': relation['sentence_id'],
                    'head_entity': relation['head'],
                    'head_type': relation['head_type'],
                    'relation': relation['relation'],
                    'tail_entity': relation['tail'],
                    'tail_type': relation['tail_type'],
                    'sentence': relation['sentence_text']
                })
    
    # Write to CSV
    csv_path = os.path.join(output_folder, csv_filename)
    if all_relations:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_relations[0].keys())
            writer.writeheader()
            writer.writerows(all_relations)
        
        print(f"Created CSV file with {len(all_relations)} relations: {csv_filename}")
    else:
        print("No relations found to export to CSV")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TIRE Model - Batch Document Processing")
    print("="*80 + "\n")
    
    # Configuration
    MODEL_FOLDER = "."  # Folder containing config.json and model_weights.pth
    DATA_FOLDER = "./Data"  # Folder containing .txt documents
    OUTPUT_FOLDER = "./relationship"  # Folder to save JSON results
    DEBUG_MODE = False  # Set to True for detailed debug output
    
    try:
        # Load model
        print("Loading TIRE model...")
        model, config = load_model_from_zip(MODEL_FOLDER)
        print("Model loaded successfully!\n")
        
        # Process all documents
        process_all_documents(DATA_FOLDER, OUTPUT_FOLDER, model, config, debug=DEBUG_MODE)
        
        # Create relations CSV for easy analysis
        print("\nCreating consolidated relations CSV...")
        create_relations_csv(OUTPUT_FOLDER)
        
        print("\n✓ All processing complete!")
        print(f"✓ Check the '{OUTPUT_FOLDER}' folder for results")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
