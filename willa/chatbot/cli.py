"""
Provide a command line interface to the Willa chatbot.
"""

from rich.console import Console

from willa.etl.pipeline import run_pipeline
from willa.chatbot import Chatbot


def main() -> None:
    """The entry point for the Willa chatbot command line interface."""
    console = Console()

    with console.status("[bold green]Loading documents..."):
        my_store = run_pipeline()

    while True:
        bot = Chatbot(my_store)

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
