import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions
import json
import uuid
import argparse
import sys
import time
import os
from pathlib import Path

def load_json_file(file_path):
    """Load JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)

def load_text_file(file_path):
    """Load text file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Text file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading text file {file_path}: {e}")
        sys.exit(1)

def send_message_with_retry(chat, prompt, max_retries=10, initial_delay=10):
    """Send message to chat with retry logic for rate limits."""
    retries = 0
    delay = initial_delay
    
    while retries < max_retries:
        try:
            return chat.send_message(prompt)
        except exceptions.ResourceExhausted as e:
            print(f"\n⚠ Rate limit exceeded. Retrying in {delay} seconds... (Attempt {retries + 1}/{max_retries})")
            time.sleep(delay)
            retries += 1
            delay *= 2  # Exponential backoff
        except Exception as e:
            print(f"\n✗ Error sending message: {e}")
            raise e
            
    raise Exception("Max retries exceeded for Gemini API rate limit.")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Validate merged CTI entities and relationships using Gemini LLM and generate STIX 2.1 bundle',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python LLM_Validation.py --json merged_final/ALLANITE_merged.json --text Data/ALLANITE.txt
  python LLM_Validation.py -j merged_final/APT28_merged.json -t Data/APT28.txt --output APT28_stix.json
        """
    )
    parser.add_argument('-j', '--json', required=True, help='Path to merged JSON file (e.g., merged_final/ALLANITE_merged.json)')
    parser.add_argument('-t', '--text', required=True, help='Path to original CTI text document (e.g., Data/ALLANITE.txt)')
    parser.add_argument('-o', '--output', default='validated_stix_output.json', help='Output file for STIX bundle (default: validated_stix_output.json)')
    
    args = parser.parse_args()
    
    # Load inputs
    print(f"\nLoading merged JSON from: {args.json}")
    merged_json = load_json_file(args.json)
    combined_json_str = json.dumps(merged_json)
    
    print(f"Loading original document from: {args.text}")
    document_text = load_text_file(args.text)
    
    
    # Initialize model
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_instruction,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    
    # Start chat session
    chat = model.start_chat(history=[])

    print("\n" + "="*80)
    print("STEP 1: Validating entities and relationships against document text")
    print("="*80)
    
    step1_prompt = f"""
Validate the provided combined JSON (entities and relationships) against the content of the uploaded document file. Check completeness by adding any missing STIX-mappable items explicitly derived from the file's text, accuracy by removing or correcting items that do not match the file's content, and compliance by ensuring all elements adhere to valid STIX 2.1 types, required attributes, and relationship verbs. Output strictly in JSON format: {{
"validated_entities": [array of validated entity objects, each with STIX-compliant structure including type, id, and other relevant attributes],
"validated_relationships": [array of validated relationship objects, each with STIX-compliant structure including type, id, source_ref, target_ref, and relationship_type],
"issues": ["array of any errors or discrepancies identified"]
}}.
Combined JSON: {combined_json_str}
Document Text: {document_text}
"""
    response1 = send_message_with_retry(chat, step1_prompt)
    validated_data = json.loads(response1.text)  # Parse the JSON response
    
    # Handle issues if any (e.g., retry or log)
    if validated_data.get("issues"):
        print("\n⚠ Issues found during validation:")
        for issue in validated_data["issues"]:
            print(f"  - {issue}")
    else:
        print("✓ Validation completed successfully")
    
    print(f"✓ Validated entities: {len(validated_data.get('validated_entities', []))}")
    print(f"✓ Validated relationships: {len(validated_data.get('validated_relationships', []))}")
    
    # Step 2: Generate final STIX JSON bundle
    print("\n" + "="*80)
    print("STEP 2: Generating STIX 2.1 bundle")
    print("="*80)
    
    validated_entities_str = json.dumps(validated_data["validated_entities"])
    validated_relationships_str = json.dumps(validated_data["validated_relationships"])
    step2_prompt = f"""
Combine the validated entities and relationships into a complete STIX 2.1 bundle. Ensure all objects are linked correctly, add required bundle attributes (e.g., type: "bundle", id: "bundle--{str(uuid.uuid4())}"), and verify against the text for no omissions. This JSON must be compatible with STIX diagram tools (e.g., OASIS STIX Visualizer).
Output JSON: {{
    "type": "bundle",
    "id": "bundle--[uuid]",
    "objects": [array of all entities and relationships],
    "issues": ["if any"]
}}.
Validated Entities: {validated_entities_str}
Validated Relationships: {validated_relationships_str}
Document Text: {document_text}  # Include for final cross-check
"""
    response2 = send_message_with_retry(chat, step2_prompt)
    final_stix_json = json.loads(response2.text)
    
    # Handle issues if any
    if final_stix_json.get("issues"):
        print("\n⚠ Issues found in STIX bundle generation:")
        for issue in final_stix_json["issues"]:
            print(f"  - {issue}")
    else:
        print("✓ STIX bundle generated successfully")
    
    print(f"✓ Total STIX objects: {len(final_stix_json.get('objects', []))}")
    
    # Save the final STIX JSON
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_stix_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ STIX bundle saved to: {output_path}")
    print("="*80)
    print("\n✓ Validation complete!")
    
    # Optional: Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Input JSON: {args.json}")
    print(f"Input Text: {args.text}")
    print(f"Output STIX: {args.output}")
    print(f"Total Objects: {len(final_stix_json.get('objects', []))}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()