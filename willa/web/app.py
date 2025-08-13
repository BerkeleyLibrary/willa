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
                                base_url=OLLAMA_URL))
"""The Chatbot instance to use for chatting."""


@cl.on_message
async def chat(message: cl.Message) -> None:
    """Handle an incoming chat message."""
    reply = await cl.make_async(BOT.ask)(message.content)

    await cl.Message(
        author='Willa',
        content=reply
    ).send()
