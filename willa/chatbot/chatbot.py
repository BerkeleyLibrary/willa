"""Implements the Chatbot class for Willa."""

import os

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores.base import VectorStore

import willa.config  # pylint: disable=W0611


_PROMPT_FILE: str = os.getenv('PROMPT_TEMPLATE',
                              os.path.join(os.path.dirname(__package__),
                                           'prompt_templates', 'initial_prompt.txt'))
"""The file from which to load the system prompt."""


with open(_PROMPT_FILE, encoding='utf-8') as f:
    _SYS_PROMPT: str = f.read()
    """The system prompt."""


PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYS_PROMPT),
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

    def __init__(self, vector_store: VectorStore, model: BaseChatModel,
                 conversation_history: list[dict[str, str]]=None):
        """Create a new Willa chatbot instance.

        :param vector_store: The vector store to use for searching.
        :param model: The LLM to use for processing.
        :param conversation_history: The history of the conversation.
        """
        self.vector_store = vector_store
        self.model = model
        self.chain = PROMPT | self.model
        self.conversation_history = conversation_history

    def ask(self, question: str) -> str:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns: The answer given by the model.
        """
        matching_docs = self.vector_store.similarity_search(question)
        context = '\n\n'.join(doc.page_content for doc in matching_docs)

        conversation_context = ""
        if self.conversation_history:
            conversation_context = "\n".join([
                f"{entry['role']}: {entry['content']}" for entry in self.conversation_history
            ]) + "\n\n"

        answer = self.chain.invoke({'conversation_context': conversation_context,
                                    'question': question, 'context': context})
        return answer.text()
