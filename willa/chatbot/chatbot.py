"""Implements the Chatbot class for Willa."""

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores.base import VectorStore
from langchain_ollama import ChatOllama

import willa.config  # pylint: disable=W0611


_PROMPT_FILE: str = os.getenv('PROMPT_FILE',
                              os.path.join(os.path.dirname(__package__), 'prompt.txt'))
"""The file from which to load the system prompt."""


with open(_PROMPT_FILE, encoding='utf-8') as f:
    _SYS_PROMPT: str = f.read()
    """The system prompt."""


PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYS_PROMPT),
        ("human", "{input}"),
    ]
)
"""The prompt template to use for initiating a chatbot."""


class Chatbot:  # pylint: disable=R0903
    """An instance of a Willa chatbot.

    The ``Chatbot`` class provides the ability to ask a question and receive
    answers based on loaded oral histories.

    In the future, contexts will be preserved within an instance, so multiple
    questions can be asked in succession.  See AP-375.
    """

    def __init__(self, vector_store: VectorStore):
        """Create a new Willa chatbot instance.

        :param vector_store: The vector store to use for searching.
        """
        self.vector_store = vector_store
        self.ollama = ChatOllama(model=os.getenv('CHAT_MODEL', 'gemma3n:e4b'),
                                 temperature=0.5)
        self.chain = PROMPT | self.ollama

    def ask(self, question: str) -> str:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns: The answer given by the model.
        """
        answer = self.chain.invoke({'input': question})
        return answer.text()
