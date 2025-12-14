import torch
import torch.nn as nn
from transformers import BertTokenizerFast, BertModel
from torchcrf import CRF
import json
import os

# --- 1. MODEL CLASS (Required to load weights) ---
class JointExtractionModel(nn.Module):
    def __init__(self, bert_model, num_ner_labels, num_re_labels, entity_type_vocab_size):
        super(JointExtractionModel, self).__init__()
        self.bert = bert_model
        self.ner_classifier = nn.Linear(bert_model.config.hidden_size, num_ner_labels)
        
        # Input dim is hidden_size * 3 (Pooled Entity + 2 Type Embeddings)
        self.re_dim_reduction = nn.Linear(bert_model.config.hidden_size * 3, bert_model.config.hidden_size)
        
        self.re_classifier = nn.Linear(bert_model.config.hidden_size, num_re_labels)
        self.entity_type_embedding = nn.Embedding(entity_type_vocab_size, bert_model.config.hidden_size)
        self.crf = CRF(num_ner_labels, batch_first=True)

    def forward(self, input_ids, attention_mask, entity_type_ids, entity_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs[0]
        
        # NER Logits
        ner_logits = self.ner_classifier(sequence_output)
        
        # RE Logic (Pooling)
        entity_type_embedded = self.entity_type_embedding(entity_type_ids)
        
        # Mask and Pool
        # entity_mask shape: (batch, seq_len) -> (batch, seq_len, 1)
        mask_expanded = entity_mask.unsqueeze(-1)
        masked_output = sequence_output * mask_expanded
        entity_representation = masked_output.sum(dim=1)
        
        # Concatenate: [Pooled Entity Representation, Type Embedding 1, Type Embedding 2]
        # entity_type_embedded shape: (batch, 2, hidden) -> flatten to (batch, hidden*2)
        types_flat = entity_type_embedded.view(entity_type_embedded.size(0), -1)
        
        pooled_entity_pairs = torch.cat([entity_representation, types_flat], dim=-1)
        
        reduced_entity_representation = torch.relu(self.re_dim_reduction(pooled_entity_pairs))
        re_logits = self.re_classifier(reduced_entity_representation)
        
        return ner_logits, re_logits

    def decode_ner(self, ner_logits, attention_mask):
        return self.crf.decode(ner_logits, mask=attention_mask.bool())

# --- 2. LOADING FUNCTION ---
def load_model_from_zip(folder_path):
    config_path = os.path.join(folder_path, 'config.json')
    weights_path = os.path.join(folder_path, 'model_weights.pth')
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    print("Loading BERT...")
    bert = BertModel.from_pretrained('bert-base-cased')
    
    print("Building Model...")
    model = JointExtractionModel(
        bert,
        num_ner_labels=config['num_ner_labels'],
        num_re_labels=config['num_re_labels'],
        entity_type_vocab_size=config['entity_vocab_size']
    )
    
    print("Loading Weights...")
    model.load_state_dict(torch.load(weights_path, map_location=torch.device('cpu')))
    model.eval()
    
    return model, config

# --- 3. PREDICTION FUNCTION ---
def predict(text, model, config, debug=False):
    tokenizer = BertTokenizerFast.from_pretrained('bert-base-cased')
    max_len = config['max_len']
    
    # Map IDs back to Labels
    # JSON stores keys as strings, convert back to int
    neid2type = {int(k): v for k, v in config['neid2type'].items()}
    netype2id = config['netype2id']
    reid2type = {int(k): v for k, v in config['reid2type'].items()}
    
    # Tokenize with offset mapping to track original text positions
    inputs = tokenizer(
        text, 
        return_tensors="pt", 
        max_length=max_len, 
        truncation=True, 
        padding="max_length",
        return_offsets_mapping=True,
        return_special_tokens_mask=True
    )
    input_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]
    offset_mapping = inputs["offset_mapping"][0]  # (seq_len, 2) - start and end char positions
    special_tokens_mask = inputs["special_tokens_mask"][0]  # 1 for special tokens, 0 otherwise
    
    # Dummy inputs for RE (needed for forward pass)
    dummy_mask = torch.zeros((1, max_len), dtype=torch.long)
    dummy_types = torch.zeros((1, 2), dtype=torch.long)
    
    # NER Inference
    with torch.no_grad():
        ner_logits, _ = model(input_ids, attention_mask, dummy_types, dummy_mask)
        ner_tags = model.decode_ner(ner_logits, attention_mask)[0]
        
    # Parse Entities using offset mapping
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    
    # DEBUG: Print tokenization details
    if debug:
        print("\n=== TOKENIZATION DEBUG ===")
        for idx, (token, tag_id, offset, special) in enumerate(zip(tokens, ner_tags, offset_mapping, special_tokens_mask)):
            if special == 0:  # Not a special token
                tag = neid2type.get(tag_id, 'O')
                print(f"  [{idx:2d}] Token: {token:15s} | Tag: {tag:15s} | Offset: {offset.tolist()} | Text: '{text[offset[0]:offset[1]]}'")
        print("=" * 50 + "\n")
    
    entities = []
    current_ent = None
    
    for idx, tag_id in enumerate(ner_tags):
        # Skip special tokens
        if special_tokens_mask[idx] == 1:
            if current_ent:
                entities.append(current_ent)
                current_ent = None
            continue
            
        tag = neid2type.get(tag_id, 'O')
        token = tokens[idx]
        start_char, end_char = offset_mapping[idx]
        
        # Skip tokens with no character mapping (padding)
        if start_char == 0 and end_char == 0 and token == '[PAD]':
            continue
        
        if tag.startswith("B-"):
            # Save previous entity if exists
            if current_ent:
                entities.append(current_ent)
            # Start new entity
            current_ent = {
                'type': tag[2:], 
                'start_idx': idx,
                'end_idx': idx,
                'start_char': start_char,
                'end_char': end_char
            }
        elif tag.startswith("I-") and current_ent and tag[2:] == current_ent['type']:
            # Continue current entity
            current_ent['end_idx'] = idx
            current_ent['end_char'] = end_char
        else:
            # End of entity or outside tag
            if current_ent:
                entities.append(current_ent)
                current_ent = None
            
    if current_ent:
        entities.append(current_ent)
    
    # Extract entity text from original text using character offsets
    parsed_entities = []
    for e in entities:
        # Use character offsets to extract the exact text from original input
        entity_text = text[e['start_char']:e['end_char']].strip()
        
        # Fallback: if character offset gives empty result, use token reconstruction
        if not entity_text:
            entity_tokens = tokens[e['start_idx']:e['end_idx']+1]
            cleaned_tokens = []
            for token in entity_tokens:
                if token.startswith('##'):
                    if cleaned_tokens:
                        cleaned_tokens[-1] += token[2:]
                    else:
                        cleaned_tokens.append(token[2:])
                else:
                    cleaned_tokens.append(token)
            entity_text = ' '.join(cleaned_tokens)
        
        # HEURISTIC FIX: Expand entity boundaries to capture complete words
        # Look for word boundaries in the original text
        expanded_text = expand_entity_to_word_boundaries(text, e['start_char'], e['end_char'])
        
        parsed_entities.append({
            'text': expanded_text, 
            'type': e['type'], 
            'start': e['start_idx'], 
            'end': e['end_idx']
        })
        
    # RE Inference (Pairwise)
    relations = []
    for i in range(len(parsed_entities)):
        for j in range(len(parsed_entities)):
            if i == j: continue
            
            ent1 = parsed_entities[i]
            ent2 = parsed_entities[j]
            
            # Build specific mask for this pair
            pair_mask = torch.zeros((1, max_len), dtype=torch.long)
            pair_mask[0, ent1['start']:ent1['end']+1] = 1
            pair_mask[0, ent2['start']:ent2['end']+1] = 1
            
            # Build Types
            t1 = netype2id.get(f"B-{ent1['type']}", 0)
            t2 = netype2id.get(f"B-{ent2['type']}", 0)
            pair_types = torch.tensor([[t1, t2]], dtype=torch.long)
            
            with torch.no_grad():
                _, re_logits = model(input_ids, attention_mask, pair_types, pair_mask)
                pred = torch.argmax(re_logits, dim=1).item()
                
            rel_label = reid2type.get(pred, 'noRelation')
            if rel_label != 'noRelation':
                relations.append({
                    'head': ent1['text'],
                    'head_type': ent1['type'],
                    'relation': rel_label,
                    'tail': ent2['text'],
                    'tail_type': ent2['type']
                })
                
    return parsed_entities, relations

