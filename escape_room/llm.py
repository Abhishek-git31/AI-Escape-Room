"""Small wrapper around the Gemini API (google-genai) that both versions share.

The free tier sometimes answers with 503 (model overloaded) or 429 (quota),
so the wrapper retries a couple of times and then tries the next model in
the fallback list instead of just crashing.
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv

# Always read the .env in the project folder, no matter which folder the app
# is started from. override=True means the .env wins even if the terminal
# already has an (empty or old) GEMINI_API_KEY set.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_FALLBACKS = "gemini-2.5-flash-lite,gemini-2.5-flash"


def load_env():
    load_dotenv(ENV_PATH, override=True)


def key_problem():
    """Explain why no key was found, so the error message is actually useful."""
    if not ENV_PATH.exists():
        for wrong in (".env.txt", ".env.rtf", "env", ".env.example.txt"):
            if (PROJECT_ROOT / wrong).exists():
                return (f"I found '{wrong}' in {PROJECT_ROOT} but not '.env'. "
                        f"Rename it to exactly '.env' (no extension).")
        return f"There is no .env file in {PROJECT_ROOT}. Copy .env.example to .env and put your key in it."
    text = ENV_PATH.read_text(encoding="utf-8", errors="ignore")
    if "GEMINI_API_KEY" not in text:
        return f"{ENV_PATH} exists but has no line starting with GEMINI_API_KEY=."
    if "your_gemini_api_key_here" in text:
        return f"{ENV_PATH} still has the placeholder. Replace your_gemini_api_key_here with your real key and save."
    return f"{ENV_PATH} has a GEMINI_API_KEY line, but it's empty. Check the file is saved and restart the app."


class LLMError(Exception):
    pass


class GeminiLLM:
    def __init__(self, api_key=None, model=None, fallbacks=None):
        load_env()  # re-read every new game, so editing .env doesn't need a code change
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.api_key = key.strip().strip('"').strip("'")
        primary = model or os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        extra = fallbacks or os.getenv("GEMINI_FALLBACK_MODELS", DEFAULT_FALLBACKS)
        self.models = [primary] + [m.strip() for m in extra.split(",") if m.strip() and m.strip() != primary]
        self._client = None

    @property
    def available(self):
        # A placeholder key from .env.example doesn't count.
        return bool(self.api_key) and "your_" not in self.api_key

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(self, system, contents, json_mode=False, retries=2):
        """Send a prompt and return the text. `contents` can be a string or a list of chat turns."""
        if not self.available:
            raise LLMError("No Gemini API key set. Add GEMINI_API_KEY to your .env file.")
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2 if json_mode else 0.8,
            response_mime_type="application/json" if json_mode else None,
        )
        last_error = None
        for model in self.models:
            for attempt in range(retries + 1):
                try:
                    response = self._get_client().models.generate_content(
                        model=model, contents=contents, config=config
                    )
                    return response.text or ""
                except Exception as e:  # the SDK raises different error types, so keep it simple
                    last_error = e
                    message = str(e)
                    if any(code in message for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    if any(code in message for code in ("404", "NOT_FOUND")):
                        break  # this model isn't available for the key, try the next one
                    raise LLMError(friendly_error(message)) from e
        raise LLMError(friendly_error(str(last_error)))


def friendly_error(message):
    if "API key not valid" in message or "401" in message or "403" in message:
        return "The Gemini API key is not valid. Create a new one in Google AI Studio and put it in .env."
    if "429" in message or "RESOURCE_EXHAUSTED" in message:
        return "The free Gemini quota is used up for now. Wait a bit or try another model."
    if "503" in message or "UNAVAILABLE" in message:
        return "Gemini is overloaded right now. Wait a minute and try again."
    if "404" in message or "NOT_FOUND" in message:
        return "The Gemini model in .env wasn't found. Remove GEMINI_MODEL to use the default."
    return f"Gemini error: {message[:200]}"
