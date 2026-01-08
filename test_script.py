import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
DEVICE = "cpu"

"""
import os

# Set the path to your checkpoint folder
checkpoint_dir = "checkpoint-4089"

# List of files to fix (stripping the " (1)" suffix)
for filename in os.listdir(checkpoint_dir):
    if " (1)" in filename:
        old_path = os.path.join(checkpoint_dir, filename)
        # Remove " (1)" and any extra spaces
        new_name = filename.replace(" (1)", "").strip()
        new_path = os.path.join(checkpoint_dir, new_name)
        
        print(f"Renaming: {filename} -> {new_name}")
        os.rename(old_path, new_path)

print("\n✅ All files renamed! You can now run your test_script.py")"""

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from typing import List, Dict

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
MODEL_PATH = "checkpoint-4089"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MAX_LENGTH = 512
STRIDE = 128
N_BEST = 5
MAX_ANSWER_LENGTH = 40
NULL_THRESHOLD = 0.0  # conservative; tune later if needed

# ---------------------------------------------------------
# LOAD MODEL + TOKENIZER
# ---------------------------------------------------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForQuestionAnswering.from_pretrained(MODEL_PATH)
model.to(DEVICE)
model.eval()

# ---------------------------------------------------------
# SAMPLE CONTRACT PARAGRAPH (REALISTIC LEGAL STYLE)
# ---------------------------------------------------------
context = """
THIS DISTRIBUTOR AGREEMENT ("Agreement") is made and entered into as of
September 7, 1999 ("Effective Date"), by and between Electric City Corp.,
a Delaware corporation ("Company"), and Electric City of Illinois LLC
("Distributor").

The initial term of this Agreement shall expire on September 6, 2004,
unless earlier terminated. This Agreement shall automatically renew
for successive one-year terms unless either party provides written
notice of termination at least ninety (90) days prior to the expiration
of the then-current term.

This Agreement shall be governed by and construed in accordance with
the laws of the State of Delaware.

Distributor agrees not to engage in any business that directly competes
with the Company during the term of this Agreement.
"""

# ---------------------------------------------------------
# 10 COMMON CUAD QUESTIONS
# ---------------------------------------------------------
questions = [
    "Highlight the parts (if any) of this contract related to \"Document Name\".",
    "Highlight the parts (if any) of this contract related to \"Parties\".",
    "Highlight the parts (if any) of this contract related to \"Agreement Date\".",
    "Highlight the parts (if any) of this contract related to \"Effective Date\".",
    "Highlight the parts (if any) of this contract related to \"Expiration Date\".",
    "Highlight the parts (if any) of this contract related to \"Renewal Term\".",
    "Highlight the parts (if any) of this contract related to \"Notice Period To Terminate Renewal\".",
    "Highlight the parts (if any) of this contract related to \"Governing Law\".",
    "Highlight the parts (if any) of this contract related to \"Most Favored Nation\".",
    "Highlight the parts (if any) of this contract related to \"Non-Compete\".",
]

# ---------------------------------------------------------
# CORE QA INFERENCE FUNCTION
# ---------------------------------------------------------
def answer_question(question: str, context: str) -> List[Dict]:
    inputs = tokenizer(
        question,
        context,
        max_length=MAX_LENGTH,
        stride=STRIDE,
        truncation="only_second",
        return_overflowing_tokens=True,
        return_offsets_mapping=True,
        padding="max_length",
        return_tensors="pt"
    )

    answers = []

    for i in range(len(inputs["input_ids"])):
        input_ids = inputs["input_ids"][i].unsqueeze(0).to(DEVICE)
        attention_mask = inputs["attention_mask"][i].unsqueeze(0).to(DEVICE)
        offsets = inputs["offset_mapping"][i]

        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)

        start_logits = outputs.start_logits[0].cpu().numpy()
        end_logits = outputs.end_logits[0].cpu().numpy()

        # Null score (CLS token)
        null_score = start_logits[0] + end_logits[0]

        # Top candidate spans
        start_indexes = np.argsort(start_logits)[-N_BEST:]
        end_indexes = np.argsort(end_logits)[-N_BEST:]

        for start in start_indexes:
            for end in end_indexes:
                if end < start:
                    continue
                length = end - start + 1
                if length > MAX_ANSWER_LENGTH:
                    continue
                if offsets[start] is None or offsets[end] is None:
                    continue

                start_char = offsets[start][0]
                end_char = offsets[end][1]
                text = context[start_char:end_char].strip()

                if not text:
                    continue

                score = start_logits[start] + end_logits[end]
                if score > null_score + NULL_THRESHOLD:
                    answers.append({
                        "text": text,
                        "score": float(score)
                    })

    # Deduplicate & sort
    unique = {}
    for ans in answers:
        unique[ans["text"]] = max(unique.get(ans["text"], -1), ans["score"])

    results = [
        {"text": k, "score": v}
        for k, v in sorted(unique.items(), key=lambda x: x[1], reverse=True)
    ]

    return results[:3]  # top-3 answers max


# ---------------------------------------------------------
# RUN TEST
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n================ CONTRACT CLAUSE EXTRACTION ================\n")

    for q in questions:
        print(f"❓ QUESTION: {q}")
        preds = answer_question(q, context)

        if len(preds) == 0:
            print("   ➤ No answer found.\n")
        else:
            for i, p in enumerate(preds, 1):
                print(f"   ✅ Answer {i}: {p['text']} (score={p['score']:.2f})")
            print()
