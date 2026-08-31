import math

from risk_verifier.embedding import HashingEmbedder


def test_embedding_is_deterministic_and_normalized() -> None:
    embedder = HashingEmbedder(64)
    first = embedder.embed("shared device coordinated accounts")
    second = embedder.embed("shared device coordinated accounts")

    assert first == second
    assert len(first) == 64
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_empty_text_returns_zero_vector() -> None:
    assert HashingEmbedder(32).embed("") == [0.0] * 32
