"""Tests for the rules in engine.py. These are the most important tests."""

from escape_room.v2.engine import apply


def act(state, config, action, **kw):
    intent = {"action": action, "target": None, "item": None, "code": None, "reason": None}
    intent.update(kw)
    return apply(state, config, intent)


def solve_until(state, config, step):
    """Play the real solution up to (and including) a named step."""
    steps = [
        ("bookshelf", dict(action="examine", target="bookshelf")),
        ("books", dict(action="examine", target="books")),
        ("drawer", dict(action="enter_code", target="drawer", code="5286")),
        ("key", dict(action="take", item="key")),
        ("painting", dict(action="use", item="key", target="painting")),
        ("paper", dict(action="take", item="paper")),
        ("read", dict(action="examine", target="paper")),
    ]
    for name, kw in steps:
        act(state, config, **kw)
        if name == step:
            return


# --- normal play ---

def test_full_walkthrough_escapes(state, config):
    solve_until(state, config, "read")
    result = act(state, config, "enter_code", target="door", code="7314")
    assert result["ok"] and state["escaped"] and state["door_unlocked"]


def test_examining_books_reveals_drawer_digits(state, config):
    act(state, config, "examine", target="bookshelf")
    result = act(state, config, "examine", target="books")
    assert "5, 2, 8 and 6" in result["facts"]


def test_aliases_work(state, config):
    assert act(state, config, "examine", target="the shelf")["event"] == "examined_bookshelf"
    assert act(state, config, "examine", target="picture")["event"] == "examined_painting"


def test_look_shows_intro(state, config):
    assert act(state, config, "look")["facts"] == config["intro"]


# --- order of puzzles ---

def test_books_hidden_until_bookshelf_examined(state, config):
    result = act(state, config, "examine", target="books")
    assert not result["ok"]
    assert "5" not in result["facts"]


def test_cannot_read_paper_without_having_it(state, config):
    result = act(state, config, "examine", target="paper")
    assert not result["ok"]
    assert "7314" not in result["facts"]


def test_key_not_reachable_before_drawer_open(state, config):
    result = act(state, config, "take", item="key")
    assert not result["ok"]
    assert state["inventory"] == []


def test_paper_not_reachable_before_panel_open(state, config):
    solve_until(state, config, "key")
    result = act(state, config, "take", item="paper")
    assert not result["ok"]
    assert "paper" not in state["inventory"]


# --- inventory rules ---

def test_cannot_use_item_not_collected(state, config):
    result = act(state, config, "use", item="key", target="painting")
    assert result["event"] == "not_in_inventory"
    assert not state["panel_open"]


def test_cannot_take_twice(state, config):
    solve_until(state, config, "key")
    result = act(state, config, "take", item="key")
    assert result["event"] == "already_have"
    assert state["inventory"].count("key") == 1


def test_cannot_take_furniture(state, config):
    result = act(state, config, "take", item="desk")
    assert result["event"] == "cannot_take"


def test_key_on_wrong_target_does_nothing(state, config):
    solve_until(state, config, "key")
    result = act(state, config, "use", item="key", target="door")
    assert not result["ok"]
    assert not state["door_unlocked"]


# --- codes ---

def test_wrong_drawer_code(state, config):
    result = act(state, config, "enter_code", target="drawer", code="1111")
    assert result["event"] == "wrong_code"
    assert not state["drawer_unlocked"]
    assert state["wrong_codes"] == 1


def test_wrong_door_code(state, config):
    result = act(state, config, "enter_code", target="door", code="0000")
    assert result["event"] == "wrong_code"
    assert not state["escaped"]


def test_drawer_code_does_not_open_door(state, config):
    result = act(state, config, "enter_code", target="door", code="5286")
    assert not result["ok"] and not state["escaped"]


def test_code_must_be_four_digits(state, config):
    result = act(state, config, "enter_code", target="drawer", code="52")
    assert result["event"] == "bad_format"


def test_no_keypad_on_painting(state, config):
    result = act(state, config, "enter_code", target="painting", code="5286")
    assert result["event"] == "no_keypad"


def test_spaced_code_still_works(state, config):
    result = act(state, config, "enter_code", target="drawer", code="5 2 8 6")
    assert result["ok"]


# --- things that shouldn't exist ---

def test_nonexistent_object(state, config):
    result = act(state, config, "examine", target="trapdoor")
    assert result["event"] == "no_such_object"
    assert "trapdoor" not in state["examined"]


def test_nonexistent_item(state, config):
    result = act(state, config, "take", item="crowbar")
    assert result["event"] == "no_such_item"
    assert state["inventory"] == []


def test_unknown_action_name_is_safe(state, config):
    result = act(state, config, "teleport")
    assert result["event"] == "unknown"


# --- consistency ---

def test_failed_actions_never_change_flags(state, config):
    before = {k: v for k, v in state.items() if k not in ("turns", "log", "wrong_codes")}
    act(state, config, "use", item="key", target="painting")
    act(state, config, "take", item="paper")
    act(state, config, "enter_code", target="door", code="9999")
    act(state, config, "unknown", reason="authority")
    after = {k: v for k, v in state.items() if k not in ("turns", "log", "wrong_codes")}
    assert before == after


def test_drawer_stays_open(state, config):
    solve_until(state, config, "drawer")
    act(state, config, "enter_code", target="drawer", code="0000")
    assert state["drawer_unlocked"]


def test_nothing_changes_after_escape(state, config):
    solve_until(state, config, "read")
    act(state, config, "enter_code", target="door", code="7314")
    result = act(state, config, "enter_code", target="drawer", code="1111")
    assert result["event"] == "already_escaped"
    assert state["wrong_codes"] == 0


def test_log_records_every_turn(state, config):
    act(state, config, "look")
    act(state, config, "examine", target="desk")
    assert len(state["log"]) == 2 and state["turns"] == 2


# --- hints ---

def test_hints_never_contain_codes(state, config):
    for step in ["bookshelf", "books", "drawer", "key", "painting", "paper", "read"]:
        hint = act(state, config, "hint")["facts"]
        assert "5286" not in hint and "7314" not in hint
        solve_until(state, config, step)
