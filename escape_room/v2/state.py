"""The game state for Version 2.

This dictionary is the only thing that decides where the player is in the
game. The chat history is just for display. If the chat and the state ever
disagree, the state wins.
"""


def new_state():
    return {
        "inventory": [],          # items the player actually picked up
        "examined": [],           # objects the player has looked at
        "drawer_unlocked": False,
        "panel_open": False,      # hidden panel behind the painting
        "door_unlocked": False,
        "escaped": False,
        "wrong_codes": 0,
        "turns": 0,
        "log": [],                # short record of what happened each turn
    }


def summary(state):
    """Short text version of the state for the status panel in the UI."""
    inv = ", ".join(state["inventory"]) or "nothing"
    lines = [
        f"**Inventory:** {inv}",
        f"**Drawer:** {'open' if state['drawer_unlocked'] else 'locked'}",
        f"**Painting panel:** {'open' if state['panel_open'] else 'closed'}",
        f"**Door:** {'unlocked' if state['door_unlocked'] else 'locked'}",
        f"**Turns:** {state['turns']}  |  **Wrong codes:** {state['wrong_codes']}",
    ]
    if state["escaped"]:
        lines.append("**You escaped!**")
    return "\n\n".join(lines)
