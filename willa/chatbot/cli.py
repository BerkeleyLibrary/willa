"""
Provide a command line interface to the Willa chatbot.
"""

from rich.console import Console

from willa.chatbot import Chatbot


def main() -> None:
    """The entry point for the Willa chatbot command line interface."""
    console = Console()

    while True:
        bot = Chatbot()

        console.print()  # Empty line after the pipeline output or prior answer.
        console.print('This is [bold purple]Willa[/bold purple], ready to answer your question.')
        console.print('Ask me a question about the Oral Histories at '
                      '[bold blue]Berkeley[/bold blue] [bold yellow]Library[/bold yellow]!')
        console.print('To stop and return to your shell, type `quit`.\n')

        question = console.input('> ')
        if question == 'quit':
            break

        with console.status('[bold green]Thinking...'):
            answer = bot.ask(question)

        for message_type, result in answer.items():
            console.print(f"{message_type}: {result}")


if __name__ == "__main__":
    main()
