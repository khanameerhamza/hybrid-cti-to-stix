#!/usr/bin/env python3
"""
Main Pipeline Orchestration Script for CTI Document Processing

This script runs the entire pipeline sequentially:
1. Entity Extraction (KB, IOC, Novel, TTP)
2. Entity Merging
3. Relationship Extraction (TIRE Model)
4. Final Data Fusion (Entity + Relationship)
5. LLM Validation & STIX Generation
"""

import os
import sys
import subprocess
import glob
import time
from pathlib import Path

# Configuration
PYTHON_EXEC = sys.executable
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "Data")  # Adjusted to correct path
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
MERGED_FINAL_DIR = os.path.join(ROOT_DIR, "merged_final")
VALIDATED_DIR = os.path.join(ROOT_DIR, "validated_stix")

def run_command(command, description):
    """Run a shell command and print status."""
    print(f"\n{'='*80}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {' '.join(command)}")
    print(f"{'='*80}")
    
    start_time = time.time()
    try:
        # Run command and stream output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd=ROOT_DIR
        )
        
        # Print output in real-time
        for line in process.stdout:
            print(line, end='')
            
        process.wait()
        
        end_time = time.time()
        duration = end_time - start_time
        
        if process.returncode != 0:
            print(f"\n❌ FAILED: {description} (Exit Code: {process.returncode})")
            return False
        else:
            print(f"\n✓ COMPLETED: {description} in {duration:.2f}s")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR executing {description}: {str(e)}")
        return False

def main():
    print("STARTING CTI PIPELINE ORCHESTRATION")
    print(f"Root Directory: {ROOT_DIR}")
    
    # Ensure directories exist
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(VALIDATED_DIR, exist_ok=True)
    
    # --- STAGE 1: ENTITY EXTRACTION ---
    print("\n\n" + "#"*40)
    print("STAGE 1: ENTITY EXTRACTION")
    print("#"*40)
    
    # 1.1 KB Matching
    if not run_command([PYTHON_EXEC, "kb_match_batch.py"], "KB Matching"):
        print("Stopping pipeline due to failure.")
        return

    # 1.2 IOC Extraction
    if not run_command([PYTHON_EXEC, "run_ioc_extraction.py"], "IOC Extraction"):
        print("Stopping pipeline due to failure.")
        return

    # 1.3 Novel Entity Extraction
    if not run_command([PYTHON_EXEC, "novel_entities.py"], "Novel Entity Extraction"):
        print("Stopping pipeline due to failure.")
        return

    # 1.4 TTP Extraction
    # Note: TTP script is in a subdirectory
    ttp_script = os.path.join("Entity-Extraction", "rcATT", "infer_rcatt.py")
    if not run_command([PYTHON_EXEC, ttp_script], "TTP Extraction"):
        print("Stopping pipeline due to failure.")
        return

    # --- STAGE 2: ENTITY MERGING ---
    print("\n\n" + "#"*40)
    print("STAGE 2: ENTITY MERGING")
    print("#"*40)
    
    if not run_command([PYTHON_EXEC, "merge_entities.py"], "Entity Merging"):
        print("Stopping pipeline due to failure.")
        return

    # --- STAGE 3: RELATIONSHIP EXTRACTION ---
    print("\n\n" + "#"*40)
    print("STAGE 3: RELATIONSHIP EXTRACTION (TIRE MODEL)")
    print("#"*40)
    
    if not run_command([PYTHON_EXEC, "process_documents.py"], "Relationship Extraction"):
        print("Stopping pipeline due to failure.")
        return

    # --- STAGE 4: FINAL DATA FUSION ---
    print("\n\n" + "#"*40)
    print("STAGE 4: FINAL DATA FUSION")
    print("#"*40)
    
    if not run_command([PYTHON_EXEC, "merge_entity_relationship_data.py"], "Final Data Fusion"):
        print("Stopping pipeline due to failure.")
        return

    # --- STAGE 5: LLM VALIDATION ---
    print("\n\n" + "#"*40)
    print("STAGE 5: LLM VALIDATION & STIX GENERATION")
    print("#"*40)
    
    # Find all merged files
    merged_files = sorted(glob.glob(os.path.join(MERGED_FINAL_DIR, "*_merged.json")))
    
    if not merged_files:
        print("❌ No merged files found in 'merged_final/'. Skipping LLM validation.")
    else:
        print(f"Found {len(merged_files)} documents to validate.")
        
        # for merged_file in merged_files:
        #     basename = os.path.basename(merged_file).replace("_merged.json", "")
        #     original_text_file = os.path.join(DATA_DIR, f"{basename}.txt")
        #     output_stix = os.path.join(VALIDATED_DIR, f"{basename}_stix.json")
            
        #     if not os.path.exists(original_text_file):
        #         print(f"⚠ Warning: Original text file not found for {basename}. Skipping.")
        #         continue
                
        #     cmd = [
        #         PYTHON_EXEC, "LLM_Validation.py",
        #         "--json", merged_file,
        #         "--text", original_text_file,
        #         "--output", output_stix
        #     ]
            
        #     # We don't stop the pipeline if one LLM validation fails, just continue to next
        #     run_command(cmd, f"LLM Validation for {basename}")
        print("Skipping LLM Validation due to API daily limit reached.")

    print("\n\n" + "="*80)
    print("PIPELINE EXECUTION COMPLETE")
    print("="*80)
    print(f"Final STIX bundles should be in: {VALIDATED_DIR}")

if __name__ == "__main__":
    main()
