import os
from unittest.mock import patch
import pytest
from embeddings.gemini_client import GeminiEmbedder


def test_gemini_embedder_empty_input():
    embedder = GeminiEmbedder(api_key="fake_key")
    with pytest.raises(ValueError, match="non-empty string"):
        embedder.embed("")

    with pytest.raises(ValueError, match="non-empty string"):
        embedder.embed(None)

    with pytest.raises(ValueError, match="non-empty string"):
        embedder.embed("   ")


def test_gemini_embedder_missing_key():
    with patch.dict(os.environ, {}, clear=True):
        embedder = GeminiEmbedder(api_key=None)
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            embedder.embed("hello world")


def test_gemini_embedder_mocked():
    fake_vector = [0.1] * 768
    with patch(
        "google.generativeai.embed_content",
        return_value={"embedding": fake_vector},
    ) as mock_embed:
        embedder = GeminiEmbedder(api_key="fake_key")
        result = embedder.embed("hello world")
        assert isinstance(result, list)
        assert len(result) == 768
        mock_embed.assert_called_once_with(
            model="models/gemini-embedding-001", content="hello world", output_dimensionality=768
        )


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY environment variable not set",
)
def test_gemini_embedder_live():
    embedder = GeminiEmbedder()
    result = embedder.embed("hello world")
    assert isinstance(result, list)
    assert len(result) == 768
    assert all(isinstance(x, float) for x in result)
