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
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.embeddings = [MagicMock(values=fake_vector)]

    with patch("google.genai.Client") as mock_client_cls:
        mock_client_instance = MagicMock()
        mock_client_cls.return_value = mock_client_instance
        mock_client_instance.models.embed_content.return_value = mock_response

        embedder = GeminiEmbedder(api_key="fake_key")
        result = embedder.embed("hello world")
        assert isinstance(result, list)
        assert len(result) == 768
        assert result == fake_vector
        mock_client_instance.models.embed_content.assert_called_once()



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
