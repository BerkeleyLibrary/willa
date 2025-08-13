"""
Provide a command line interface to the Willa chatbot.
"""

import argparse

from langchain_ollama import ChatOllama
from rich.console import Console

from willa.etl.pipeline import run_pipeline
from willa.chatbot import Chatbot
from willa.config import OLLAMA_URL


def main() -> None:
    """The entry point for the Willa chatbot command line interface."""
    console = Console()

    parser = argparse.ArgumentParser(
        prog='willa-cli',
        description='Provides an AI chatbot interface to Berkeley Library OHC'
    )
    parser.add_argument('-m', '--model', action='store', help='Choose the model to use',
                        default='gemma3n:e4b')
    args = parser.parse_args()

    with console.status("[bold green]Loading documents..."):
        my_store = run_pipeline()

    model = ChatOllama(model=args.model, temperature=0.5, base_url=OLLAMA_URL)

    while True:
        bot = Chatbot(my_store, model)

        console.print()  # Empty line after the pipeline output or prior answer.
        console.print('This is [bold purple]Willa[/bold purple], ready to answer your question.')
        console.print('Ask me a question about the Oral Histories at '
                      '[bold blue]Berkeley[/bold blue] [bold yellow]Library[/bold yellow]!')
        console.print('Each question has its own context; memory is not shared between questions.')
        console.print('To stop and return to your shell, type `quit`.\n')

        question = console.input('> ')
        if question == 'quit':
            break

        with console.status('[bold green]Thinking...'):
            answer = bot.ask(question)

        console.print(answer)


if __name__ == "__main__":
    main()
