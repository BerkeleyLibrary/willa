"""
Implementation of the Web interface for Willa.
"""

import logging

import chainlit as cl
from chainlit.types import ThreadDict, CommandDict, Feedback
from langfuse import get_client

from willa.chatbot import Chatbot
from willa.config import CONFIG
from willa.web.cas_provider import CASProvider
from willa.web.inject_custom_auth import add_custom_oauth_provider

langfuse = get_client()

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

# pylint: disable=not-context-manager
@cl.on_feedback
async def on_feedback(feedback: Feedback) -> None:
    """Send feedback to langfuse"""
    langfuse.create_score(
        trace_id=cl.user_session.get("trace_id"),
        data_type='BOOLEAN',
        name='feedback',
        value=feedback.value,
        comment=feedback.comment
    )
# pylint: enable=not-context-manager

# pylint: disable="unused-argument"
@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    """Resume chat session for data persistence."""
    await cl.context.emitter.set_commands(COMMANDS)
# pylint: enable="unused-argument"


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

        if 'trace_id' in reply:
            cl.user_session.set("trace_id", reply['trace_id'])
            cl.context.current_step.metadata = {"trace_id":reply['trace_id']}

        if 'ai_message' in reply:
            await cl.Message(content=reply['ai_message']).send()

        if 'tind_message' in reply:
            tind_refs = cl.CustomElement(
                name='tind-refs',
                props={'tind_message': reply['tind_message']}
                )
            msg = cl.Message(
                author='TIND',
                content='References:',
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
