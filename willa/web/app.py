"""
Implementation of the Web interface for Willa.
"""

import os

import chainlit as cl
from chainlit.types import ThreadDict
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama, OllamaEmbeddings

from willa.chatbot import Chatbot
from willa.config import OLLAMA_URL
from willa.etl.pipeline import run_pipeline
from willa.web.cas_provider import CASProvider
from willa.web.inject_custom_auth import add_custom_oauth_provider


STORE = InMemoryVectorStore(OllamaEmbeddings(model='nomic-embed-text', base_url=OLLAMA_URL))
"""The vector store."""


run_pipeline(STORE)

add_custom_oauth_provider('cas', CASProvider())


BOT = Chatbot(STORE, ChatOllama(model=os.getenv('CHAT_MODEL', 'gemma3n:e4b'),
                                temperature=float(os.getenv('CHAT_TEMPERATURE', '0.5')),
                                base_url=OLLAMA_URL))
"""The Chatbot instance to use for chatting."""


# pylint: disable=unnecessary-pass
# pylint: disable=unused-argument
# placeholder. Not being used yet
@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    """Resume chat session for data persistence."""
    pass
# pylint: enable=unnecessary-pass
# pylint: enable=unused-argument


@cl.on_message
async def chat(message: cl.Message) -> None:
    """Handle an incoming chat message."""
    reply = await cl.make_async(BOT.ask)(message.content)

    await cl.Message(
        author='Willa',
        content=reply
    ).send()


# Chainlit erroneously defines the callback as taking an `id_token` param that is never passed.
@cl.oauth_callback  # type: ignore[arg-type]
async def oauth_callback(provider_id: str, _token: str, _raw_user_data: dict[str, str],
                         default_user: cl.User) -> cl.User | None:
    """Handle OAuth authentication."""
    if provider_id != 'cas':
        return None

    return default_user
