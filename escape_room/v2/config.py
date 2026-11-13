"""Loads the room from config/game_v2.json and matches player words to real objects.

I kept all the room content in JSON so the engine doesn't need to know
anything about libraries, books or paintings. In theory I could make a
second room just by writing a new JSON file.
"""

import json
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "game_v2.json"


def load_config(path=DEFAULT_CONFIG):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean(text):
    text = (text or "").lower().strip()
    for word in ("the ", "a ", "an ", "my ", "that ", "this "):
        if text.startswith(word):
            text = text[len(word):]
    return text.strip(" .!?")


def resolve_object(config, word):
    """Turn something like 'the shelf' into 'bookshelf'. Returns None if it isn't in the room."""
    word = clean(word)
    if not word:
        return None
    for name, obj in config["objects"].items():
        if word == name or word in obj["aliases"]:
            return name
    return None


def resolve_item(config, word):
    """Same idea as resolve_object, but for things you can pick up."""
    word = clean(word)
    if not word:
        return None
    for name, item in config["items"].items():
        if word == name or word in item["aliases"]:
            return name
    return None


def secret_codes(config):
    """All the codes the model is never allowed to say unless the engine revealed them."""
    return list(config["codes"].values())
