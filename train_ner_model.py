# train_ner_model.py — Run this separately after ml_training_data.csv is generated

import spacy
from spacy.training import Example
import csv

# Load blank model
nlp = spacy.blank("en")
ner = nlp.add_pipe("ner")

# Add labels
ner.add_label("BLOCK")
ner.add_label("ROAD")

# Load training data
TRAIN_DATA = []
with open("/Users/alfredlim/Redpower/rename_images/ml_training_data.csv", 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        text = row['watermark_ocr']
        block = row['block_label']
        road = row['road_label']

        # Create entity spans
        entities = []
        if block:
            start = text.find(block)
            if start != -1:
                entities.append((start, start + len(block), "BLOCK"))
        if road:
            # Clean road for matching
            road_clean = road.replace('_', ' ')
            start = text.find(road_clean)
            if start != -1:
                entities.append((start, start + len(road_clean), "ROAD"))

        # Add to training data
        TRAIN_DATA.append((text, {"entities": entities}))

# Train model
nlp.begin_training()
for i in range(50):  # 50 iterations
    losses = {}
    for text, annotations in TRAIN_DATA:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        nlp.update([example], losses=losses)
    if i % 10 == 0:
        print(f"Epoch {i}, Loss: {losses.get('ner', 0):.3f}")

# Save model
nlp.to_disk("/Users/alfredlim/Redpower/rename_images/ner_model")
print("✅ Model saved to: /Users/alfredlim/Redpower/rename_images/ner_model")