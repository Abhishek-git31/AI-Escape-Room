"""One turn of Version 2: parse -> apply -> narrate.

This is the glue between the parser, the engine and the narrator. If no
LLM is available, everything still works with the regex parser and the
plain narrator.
"""

from .config import load_config, secret_codes
from .engine import apply
from .narrator import narrate_plain, narrate_with_llm
from .parser import parse_with_llm, parse_with_regex
from .state import new_state


class GameV2:
    def __init__(self, llm=None, config=None):
        self.llm = llm                      # None means offline mode
        self.config = config or load_config()
        self.secrets = secret_codes(self.config)
        self.state = new_state()

    @property
    def online(self):
        return self.llm is not None and self.llm.available

    def intro(self):
        return self.config["intro"] + "\n\nType things like *examine the desk*, *take the key* or *enter 1234 on the door*."

    def restart(self):
        self.state = new_state()

    def turn(self, text, intent=None):
        """Play one turn. `intent` lets buttons (Inventory/Hint) skip the parser."""
        if intent is None:
            intent = parse_with_llm(self.llm, text) if self.online else parse_with_regex(text)
        result = apply(self.state, self.config, intent)
        if self.online:
            reply = narrate_with_llm(self.llm, text, result, self.secrets)
        else:
            reply = narrate_plain(result)
        return reply, intent, result
