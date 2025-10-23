
#!/usr/bin/env python3
"""
Quick NER test using Hugging Face transformers.
Run: python ner/ner_quick_test.py
"""
from transformers import pipeline

def load_sentences(path):
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def main():
    print("Loading NER pipeline (dslim/bert-base-NER)... this may take a moment the first time.")
    nlp = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
    sentences = load_sentences("data/sample_sentences.txt")
    for s in sentences:
        print("\nTEXT:", s)
        ents = nlp(s)
        for e in ents:
            print(f"  - {e['word']} -> {e['entity_group']} (score={e['score']:.3f})")

if __name__ == "__main__":
    main()
