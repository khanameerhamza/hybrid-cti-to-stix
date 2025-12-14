import streamlit as st
import os
import shutil
import subprocess
import json
import glob
import sys
import networkx as nx
from streamlit_agraph import agraph, Node, Edge, Config

# Configuration
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "Data")
BACKUP_DIR = os.path.join(ROOT_DIR, "Data_Backup")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
MERGED_DIR = os.path.join(ROOT_DIR, "merged_final")
VALIDATED_DIR = os.path.join(ROOT_DIR, "validated_stix")
PYTHON_EXEC = sys.executable

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(MERGED_DIR, exist_ok=True)
os.makedirs(VALIDATED_DIR, exist_ok=True)

def backup_data():
    """Move existing files from Data to Data_Backup to isolate the single input."""
    files = glob.glob(os.path.join(DATA_DIR, "*"))
    for f in files:
        shutil.move(f, os.path.join(BACKUP_DIR, os.path.basename(f)))

def restore_data():
    """Restore files from Data_Backup to Data."""
    # First, clear any temporary files in Data
    files = glob.glob(os.path.join(DATA_DIR, "*"))
    for f in files:
        os.remove(f)
    
    # Move backup files back
    files = glob.glob(os.path.join(BACKUP_DIR, "*"))
    for f in files:
        shutil.move(f, os.path.join(DATA_DIR, os.path.basename(f)))

