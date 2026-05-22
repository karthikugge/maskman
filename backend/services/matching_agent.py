import numpy as np
from sentence_transformers import SentenceTransformer, util

class MatchingAgent:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MatchingAgent, cls).__new__(cls)
        return cls._instance

    @property
    def model(self):
        if self._model is None:
            # We use a compact but powerful model
            print("Loading SentenceTransformer model...")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def get_similarity(self, text1: str, text2: str) -> float:
        """Calculates cosine similarity between two product titles."""
        try:
            # Clean titles slightly
            t1 = text1.lower().strip()
            t2 = text2.lower().strip()
            
            embeddings = self.model.encode([t1, t2], convert_to_tensor=True)
            cosine_score = util.cos_sim(embeddings[0], embeddings[1])
            return float(cosine_score.item())
        except Exception as e:
            print(f"Similarity Calculation Error: {e}")
            return 0.0

matching_agent = MatchingAgent()
