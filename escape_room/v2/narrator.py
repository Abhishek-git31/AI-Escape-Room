"""Turns the engine's result into the text the player reads.

With an API key, Gemini rewrites the facts in a nicer, spookier way.
Without a key, the facts are shown as they are (this is the offline mode).

Even when Gemini writes the text, I don't fully trust it. leaks_secret()
checks the narration for any code that wasn't already in the facts, also
if it's written with spaces ("7 3 1 4") or in words ("seven three one
four"). If it finds one, the nice narration is thrown away and the plain
facts are shown instead.
"""

import re

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

NARRATOR_PROMPT = """You are the narrator of a text escape room in an old library.
You get the player's message and the FACTS of what happened. Rewrite the facts
as 1-3 short, atmospheric sentences in second person.

Rules:
- The facts are the truth. If the facts say something failed, it failed.
- Do not add objects, items, numbers or events that are not in the facts.
- Never mention any number that is not in the facts.
- Do not give hints beyond the facts.
"""


def _digits_in_words(text):
    """'seven three one four' -> '7314' so spelled-out codes get caught too."""
    out = []
    for word in re.findall(r"[a-z]+", text.lower()):
        if word in WORDS:
            out.append(str(WORDS.index(word)))
        else:
            out.append(" ")
    return "".join(out)


def leaks_secret(narration, facts, secrets):
    squashed = re.sub(r"[^0-9]", "", narration)  # catches "7 3 1 4" and "7-3-1-4"
    spelled = _digits_in_words(narration).replace(" ", "")
    fact_digits = re.sub(r"[^0-9]", "", facts)
    for code in secrets:
        if code in fact_digits:
            continue  # the engine revealed it on purpose, so it's allowed
        if code in squashed or code in spelled:
            return True
    return False


def narrate_plain(result):
    return result["facts"]


def narrate_with_llm(llm, player_text, result, secrets):
    prompt = (
        f"Player said: {player_text}\n"
        f"Action worked: {result['ok']}\n"
        f"FACTS: {result['facts']}"
    )
    try:
        text = llm.generate(NARRATOR_PROMPT, prompt).strip()
    except Exception:
        return narrate_plain(result)
    if not text or leaks_secret(text, result["facts"], secrets):
        return narrate_plain(result)
    return text
