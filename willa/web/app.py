"""
Implementation of the Web interface for Willa.
"""

import os

import chainlit as cl
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama, OllamaEmbeddings

from willa.chatbot import Chatbot
from willa.config import OLLAMA_URL
from willa.etl.pipeline import run_pipeline


STORE = InMemoryVectorStore(OllamaEmbeddings(model='nomic-embed-text', base_url=OLLAMA_URL))
"""The vector store."""


run_pipeline(STORE)


BOT = Chatbot(STORE, ChatOllama(model=os.getenv('CHAT_MODEL', 'gemma3n:e4b'),
                                temperature=float(os.getenv('CHAT_TEMPERATURE', '0.5')),
                                base_url=OLLAMA_URL), [])
"""The Chatbot instance to use for chatting."""


@cl.on_chat_start
async def start():
    """Initialize conversation history when chat starts."""
    cl.user_session.set('conversation_history', [])


@cl.on_message
async def chat(message: cl.Message) -> None:
    """Handle an incoming chat message."""
    # # Get conversation history
    # history = cl.user_session.get("conversation_history", [])

    # Ask with history context
    reply = await cl.make_async(BOT.ask)(message.content)

    #update conversation history
    BOT.conversation_history.extend([
        {"role": "human", "content": message.content},
        {"role": "assistant", "content": reply}
    ])
    cl.user_session.set("conversation_history", BOT.conversation_history)

    await cl.Message(
        author='Willa',
        content=reply
    ).send()
