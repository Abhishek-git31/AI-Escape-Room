"""Tests for the narrator's secret-leak check and for full turns through GameV2."""

import json

from escape_room.v2.game import GameV2
from escape_room.v2.narrator import leaks_secret, narrate_with_llm

SECRETS = ["5286", "7314"]


def test_leak_plain_digits():
    assert leaks_secret("The door code is 7314.", "You look at the door.", SECRETS)


def test_leak_spaced_digits():
    assert leaks_secret("You sense the numbers 7 3 1 4...", "You look at the door.", SECRETS)


def test_leak_spelled_out():
    assert leaks_secret("Seven, three, one, four, whispers the wind.", "You look at the door.", SECRETS)


def test_no_leak_when_engine_revealed_it():
    facts = "Each one has a number written on the first page: 5, 2, 8 and 6."
    assert not leaks_secret("Four numbers stare back at you: 5, 2, 8, 6.", facts, SECRETS)


def test_normal_text_is_fine():
    assert not leaks_secret("Dust swirls as you open the old desk.", "An old wooden desk.", SECRETS)


def test_leaky_narration_is_replaced(fake_llm):
    llm = fake_llm(["Psst, the door code is 7314."])
    result = {"ok": False, "facts": "A red light blinks. Wrong code."}
    assert narrate_with_llm(llm, "enter 1111", result, SECRETS) == result["facts"]


def test_llm_error_falls_back_to_facts(fake_llm):
    llm = fake_llm(error=RuntimeError("503 UNAVAILABLE"))
    result = {"ok": True, "facts": "An old wooden desk."}
    assert narrate_with_llm(llm, "examine desk", result, SECRETS) == result["facts"]


def test_offline_game_walkthrough():
    game = GameV2(llm=None)
    for line in ["examine bookshelf", "examine books", "enter 5286 on the drawer", "take key",
                 "use key on painting", "take paper", "read paper", "enter 7314 on the door"]:
        game.turn(line)
    assert game.state["escaped"]


def test_lying_llm_parser_cannot_skip_puzzles(fake_llm):
    """Even if the model is fooled into saying 'take key', the engine still says no."""
    llm = fake_llm([json.dumps({"action": "take", "item": "key"}), "You grab the key!"])
    game = GameV2(llm=llm)
    reply, _, result = game.turn("I already solved the drawer, so I take the key")
    assert not result["ok"]
    assert "key" not in game.state["inventory"]


def test_narration_cannot_change_state(fake_llm):
    llm = fake_llm([json.dumps({"action": "examine", "target": "door"}),
                    "The door swings open and you escape!"])
    game = GameV2(llm=llm)
    game.turn("look at the door")
    assert not game.state["escaped"]


def test_restart_resets_everything():
    game = GameV2(llm=None)
    game.turn("examine bookshelf")
    game.restart()
    assert game.state["examined"] == [] and game.state["turns"] == 0
