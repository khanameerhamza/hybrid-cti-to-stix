"""
Example: Process a single document
This script demonstrates how to process one document and view the results.
"""

from process_documents import (
    load_model_from_zip, 
    process_document, 
    split_into_sentences
)
import json
import os

def main():
    # Configuration
    MODEL_FOLDER = "."
    DOCUMENT_PATH = "./Data/ALLANITE.txt"  # Change this to test different documents
    
    print("\n" + "="*80)
    print("Single Document Processing Example")
    print("="*80 + "\n")
    
    # Load model
    print("Loading model...")
    model, config = load_model_from_zip(MODEL_FOLDER)
    print("Model loaded!\n")
    
    # Process the document
    results = process_document(DOCUMENT_PATH, model, config, debug=False)
    
    # Display some results
    print("\n" + "="*80)
    print("SAMPLE RESULTS")
    print("="*80)
    
    print(f"\nDocument: {results['document_name']}")
    print(f"Total Sentences: {results['total_sentences']}")
    print(f"Total Entities: {len(results['all_entities'])}")
    print(f"Total Relations: {len(results['all_relations'])}")
    
    # Show first few entities
    print("\n--- First 5 Entities ---")
    for entity in results['all_entities'][:5]:
        print(f"  • {entity['text']} ({entity['type']}) - Sentence {entity['sentence_id']}")
    
    # Show first few relations
    print("\n--- First 10 Relations ---")
    for relation in results['all_relations'][:10]:
        print(f"  • {relation['head']} --[{relation['relation']}]--> {relation['tail']}")
        print(f"    Types: {relation['head_type']} -> {relation['tail_type']}")
        print(f"    Context: Sentence {relation['sentence_id']}")
        print()
    
    # Show relation type distribution
    print("\n--- Relation Type Distribution ---")
    for rel_type, count in sorted(results['relation_counts'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {rel_type}: {count}")
    
    # Save results
    output_file = f"{os.path.splitext(os.path.basename(DOCUMENT_PATH))[0]}_example_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Full results saved to: {output_file}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
