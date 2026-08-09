import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


class GeminiEmbedder:
    """Gemini API client for generating 768-dimensional text embeddings using text-embedding-004 / gemini-embedding-001."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "models/gemini-embedding-001",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self._client = genai.Client(api_key=self.api_key) if self.api_key else None

    def embed(self, text: str) -> list[float]:
        """Generate a 768-dimensional vector embedding for the given text.

        Raises:
            ValueError: If text is empty, None, or invalid string.
            ValueError: If GEMINI_API_KEY environment variable or api_key parameter is missing.
        """
        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError("Text to embed must be a non-empty string.")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable or api_key parameter must be set.")

        if not self._client:
            self._client = genai.Client(api_key=self.api_key)

        response = self._client.models.embed_content(
            model=self.model_name,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768),
        )
        return list(response.embeddings[0].values)

