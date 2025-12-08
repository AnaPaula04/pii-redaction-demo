
# Individualized Study Starter (Python + Hugging Face)

This starter gives me:
- **Environment setup** for Python, Jupyter, pandas, NumPy, scikit-learn, and Hugging Face
- **Python refresh** exercises (variables, loops, lists/dicts, functions, basic OOP)
- **Quick NER test** using a pre-trained model (`dslim/bert-base-NER`) from Hugging Face

## 1) Create & activate a virtual environment (macOS)
```bash
# from this folder
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 2) Install dependencies
```bash
pip install -r requirements.txt
```

> If PyTorch wheels are slow to resolve, you can install CPU-only:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## 3) Open Jupyter 
```bash
jupyter notebook
```

## 4) Run the Python refresh exercises
Open `exercises/python_basics_exercises.py` and do the TODOs. 
Check `exercises/python_basics_solutions.py` only **after** trying myself.

Run quick tests:
```bash
python exercises/python_basics_exercises.py
```

## 5) Run the NER quick test
```bash
python ner/ner_quick_test.py
```
This will load a pre-trained NER pipeline and extract entities from `data/sample_sentences.txt`.
I can always edit that file to try other examples.

---

### Tips
- If `transformers` asks to install `sentencepiece` or `safetensors`, run:
  ```bash
  pip install sentencepiece safetensors
  ```
- If I hit SSL/timeout issues behind a network, try again or use a different network.
- Keep my virtualenv **activated** while working (`source .venv/bin/activate`).

cat > README.md <<'MD'
# PII Redaction Demo (NER + Regex)

- **Model:** `dslim/bert-base-NER` via `transformers.pipeline("ner", aggregation_strategy="simple")`
- **Masks via NER:** PERSON → `[PERSON_REDACTED]`, LOC → `[LOC_REDACTED]`
- **Masks via regex:** EMAIL, PHONE, SSN (with- and without-dashes when "SSN" present)
- **Flow:** single right-to-left pass for NER (keeps indices stable), then regex
- **Outputs:** 
  - `data/entities_report.jsonl` (entities per line) 
  - `data/redacted_output.txt` (final masked text)
- **Run:** `python -W ignore ner/pii_redact.py data/sample_sentences.txt`
MD