def run_script(script_name, description):
    """Run a python script and return success status."""
    st.write(f"running {description}...")
    try:
        result = subprocess.run(
            [PYTHON_EXEC, script_name],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            st.error(f"Failed: {description}")
            st.code(result.stderr)
            return False
        return True
    except Exception as e:
        st.error(f"Error running {description}: {e}")
        return False

def visualize_stix_graph(json_data):
    """Visualize entities and relationships using streamlit-agraph."""
    nodes = []
    edges = []
    
    # Check if this is a STIX Bundle (from LLM Validation)
    if json_data.get("type") == "bundle" and "objects" in json_data:
        st.info("Visualizing STIX 2.1 Bundle")
        objects = json_data.get("objects", [])
        
        # First pass: Collect all nodes
        for obj in objects:
            if obj.get("type") == "relationship":
                continue
                
            node_id = obj.get("id")
            # Try to get a human-readable label
            label = obj.get("name") or obj.get("value") or obj.get("pattern") or node_id
            node_type = obj.get("type")
            
            # Color coding
            color = "#97C2FC" # Default blue
            if node_type == "threat-actor": color = "#FF9999" # Red
            elif node_type == "malware": color = "#FFCC99" # Orange
            elif node_type == "indicator" or node_type == "ipv4-addr": color = "#99FF99" # Green
            elif node_type == "attack-pattern": color = "#FFFF99" # Yellow
            elif node_type == "identity": color = "#DDDDDD" # Grey
            
            nodes.append(Node(
                id=node_id,
                label=label,
                size=25,
                shape="dot",
                color=color,
                title=f"Type: {node_type}\nID: {node_id}"
            ))
            
        # Second pass: Collect edges
        for obj in objects:
            if obj.get("type") == "relationship":
                source = obj.get("source_ref")
                target = obj.get("target_ref")
                label = obj.get("relationship_type")
                
                if source and target:
                    edges.append(Edge(
                        source=source,
                        target=target,
                        label=label,
                        color="#CCCCCC"
                    ))
                    
    else:
        # Fallback to Intermediate Merged Format
        st.info("Visualizing Extracted Entities (Pre-Validation)")
        entities = json_data.get("entities", {}).get("by_type", {})
        relationships = json_data.get("relationships", {}).get("validated_relations", [])
        
        # Add Nodes
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                # Handle string entities (from by_type list)
                if isinstance(entity, str):
                    node_id = entity
                # Handle dictionary entities (if any)
                elif isinstance(entity, dict):
                    node_id = entity.get("name") or entity.get("value") or entity.get("text")
                else:
                    continue

                if not node_id:
                    continue
                    
                # Color coding based on type
                color = "#97C2FC" # Default blue
                if "Actor" in entity_type or "threat-actor" in entity_type:
                    color = "#FF9999" # Red
                elif "Malware" in entity_type or "malware" in entity_type:
                    color = "#FFCC99" # Orange
                elif "Indicator" in entity_type or "ipv4" in entity_type:
                    color = "#99FF99" # Green
                elif "TTP" in entity_type or "attack-pattern" in entity_type:
                    color = "#FFFF99" # Yellow
                    
                nodes.append(Node(
                    id=node_id,
                    label=node_id,
                    size=25,
                    shape="dot",
                    color=color,
                    title=f"Type: {entity_type}"
                ))
                
        # Add Edges
        for rel in relationships:
            source = rel.get("source") or rel.get("head")
            target = rel.get("target") or rel.get("tail")
            label = rel.get("type") or rel.get("relation")
            
            if source and target:
                edges.append(Edge(
                    source=source,
                    target=target,
                    label=label,
                    color="#CCCCCC"
                ))
            
    config = Config(width=800, height=600, directed=True, physics=True, hierarchical=False)
    return agraph(nodes=nodes, edges=edges, config=config)

# Streamlit UI
st.set_page_config(page_title="CTI Pipeline", layout="wide")
st.title("🕵️‍♂️ CTI Extraction & STIX Generation Pipeline")

st.markdown("""
This tool processes raw Cyber Threat Intelligence (CTI) reports to extract entities (Threat Actors, Malware, IOCs, TTPs), 
identifies relationships, and generates STIX 2.1 compatible graphs.
""")

# Sidebar options
st.sidebar.header("Configuration")
enable_llm = st.sidebar.checkbox("Enable LLM Validation", value=False, help="Requires Gemini API Quota")

# Input Area
input_text = st.text_area("Paste CTI Report Text Here:", height=300)

if st.button("Run Pipeline"):
    if not input_text.strip():
        st.warning("Please enter some text first.")
    else:
        status_placeholder = st.empty()
        status_placeholder.info("Starting pipeline...")
        
        # 1. Backup Data
        backup_data()
        
        try:
            # 2. Save Input
            with open(os.path.join(DATA_DIR, "input.txt"), "w", encoding="utf-8") as f:
                f.write(input_text)
            
            # 3. Run Pipeline Stages
            progress_bar = st.progress(0)
            
            # Stage 1: KB Match
            status_placeholder.text("Stage 1/5: Running Knowledge Base Matching...")
            run_script("kb_match_batch.py", "KB Matching")
            progress_bar.progress(20)
            
            # Stage 2: IOC Extraction
            status_placeholder.text("Stage 2/5: Running IOC Extraction...")
            run_script("run_ioc_extraction.py", "IOC Extraction")
            progress_bar.progress(40)
            
            # Stage 3: Novel Entity Extraction
            status_placeholder.text("Stage 3/7: Running Novel Entity Extraction...")
            run_script("novel_entities.py", "Novel Entity Extraction")
            progress_bar.progress(40)

            # Stage 4: TTP Extraction
            status_placeholder.text("Stage 4/7: Running TTP Extraction...")
            ttp_script = os.path.join("Entity-Extraction", "rcATT", "infer_rcatt.py")
            run_script(ttp_script, "TTP Extraction")
            progress_bar.progress(55)
            
            # Stage 5: Entity Merging
            status_placeholder.text("Stage 5/7: Merging Entities...")
            run_script("merge_entities.py", "Entity Merging")
            progress_bar.progress(70)

            # Stage 6: Relationship Extraction
            status_placeholder.text("Stage 6/7: Running Relationship Extraction...")
            run_script("process_documents.py", "Relationship Extraction")
            progress_bar.progress(85)
            
            # Stage 7: Relationship Fusion
            status_placeholder.text("Stage 7/7: Fusing Relationships...")
            run_script("merge_entity_relationship_data.py", "Data Fusion")
            progress_bar.progress(95)
            
            # Stage 5: LLM Validation (Optional)
            llm_success = False
            if enable_llm:
                status_placeholder.text("Stage 5/5: Running LLM Validation...")
                # We need to call LLM_Validation specifically for this file
                # The script expects --json and --text args
                merged_file = os.path.join(MERGED_DIR, "input_merged.json")
                text_file = os.path.join(DATA_DIR, "input.txt")
                output_file = os.path.join(VALIDATED_DIR, "input_stix.json")
                
                if os.path.exists(merged_file):
                    result = subprocess.run(
                        [PYTHON_EXEC, "LLM_Validation.py", "--json", merged_file, "--text", text_file, "--output", output_file],
                        cwd=ROOT_DIR,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        st.success("LLM Validation Complete")
                        llm_success = True
                    else:
                        st.warning(f"LLM Validation Failed (likely rate limit): {result.stderr}")
                else:
                    st.error("Merged file not found, skipping LLM.")
            else:
                status_placeholder.text("Skipping LLM Validation (Disabled)")
            
            progress_bar.progress(100)
            status_placeholder.success("Pipeline Execution Complete!")
            
            # 4. Display Results
            # Determine which file to show
            final_output_path = os.path.join(MERGED_DIR, "input_merged.json")
            if enable_llm and llm_success:
                stix_path = os.path.join(VALIDATED_DIR, "input_stix.json")
                if os.path.exists(stix_path):
                    final_output_path = stix_path
            
            if os.path.exists(final_output_path):
                with open(final_output_path, 'r') as f:
                    data = json.load(f)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("Extracted Data (JSON)")
                    st.json(data)
                
                with col2:
                    st.subheader("STIX Graph Visualization")
                    visualize_stix_graph(data)
            else:
                st.error("No output generated. Check logs.")
                
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            
        finally:
            # 5. Restore Data
            restore_data()
