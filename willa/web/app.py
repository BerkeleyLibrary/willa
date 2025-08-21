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

    # enter user query and reply into db?

    await cl.Message(
        author='Willa',
        content=reply
    ).send()

# @cl.password_auth_callback
# def auth_callback(username: str, password: str):
#     # Fetch the user matching username from your database
#     # and compare the hashed password with the value stored in the database
#     if (username, password) == ("admin", "admin"):
#         return cl.User(
#             identifier="admin", metadata={"role": "admin", "provider": "credentials"}
#         )
#     else:
#         return None

# @cl.on_chat_resume
# async def on_chat_resume(thread):
#     pass


# @cl.step(type="tool")
# async def tool():
#     # Fake tool
#     await cl.sleep(2)
#     return "Response from the tool!"


# @cl.on_message  # this function will be called every time a user inputs a message in the UI
# async def main(message: cl.Message):
#     """
#     This function is called every time a user inputs a message in the UI.
#     It sends back an intermediate response from the tool, followed by the final answer.

#     Args:
#         message: The user's message.

#     Returns:
#         None.
#     """
#         message: The user's message.

#     Returns:
#         None.
#     """



