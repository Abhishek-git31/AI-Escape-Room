"""The rules of the game. This is the most important file in Version 2.

Every action goes through apply(). It checks the state, decides whether the
action works, updates the state, and returns the facts of what happened.
The LLM never gets to decide any of this, it only gets to describe it.

A failed action never changes the state (except counting wrong codes).
"""

from .config import clean, resolve_item, resolve_object

ACTIONS = {"look", "examine", "take", "use", "enter_code", "inventory", "hint", "unknown"}


def _result(ok, event, facts):
    return {"ok": ok, "event": event, "facts": facts}


def apply(state, config, intent):
    action = intent.get("action", "unknown")
    if action not in ACTIONS:
        action = "unknown"

    state["turns"] += 1

    # Once you're out, you're out. Nothing else should change.
    if state["escaped"] and action not in ("inventory", "look"):
        result = _result(False, "already_escaped", "You have already escaped the library. Press Restart to play again.")
    else:
        handler = {
            "look": _look,
            "examine": _examine,
            "take": _take,
            "use": _use,
            "enter_code": _enter_code,
            "inventory": _inventory,
            "hint": _hint,
            "unknown": _unknown,
        }[action]
        result = handler(state, config, intent)

    state["log"].append(f"turn {state['turns']}: {action} -> {result['event']}")
    return result


# ---------- individual actions ----------

def _look(state, config, intent):
    if state["escaped"]:
        return _result(True, "look", "You are standing outside the library, free.")
    return _result(True, "look", config["intro"])


def _examine(state, config, intent):
    raw = intent.get("target") or intent.get("item") or ""
    if raw.strip().lower() in ("room", "library", "around", "everything"):
        return _look(state, config, intent)

    target = resolve_object(config, raw)
    if target is None:
        return _result(False, "no_such_object", f"There is no {clean(raw) or 'such thing'} in this room.")

    obj = config["objects"][target]

    # You have to notice the books on the shelf before you can read them.
    needed = obj.get("needs_examined")
    if needed and needed not in state["examined"]:
        return _result(False, "not_found_yet", f"You don't see any {target} yet. Maybe look around first.")

    # You can only read the paper if you actually have it.
    if target == "paper" and "paper" not in state["inventory"]:
        return _result(False, "not_found_yet", "You don't have any paper to read.")

    if target == "drawer" and state["drawer_unlocked"]:
        text = obj["open_description"]
        if "key" not in state["inventory"]:
            text += " A small brass key is lying inside."
        else:
            text += " It is empty now."
        desc = text
    elif target == "painting" and state["panel_open"]:
        desc = obj["open_description"]
        if "paper" not in state["inventory"]:
            desc += " There is a folded piece of paper inside."
    else:
        desc = obj["description"]

    if target not in state["examined"]:
        state["examined"].append(target)
    return _result(True, f"examined_{target}", desc)


def _take(state, config, intent):
    raw = intent.get("item") or intent.get("target") or ""
    item = resolve_item(config, raw)
    if item is None:
        # Maybe they tried to pick up furniture.
        if resolve_object(config, raw):
            return _result(False, "cannot_take", f"You can't carry the {resolve_object(config, raw)}.")
        return _result(False, "no_such_item", f"There is no {clean(raw) or 'such thing'} here to take.")

    if item in state["inventory"]:
        return _result(False, "already_have", f"You already have the {item}.")

    if item == "key" and not state["drawer_unlocked"]:
        return _result(False, "not_reachable", "You don't see a key anywhere you can reach.")
    if item == "paper" and not state["panel_open"]:
        return _result(False, "not_reachable", "You don't see any paper you can reach.")

    state["inventory"].append(item)
    return _result(True, f"took_{item}", f"You pick up {config['items'][item]['description'].lower().rstrip('.')}.")


def _use(state, config, intent):
    raw_item = intent.get("item") or ""
    item = resolve_item(config, raw_item)
    target = resolve_object(config, intent.get("target") or "")

    if item is None:
        return _result(False, "no_such_item", f"You don't have anything called '{clean(raw_item)}'.")
    if item not in state["inventory"]:
        return _result(False, "not_in_inventory", f"You don't have the {item}. You need to find it first.")
    if target is None:
        return _result(False, "no_such_object", "You're not sure what to use it on.")

    if item == "key" and target == "painting":
        if state["panel_open"]:
            return _result(False, "already_open", "The painting is already open.")
        state["panel_open"] = True
        return _result(True, "panel_opened",
                       "The key fits the tiny keyhole in the frame. With a click the painting swings open, "
                       "showing a hidden panel with a folded piece of paper inside.")

    if item == "key" and target in ("drawer", "door"):
        return _result(False, "wrong_target", f"The key doesn't fit anything on the {target}.")

    return _result(False, "nothing_happens", f"Using the {item} on the {target} does nothing.")


def _enter_code(state, config, intent):
    code = "".join(ch for ch in str(intent.get("code") or "") if ch.isdigit())
    target = resolve_object(config, intent.get("target") or "") or "door"

    if target not in config["codes"]:
        return _result(False, "no_keypad", f"There is nowhere to enter a code on the {target}.")
    if len(code) != 4:
        return _result(False, "bad_format", "The lock needs exactly four digits.")

    if target == "drawer":
        if state["drawer_unlocked"]:
            return _result(False, "already_open", "The drawer is already open.")
        if code == config["codes"]["drawer"]:
            state["drawer_unlocked"] = True
            return _result(True, "drawer_unlocked",
                           "The lock clicks and the drawer slides open. Inside is a small brass key.")

    if target == "door":
        if code == config["codes"]["door"]:
            state["door_unlocked"] = True
            state["escaped"] = True
            return _result(True, "escaped",
                           "The keypad turns green and the heavy door swings open. You step outside. You escaped!")

    state["wrong_codes"] += 1
    return _result(False, "wrong_code", f"You type {code} on the {target}. A red light blinks. Wrong code.")


def _inventory(state, config, intent):
    if not state["inventory"]:
        return _result(True, "inventory", "You aren't carrying anything.")
    return _result(True, "inventory", "You are carrying: " + ", ".join(state["inventory"]) + ".")


def _hint(state, config, intent):
    # Hints nudge you to the next step but never say a code.
    if state["escaped"]:
        text = "You already escaped!"
    elif "bookshelf" not in state["examined"]:
        text = "The carving on the desk mentions books. Have you looked at the bookshelf?"
    elif "books" not in state["examined"]:
        text = "Some books on the shelf look out of place. Take a closer look at them."
    elif not state["drawer_unlocked"]:
        text = "Those four numbers from the books might open something with a four-digit lock nearby."
    elif "key" not in state["inventory"]:
        text = "Something is waiting for you in the open drawer."
    elif not state["panel_open"]:
        text = "Small keys fit small keyholes. Look closely at the painting."
    elif "paper" not in state["inventory"]:
        text = "The hidden panel behind the painting is holding something."
    elif "paper" not in state["examined"]:
        text = "Read the paper you found."
    else:
        text = "You have everything you need. Try the door."
    return _result(True, "hint", text)


def _unknown(state, config, intent):
    reason = intent.get("reason") or ""
    if reason == "authority":
        text = "Nobody in this room has special powers, including you. The door only listens to the right code."
    elif reason == "secret":
        text = "The room keeps its secrets. You'll have to find the codes yourself."
    else:
        text = "That doesn't do anything here. Try examining things, taking items, using items or entering a code."
    return _result(False, "unknown", text)
