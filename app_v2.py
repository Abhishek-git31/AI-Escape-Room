"""Gradio interface for Version 2 (Python engine + LLM for language).

Run:  python app_v2.py   (or: python run.py v2)
Works without an API key (offline mode).
"""

import gradio as gr

from escape_room.llm import GeminiLLM
from escape_room.v2.game import GameV2
from escape_room.v2.parser import empty_intent
from escape_room.v2.state import summary

INTRO_MD = """
# AI Escape Room - Version 2
*Python keeps the rules, the LLM tells the story.* You are locked in an old library.
Examine things, pick up items, use them and find the code for the door.
"""


def mode_text(game):
    if game.online:
        return f"Mode: **online** (Gemini - {game.llm.models[0]})"
    return "Mode: **offline** (no API key - regex parser and plain narration)"


def new_game():
    game = GameV2(GeminiLLM())
    history = [{"role": "assistant", "content": game.intro()}]
    return game, history, summary(game.state), mode_text(game)


def _play(game, history, text, intent=None, show_user=True):
    reply, _, _ = game.turn(text, intent)
    if show_user:
        history = history + [{"role": "user", "content": text}]
    history = history + [{"role": "assistant", "content": reply}]
    return history


def send(message, history, game):
    if not message.strip():
        return "", history, game, summary(game.state)
    history = _play(game, history, message)
    return "", history, game, summary(game.state)


def show_inventory(history, game):
    history = _play(game, history, "inventory", empty_intent("inventory"), show_user=False)
    return history, game, summary(game.state)


def show_hint(history, game):
    history = _play(game, history, "hint", empty_intent("hint"), show_user=False)
    return history, game, summary(game.state)


def restart(game):
    # A brand-new game also re-reads .env, so a key added later switches it to online mode.
    return new_game()


def build():
    with gr.Blocks(title="AI Escape Room - V2") as demo:
        gr.Markdown(INTRO_MD)
        game_state = gr.State()
        with gr.Row():
            with gr.Column(scale=3):
                chat = gr.Chatbot(height=460, label="Game Master")
                box = gr.Textbox(placeholder="e.g. examine the bookshelf", label="What do you do?")
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    inv_btn = gr.Button("Inventory")
                    hint_btn = gr.Button("Hint")
                    restart_btn = gr.Button("Restart game")
            with gr.Column(scale=1):
                gr.Markdown("### Game state")
                status = gr.Markdown()
                mode = gr.Markdown()

        demo.load(new_game, outputs=[game_state, chat, status, mode])
        box.submit(send, [box, chat, game_state], [box, chat, game_state, status])
        send_btn.click(send, [box, chat, game_state], [box, chat, game_state, status])
        inv_btn.click(show_inventory, [chat, game_state], [chat, game_state, status])
        hint_btn.click(show_hint, [chat, game_state], [chat, game_state, status])
        restart_btn.click(restart, [game_state], [game_state, chat, status, mode])
    return demo


if __name__ == "__main__":
    build().launch()
