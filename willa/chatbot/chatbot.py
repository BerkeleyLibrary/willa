"""Implements the Chatbot class for Willa."""

import logging
import uuid
from itertools import filterfalse
from typing import Optional

from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage, AIMessage, ChatMessage
from langchain_core.runnables.config import RunnableConfig

from willa.chatbot.graph_manager import get_graph_manager

LOGGER = logging.getLogger(__name__)
"""The logging instance used for Chatbot log messages."""


class Chatbot:  # pylint: disable=R0903
    """An instance of a Willa chatbot.

    The ``Chatbot`` class provides the ability to ask a question and receive
    answers based on loaded oral histories.
    """

    def __init__(self,
                 thread_id: Optional[str] = None,
                 conversation_thread: Optional[list[dict|AnyMessage]] = None):
        """Create a new Willa chatbot instance.

        :param Optional[str] thread_id: The ID of the thread for this conversation.
        :param Optional[list[dict|AnyMessage]] conversation_thread: conversation thread from
            chainlit data_layer
        """
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
        def is_tind_message(candidate: dict|AnyMessage) -> bool:
            """Determines if a message is a TIND message."""
            return isinstance(candidate, BaseMessage) and 'tind' in candidate.response_metadata
        conversation = filterfalse(is_tind_message, self.previous_conversation)
        self.graph_manager.update_state(self.config, {"messages": list(conversation)})

        LOGGER.debug("Initialized conversation with %d messages for thread %s",
                     len(self.previous_conversation), self.thread_id)

    def ask(self, question: str) -> dict[str, str]:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns: The answer given by the model. Key is the message type.
        :rtype: dict[str, str]
        """

        result = self.graph_manager.invoke(
            {
                "messages": [HumanMessage(content=question)]  # type: ignore[arg-type]
             },
            config=self.config
        )

        # Return the last AI/system_mesage in content
        ai_message = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        tind_message = [msg for msg in result["messages"]
                        if isinstance(msg, ChatMessage) and msg.role == 'TIND']

        answers: dict[str, str] = {}

        if tind_message:
            answers["tind_message"] = str(tind_message[-1].content)

        if ai_message:
            answers["ai_message"] = str(ai_message[-1].content)

        if len(answers) == 0:
            return {"no_result": "I'm sorry, I couldn't generate a response."}

        return answers
