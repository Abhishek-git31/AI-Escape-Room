"""Gradio interface for Version 1 (LLM-only game master).

Run:  python app_v1.py   (or: python run.py v1)
"""

import gradio as gr

from escape_room.llm import GeminiLLM
from escape_room.v1_game import GameV1

INTRO_MD = """
# AI Escape Room - Version 1
*The LLM runs everything.* You are locked in an old library. Explore, find clues and
open the door. This version needs a Gemini API key.
"""


def new_game():
    game = GameV1(GeminiLLM())
    return game, [{"role": "assistant", "content": game.intro()}]


def send(message, history, game):
    if not message.strip():
        return "", history, game
    reply = game.turn(message)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return "", history, game


def restart(game):
    # A brand-new game also re-reads .env, so a key added later is picked up.
    return new_game()


def build():
    with gr.Blocks(title="AI Escape Room - V1") as demo:
        gr.Markdown(INTRO_MD)
        game_state = gr.State()
        chat = gr.Chatbot(height=460, label="Game Master")
        box = gr.Textbox(placeholder="e.g. examine the bookshelf", label="What do you do?")
        with gr.Row():
            send_btn = gr.Button("Send", variant="primary")
            restart_btn = gr.Button("Restart game")

        demo.load(new_game, outputs=[game_state, chat])
        box.submit(send, [box, chat, game_state], [box, chat, game_state])
        send_btn.click(send, [box, chat, game_state], [box, chat, game_state])
        restart_btn.click(restart, [game_state], [game_state, chat])
    return demo


if __name__ == "__main__":
    build().launch()
