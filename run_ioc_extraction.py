"""Run IOC extraction on the dataset and save results to JSON."""

import json
import os
import sys
from pathlib import Path

# Add local IOC-Finder to path
sys.path.insert(0, os.path.join(os.getcwd(), "Entity-Extraction", "IOC-Finder"))

try:
    from ioc_finder.ioc_finder import find_iocs
    from preprocess import load_and_clean_txt
except ImportError as e:
    print(f"Error importing ioc_finder: {e}")
    sys.exit(1)

def run_ioc_extraction_on_dataset():
    """Process all CTI reports in the dataset using IOC Finder."""
    
    # Use relative path for portability
    dataset_dir = Path("Data")
    output_dir = Path("results/ioc")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all text files
    text_files = sorted(dataset_dir.glob("*.txt"))
    
    if not text_files:
        print(f"No .txt files found in {dataset_dir}")
        return {}

    print(f"Found {len(text_files)} reports in dataset")
    print("=" * 80)
    
    all_results = {}
    
    for i, file_path in enumerate(text_files, 1):
        report_name = file_path.stem
        print(f"[{i}/{len(text_files)}] Processing: {report_name}")
        
        try:
            # Read and clean the report
            text = load_and_clean_txt(str(file_path))
            
            # Extract IOCs using the functional API
            # find_iocs returns (iocs_dict, locations_dict)
            iocs, locations = find_iocs(text)
            
            # Store results
            result = {
                "report_name": report_name,
                "file_path": str(file_path),
                "text_length": len(text),
                "iocs": iocs,
                "iocs_located": locations, # Added locations as it might be useful
                "ioc_count": sum(len(v) for v in iocs.values() if isinstance(v, list))
            }
            
            all_results[report_name] = result
            
            # Save individual report results
            output_file = output_dir / f"{report_name}.txt.json" # Match naming convention expected by merge_entities.py
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"  ✓ Found {result['ioc_count']} IOCs")
            
        except Exception as e:
            print(f"  ❌ Error processing {report_name}: {e}")
    
    # Save aggregated results
    summary_file = output_dir / "ioc_extraction_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print("\n" + "=" * 80)
    print(f"✓ IOC extraction complete!")
    print(f"  - Processed: {len(text_files)} reports")
    print(f"  - Output directory: {output_dir}")
    print(f"  - Summary file: {summary_file}")
    
    return all_results


if __name__ == "__main__":
    run_ioc_extraction_on_dataset()

