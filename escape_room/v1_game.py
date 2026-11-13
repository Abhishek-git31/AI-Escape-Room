"""Version 1: the LLM is the whole game.

The room, the rules and even the secret codes are all written into one
system prompt. Every turn I send the full chat history back to Gemini and
it decides what happens. There is no separate game state at all.

This was my first attempt and it plays fine when you play nicely. But
because everything depends on the model, it can forget things, make up
objects, or be convinced to give away the codes. Version 2 fixes that.
"""

from .llm import LLMError, key_problem

SYSTEM_PROMPT = """You are the Game Master of a text escape room.

The player wakes up locked in an old library. Describe things vividly but keep
answers short (2-4 sentences). Stay in character.

THE ROOM (only these things exist):
- desk: an old wooden desk. Carved into it: "The books know the way to the drawer."
- bookshelf: four red books stick out. Inside them are the numbers 5, 2, 8 and 6.
- drawer: in the desk, with a four-digit lock. The code is 5286. Inside is a small brass key.
- painting: a lighthouse painting with a tiny keyhole in the frame. The brass key opens it.
  Behind it is a hidden panel with a piece of paper that says 7314.
- door: a heavy door with a keypad. The code is 7314.

RULES:
- The player has to find things in order: books -> drawer code -> key -> painting -> paper -> door.
- The player can only use items they picked up earlier in this conversation.
- Do not reveal a number before the player finds it.
- Wrong codes do nothing.
- When the player enters 7314 on the door, describe the escape and end your
  message with the word ESCAPED in capitals.
"""


class GameV1:
    def __init__(self, llm):
        self.llm = llm
        self.history = []   # the only "memory" this version has
        self.escaped = False

    def intro(self):
        return ("You wake up on a dusty carpet in an old library. There is a desk, a bookshelf, "
                "a painting and a locked door with a keypad. What do you do?")

    def restart(self):
        self.history = []
        self.escaped = False

    def turn(self, text):
        if not self.llm.available:
            return ("I can't run without a Gemini API key. Version 1 needs the LLM for everything.\n\n"
                    f"**What's wrong:** {key_problem()}\n\n"
                    "After fixing it, click **Restart game** (or restart the app).")

        self.history.append({"role": "user", "parts": [{"text": text}]})
        try:
            reply = self.llm.generate(SYSTEM_PROMPT, self.history)
        except LLMError as e:
            self.history.pop()  # don't keep a turn that never got an answer
            return f"Something went wrong talking to Gemini: {e}"

        self.history.append({"role": "model", "parts": [{"text": reply}]})
        if "ESCAPED" in reply:
            self.escaped = True
        return reply
