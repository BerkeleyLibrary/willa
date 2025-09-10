"""Implements the Chatbot class for Willa."""

import logging
import uuid
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.vectorstores.base import VectorStore

from willa.chatbot.graph_manager import get_graph_manager

LOGGER = logging.getLogger(__name__)
"""The logging instance used for Chatbot log messages."""


class Chatbot:  # pylint: disable=R0903
    """An instance of a Willa chatbot.

    The ``Chatbot`` class provides the ability to ask a question and receive
    answers based on loaded oral histories.
    """

    def __init__(self,
                 vector_store: VectorStore,
                 model: BaseChatModel,
                 thread_id: Optional[str] = None,
                 conversation_thread: Optional[list[dict]] = None):
        """Create a new Willa chatbot instance.

        :param VectorStore vector_store: The vector store to use for searching.
        :param BaseChatModel model: The LLM to use for processing.
        :param Optional[str] thread_id: The ID of the thread for this conversation.
        :param Optional[list[dict]] conversation_thread: conversation thread from
            chainlit data_layer
        """
        self.vector_store = vector_store
        self.model = model
        self.thread_id = thread_id or str(uuid.uuid4())
        self.previous_conversation = conversation_thread or []
        self.config: RunnableConfig = {
            "configurable": {"thread_id": self.thread_id}
        }

        # Create LangGraph workflow
        self.graph_manager = get_graph_manager()

        if self.previous_conversation:
            self._initialize_conversation_state()

    def _initialize_conversation_state(self) -> None:
        """Initialize conversation state with the existing messages from the data layer."""
        # TODO: Remove system messages? # pylint: disable=W0511
        self.graph_manager.app.update_state(self.config, {"messages": self.previous_conversation})

        LOGGER.debug("Initialized conversation with %d messages for thread %s",
                     len(self.previous_conversation), self.thread_id)

    def ask(self, question: str) -> str:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns str: The answer given by the model.
        """

        result = self.graph_manager.invoke(
            {
                "messages": [HumanMessage(content=question)]  # type: ignore[arg-type]
             },
            config=self.config,
            vector_store=self.vector_store,
            model=self.model
        )

        # Return the last AI message in content
        ai_message = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if ai_message:
            return str(ai_message[-1].content)
        return "I'm sorry, I couldn't generate a response."