def expand_entity_to_word_boundaries(text, start_char, end_char):
    """
    Expand entity boundaries to capture complete words.
    This handles cases where the model only predicts part of a word.
    """
    # Expand left: move back while we see alphanumeric characters
    while start_char > 0 and text[start_char - 1].isalnum():
        start_char -= 1
    
    # Expand right: move forward while we see alphanumeric characters
    while end_char < len(text) and text[end_char].isalnum():
        end_char += 1
    
    return text[start_char:end_char].strip()

# --- 3.5. DISPLAY FUNCTION ---
def display_results(text, entities, relations):
    """Display extraction results in a readable format."""
    print("\n" + "="*80)
    print("INPUT TEXT:")
    print("-"*80)
    print(f"  {text}")
    
    print("\n" + "="*80)
    print("EXTRACTED ENTITIES:")
    print("-"*80)
    if entities:
        for idx, ent in enumerate(entities, 1):
            print(f"  [{idx}] {ent['text']:<30} | Type: {ent['type']:<15} | Position: {ent['start']}-{ent['end']}")
    else:
        print("  No entities found")
    
    print("\n" + "="*80)
    print("EXTRACTED RELATIONS:")
    print("-"*80)
    if relations:
        for idx, rel in enumerate(relations, 1):
            print(f"  [{idx}] {rel['head']:<25} --[{rel['relation']}]--> {rel['tail']}")
    else:
        print("  No relations found")
    print("="*80 + "\n")

# --- 4. EXAMPLE USAGE ---
if __name__ == "__main__":
    # Unzip your file first!
    # folder_path = "./tire_model_export" 
    
    # Assuming they unzip it to the current folder:
    try:
        model, config = load_model_from_zip(".")
        
        text = "ALLANITE is a suspected Russian cyber espionage group, that has primarily targeted the electric utility sector within the United States and United Kingdom."
        ents, rels = predict(text, model, config, debug=True)  # Enable debug mode
        
        display_results(text, ents, rels)
    except Exception as e:
        print("Error:", e)
        print("Make sure config.json and model_weights.pth are in the folder.")