import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class GeminiEmbedder:
    """Gemini API client for generating 768-dimensional text embeddings using text-embedding-004."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "models/gemini-embedding-001",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_name = model_name

    def embed(self, text: str) -> list[float]:
        """Generate a 768-dimensional vector embedding for the given text.

        Raises:
            ValueError: If text is empty, None, or invalid string.
        """
        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError("Text to embed must be a non-empty string.")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable or api_key parameter must be set.")

        response = genai.embed_content(
            model=self.model_name,
            content=text,
            output_dimensionality=768,
        )
        return response["embedding"]
