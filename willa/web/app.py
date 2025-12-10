"""
Implementation of the Web interface for Willa.
"""

import logging
import os

import chainlit as cl
from chainlit.data.chainlit_data_layer import ChainlitDataLayer
from chainlit.types import ThreadDict, CommandDict

from willa.chatbot import Chatbot
from willa.config import CONFIG
from willa.web.cas_provider import CASProvider
from willa.web.inject_custom_auth import add_custom_oauth_provider


LOGGER = logging.getLogger(__name__)
"""The logging object for this module."""


_THREAD_BOTS = {}
"""The Chatbot instances associated with each thread."""


COMMANDS: list[CommandDict] = [
  {
      "id": "Copy Transcript",
      "icon": "clipboard",
      "button": True,
      "persistent": False,
      "description": "Copy the conversation transcript to the clipboard"
  },
]


@cl.on_chat_start
async def ocs() -> None:
    """loaded when new chat is started"""
    await cl.context.emitter.set_commands(COMMANDS)


# pylint: disable="unused-argument"
@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    """Resume chat session for data persistence."""
    await cl.context.emitter.set_commands(COMMANDS)
# pylint: enable="unused-argument"


@cl.data_layer
def data_layer() -> ChainlitDataLayer:
    """Retrieve the data layer to use with Chainlit.

    Simple wrapper around the native one that uses our ``POSTGRES_*`` env vars.
    """
    def _pg(var: str) -> str:
        return os.environ[f'POSTGRES_{var}']

    def _secret() -> str:
        if 'POSTGRES_PASSWORD' in os.environ:
            return os.environ['POSTGRES_PASSWORD']

        with open(os.environ.get('POSTGRES_PASSWORD_FILE',
                                 '/run/secrets/POSTGRES_PASSWORD'), 'r', encoding='utf8') as p_file:
            return p_file.read()

    database_url = os.environ.get(
        'DATABASE_URL', f"postgresql://{_pg('USER')}:{_secret()}@{_pg('HOST')}/{_pg('DB')}"
    )
    return ChainlitDataLayer(database_url=database_url)


def _get_history() -> str:
    """Get chat history for thread"""
    history = cl.chat_context.to_openai()
    contents = [h["content"] for h in history]
    content = "\n\n".join(contents)

    return content


def _get_or_create_bot(thread_id: str) -> Chatbot:
    """Get or create a bot instance for the given thread."""
    previous_conversation = cl.chat_context.to_openai()

    # If it's a new conversation, we don't want to pass the user's
    # initial query as a previous conversation
    if len(previous_conversation) <= 1:
        previous_conversation = []
    if thread_id not in _THREAD_BOTS:
        _THREAD_BOTS[thread_id] = Chatbot(
            thread_id=thread_id,
            conversation_thread=previous_conversation
        )

    return _THREAD_BOTS[thread_id]


@cl.on_message
async def chat(message: cl.Message) -> None:
    """Handle an incoming chat message."""

    if message.command == 'Copy Transcript':
        chat_history = _get_history()
        await cl.send_window_message(f"Clipboard: {chat_history}")

        await cl.Message(
          author='System',
          content="Transcript copied to clipboard!"
        ).send()
    else:
        # Use thread-specific
        bot = _get_or_create_bot(message.thread_id)

        reply = await cl.make_async(bot.ask)(message.content)

        if 'ai_message' in reply:
            await cl.Message(content=reply['ai_message']).send()

        if 'tind_message' in reply:
            tind_refs = cl.CustomElement(
                name='tind-refs',
                props={'tind_message': reply['tind_message']}
                )
            msg = cl.Message(
                author='TIND',
                content='',
                elements=[tind_refs],
                metadata={'tind_message': reply['tind_message']}
                )
            await msg.send()

        if 'no_results' in reply:
            await cl.Message(author='System', type='system_message',
                             content=reply['no_results']).send()


if CONFIG['NULL_AUTH'].lower() == 'true':
    LOGGER.warning('Null authentication backend is enabled: all login attempts will succeed.')

    @cl.password_auth_callback
    async def password_auth_callback(username: str, _password: str) -> cl.User:
        """Handle password authentication (null; all login attempts will succeed)."""
        return cl.User(identifier=username, metadata={'role': 'admin', 'provider': 'null'})
else:
    add_custom_oauth_provider('cas', CASProvider())

    # Chainlit erroneously defines the callback as taking an `id_token` param that is never passed.
    @cl.oauth_callback  # type: ignore[arg-type]
    async def oauth_callback(provider_id: str, _token: str, _raw_user_data: dict[str, str],
                             default_user: cl.User) -> cl.User | None:
        """Handle OAuth authentication."""
        if provider_id != 'cas':
            return None

        return default_user
