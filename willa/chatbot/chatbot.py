"""Implements the Chatbot class for Willa."""

import logging
import uuid
from typing import Optional, Annotated, NotRequired
from typing_extensions import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.config import RunnableConfig
from langchain_core.vectorstores.base import VectorStore
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph, add_messages
from langgraph.graph.message import AnyMessage

from willa.config import CONFIG
from willa.tind import format_tind_context

LOGGER = logging.getLogger(__name__)
"""The logging instance used for Chatbot log messages."""


with open(CONFIG['PROMPT_TEMPLATE'], encoding='utf-8') as f:
    _SYS_PROMPT: str = f.read()
    """The system prompt."""


PROMPT = ChatPromptTemplate.from_messages([("system", _SYS_PROMPT)])
"""The prompt template to use for initiating a chatbot."""


class WillaChatbotState(TypedDict):
    """State for the Chatbot LangGraph workflow."""
    messages: Annotated[list[AnyMessage], add_messages]
    context: NotRequired[str]
    search_query: NotRequired[str]
    tind_metadata: NotRequired[str]


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
        workflow = StateGraph(state_schema=WillaChatbotState)

        # Add nodes
        workflow.add_node("prepare_search", self._prepare_search_query)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges
        workflow.add_edge(START, "prepare_search")
        workflow.add_edge("prepare_search", "retrieve_context")
        workflow.add_edge("retrieve_context", "generate_response")

        memory = InMemorySaver()
        self.app = workflow.compile(checkpointer=memory)

        if self.previous_conversation:
            self._initialize_conversation_state()

    def _initialize_conversation_state(self) -> None:
        """Initialize conversation state with the existing messages from the data layer."""
        # TODO: Remove system messages? # pylint: disable=W0511
        self.app.update_state(self.config, {"messages": self.previous_conversation})

        LOGGER.debug("Initialized conversation with %d messages for thread %s",
                     len(self.previous_conversation), self.thread_id)

    def _prepare_search_query(self, state: WillaChatbotState) -> dict[str, str]:
        """Prepare search query from conversation context."""
        messages = state["messages"]

        # Get the latest human message
        human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        if not human_messages:
            return {"search_query": ""}

        latest_question = str(human_messages[-1].content)

        # Initial question: respond to the first question (current behavior)
        search_query = latest_question

        # Combine recent context for better search
        # This could include the last few exchanges for better context
        recent_messages = messages[-6:]  # Last 3 exchanges (human + AI pairs)
        if len(recent_messages) > 2:
            context_parts = []
            for msg in recent_messages[:-1]:  # Exclude the current question
                if isinstance(msg, (HumanMessage, AIMessage)) and msg.content:
                    context_parts.append(str(msg.content))

            if context_parts:
                # Limit context to the most recent 2 exchanges:
                recent_context = ' '.join(context_parts[-4:])
                search_query = f"{recent_context}\n{latest_question}"

        return {"search_query": search_query}

    def _retrieve_context(self, state: WillaChatbotState) -> dict[str, str]:
        """Retrieve relevant context from vector store."""
        search_query = state.get("search_query", "")

        if not search_query:
            return {"context": "", "tind_metadata": ""}

        # Search for relevant documents
        matching_docs = self.vector_store.similarity_search(search_query)

        # Format context and metadata
        context = '\n\n'.join(doc.page_content for doc in matching_docs)
        tind_metadata = format_tind_context.get_tind_context(matching_docs)

        return {"context": context, "tind_metadata": tind_metadata}

    def _generate_response(self, state: WillaChatbotState) -> dict[str, list[AnyMessage]]:
        """Generate response using the model."""
        messages = state["messages"]
        context = state.get("context", "")
        tind_metadata = state.get("tind_metadata", "")

        # Get the latest human message
        latest_message = next(
            (msg for msg in reversed(messages) if isinstance(msg, HumanMessage)),
            None
        )

        if not latest_message:
            return {"messages": [AIMessage(content="I'm sorry, I didn't receive a question.")]}

        # Create system message with context
        system_message = SystemMessage(content=_SYS_PROMPT.format(
            context=context,
            question=latest_message.content
        ))

        # Combine system prompt with conversation history
        # Filter out any existing system messages to avoid duplication
        conversation_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
        all_messages = [system_message] + conversation_messages

        # Get response from model
        response = self.model.invoke(all_messages)

        # Create clean response content
        response_content = str(response.content) if hasattr(response, 'content') else str(response)
        response_content += f"{tind_metadata}" if tind_metadata else ""
        response_messages: list[AnyMessage] = [AIMessage(content=response_content)]
        return {"messages": response_messages}

    def ask(self, question: str) -> str:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns str: The answer given by the model.
        """

        result = self.app.invoke(
            {"messages": [HumanMessage(content=question)]},  # type: ignore[arg-type]
            config=self.config
        )

        # Return the last AI message in content
        ai_message = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if ai_message:
            return str(ai_message[-1].content)
        return "I'm sorry, I couldn't generate a response."
