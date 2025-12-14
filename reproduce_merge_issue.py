
import json
from merge_entity_relationship_data import filter_and_validate_relations, normalize_entity_text

# Mock Data based on user's input
relationship_data = {
    "sentences": [
        {
            "sentence_id": 1,
            "text": "ALLANITE is a suspected Russian cyber espionage group...",
            "relations": [
                {
                    "head": "ALLANITE",
                    "head_type": "HackOrg",
                    "relation": "targets",
                    "tail": "utility sector within",
                    "tail_type": "Org"
                }
            ]
        }
    ]
}

# Mock Valid Entities (simulating what might be in the merged file)
# Note: "utility sector within" is NOT here, but "ALLANITE" might be (or might not be if it's new)
valid_entities_normalized = {
    "dragonfly", "russian", "united kingdom", "united states"
}

print("Valid Entities:", valid_entities_normalized)
print("Relationship Data:", json.dumps(relationship_data, indent=2))

validated_relations, missing_entities, _ = filter_and_validate_relations(relationship_data, valid_entities_normalized)

print("\n--- Results ---")
print("Validated Relations:", json.dumps(validated_relations, indent=2))
print("Missing Entities:", missing_entities)

if not validated_relations:
    print("\nFAIL: Relationship was discarded because entities were missing from valid set.")
else:
    print("\nSUCCESS: Relationship was preserved.")
