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
    bot = Chatbot(my_store, model, [])

    console.print('This is [bold purple]Willa[/bold purple], ready to answer your question.')
    console.print('Ask me a question about the Oral Histories at '
                '[bold blue]Berkeley[/bold blue] [bold yellow]Library[/bold yellow]!')
    console.print('Conversation history is maintained within this session.')

    while True:
        console.print()  # Empty line after the pipeline output or prior answer.
        console.print('To stop and return to your shell, type `quit`.\n')
        # if bot.conversation_history:
        #     console.print(f'Conversation count: {(len(bot.conversation_history))//2}')

        # console.print('Your previous conversation:')
        # for entry in bot.conversation_history:
        #     console.print(f"  {entry['role']}: {entry['content']}")
        # console.print('\n')
        question = console.input('> ')
        if question == 'quit':
            break

        with console.status('[bold green]Thinking...'):
            answer = bot.ask(question)

        # Update conversation history
        bot.conversation_history.extend([
            {"role": "human", "content": question},
            {"role": "assistant", "content": answer}
        ])

        console.print(answer)


if __name__ == "__main__":
    main()
