"""Implements the Chatbot class for Willa."""

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores.base import VectorStore

from willa.config import CONFIG
from willa.tind import format_tind_context

with open(CONFIG['PROMPT_TEMPLATE'], encoding='utf-8') as f:
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

    def __init__(self, vector_store: VectorStore, model: BaseChatModel):
        """Create a new Willa chatbot instance.

        :param VectorStore vector_store: The vector store to use for searching.
        :param BaseChatModel model: The LLM to use for processing.
        """
        self.vector_store = vector_store
        self.model = model
        self.chain = PROMPT | self.model

    def ask(self, question: str) -> str:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns str: The answer given by the model.
        """
        matching_docs = self.vector_store.similarity_search(question)
        tind_metadata = format_tind_context.get_tind_context(matching_docs)
        context = '\n\n'.join(doc.page_content for doc in matching_docs)
        answer = self.chain.invoke({'question': question, 'context': context})
        return answer.text() + tind_metadata
