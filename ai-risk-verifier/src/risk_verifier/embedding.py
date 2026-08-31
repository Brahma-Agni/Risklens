import hashlib
import math
import re
from itertools import pairwise

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{1,63}", re.IGNORECASE)


class HashingEmbedder:
    """Deterministic local embeddings suitable for exact offline reproducibility."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        normalized = text.replace("_", " ").replace("-", " ")
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(normalized)]
        features = tokens + [f"{a}::{b}" for a, b in pairwise(tokens)]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [value / norm for value in vector]
        return vector
