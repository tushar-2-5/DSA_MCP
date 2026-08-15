import os
import json
import tempfile
from datetime import date
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Rate limit counter file path
default_path = "/tmp/gemini_daily_count.json"
try:
    os.makedirs(os.path.dirname(default_path), exist_ok=True)
    GEMINI_LIMIT_FILE = default_path
except Exception:
    GEMINI_LIMIT_FILE = os.path.join(tempfile.gettempdir(), "gemini_daily_count.json")

DAILY_LIMIT = 1400


def _check_and_increment_daily_limit():
    today = str(date.today())
    try:
        with open(GEMINI_LIMIT_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError):
        data = {}

    count = data.get(today, 0)
    if count >= DAILY_LIMIT:
        raise RuntimeError(
            f"Gemini daily limit reached ({count}/{DAILY_LIMIT}). "
            "Protecting free tier. Resets at midnight."
        )

    data = {today: count + 1}
    try:
        with open(GEMINI_LIMIT_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

    return count + 1


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
            RuntimeError: If daily request count limit (1400) is reached.
        """
        _check_and_increment_daily_limit()

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


