#src/verification/nli_model.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
class NLIModel:

    def __init__(self, model_name="cross-encoder/nli-deberta-v3-large"):
        self.device = "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

        self.labels = ["contradiction", "neutral", "entailment"]

    def predict(self, premise: str, hypothesis: str):

        inputs = self.tokenizer(
            premise,
            hypothesis,
            truncation=True,
            padding=True,
            return_tensors="pt"
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        probs = F.softmax(outputs.logits, dim=1).squeeze()

        scores = {
            label: float(prob)
            for label, prob in zip(self.labels, probs.tolist())
        }

        # normalize (IMPORTANT FIX)
        total = sum(scores.values())
        scores = {k: v / total for k, v in scores.items()}

        label = max(scores, key=scores.get)
        confidence = max(scores.values())

        return label, confidence, scores