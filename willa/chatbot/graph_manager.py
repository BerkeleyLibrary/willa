"""Manages the shared state and workflow for Willa chatbots."""

import logging
from typing import Optional, Annotated, NotRequired
from typing_extensions import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.vectorstores.base import VectorStore
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import AnyMessage

from willa.config import CONFIG, get_lance, get_ollama
from willa.tind import format_tind_context

LOGGER = logging.getLogger(__name__)
"""The logging instance used for graph manager log messages."""

STORE = get_lance()
"""The LanceDB instance used for a vector store."""

MODEL = get_ollama()
"""The ChatOllama instance used for a chat model."""

with open(CONFIG['PROMPT_TEMPLATE'], encoding='utf-8') as f:
    _SYS_PROMPT: str = f.read()
    """The system prompt text."""


class WillaChatbotState(TypedDict):
    """State for the Chatbot LangGraph workflow."""
    messages: Annotated[list[AnyMessage], add_messages]
    context: NotRequired[str]
    search_query: NotRequired[str]
    tind_metadata: NotRequired[str]


class GraphManager:  # pylint: disable=too-few-public-methods
    """Manages the shared LangGraph workflow for all chatbot instances."""

    def __init__(self) -> None:
        self.memory = InMemorySaver()
        self._current_vector_store: Optional[VectorStore] = STORE
        self._current_model: Optional[BaseChatModel] = MODEL
        self.app = self._create_workflow()

    def _create_workflow(self) -> CompiledStateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(state_schema=WillaChatbotState)

        # Add nodes
        workflow.add_node("prepare_search", self._prepare_search_query)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges
        workflow.add_edge(START, "prepare_search")
        workflow.add_edge("prepare_search", "retrieve_context")
        workflow.add_edge("retrieve_context", "generate_response")

        return workflow.compile(checkpointer=self.memory)

    def _prepare_search_query(self, state: WillaChatbotState) -> dict[str, str]:
        """Prepare search query from conversation context."""
        messages = state["messages"]

        # Get the latest human message
        human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        if not human_messages:
            return {"search_query": ""}

        latest_question = str(human_messages[-1].content)
        search_query = latest_question

        # Combine recent context for better search
        recent_messages = messages[-6:]
        if len(recent_messages) > 2:
            context_parts = []
            for msg in recent_messages[:-1]:
                if isinstance(msg, (HumanMessage, AIMessage)) and msg.content:
                    context_parts.append(str(msg.content))

            if context_parts:
                recent_context = ' '.join(context_parts[-4:])
                search_query = f"{recent_context}\n{latest_question}"

        return {"search_query": search_query}

    def _retrieve_context(self, state: WillaChatbotState) -> dict[str, str]:
        """Retrieve relevant context from vector store."""
        search_query = state.get("search_query", "")
        vector_store = self._current_vector_store

        if not search_query or not vector_store:
            return {"context": "", "tind_metadata": ""}

        # Search for relevant documents
        matching_docs = vector_store.similarity_search(search_query)

        # Format context and metadata
        context = '\n\n'.join(doc.page_content for doc in matching_docs)
        tind_metadata = format_tind_context.get_tind_context(matching_docs)

        return {"context": context, "tind_metadata": tind_metadata}

    def _generate_response(self, state: WillaChatbotState) -> dict[str, list[AnyMessage]]:
        """Generate response using the model."""
        messages = state["messages"]
        context = state.get("context", "")
        tind_metadata = state.get("tind_metadata", "")
        model = self._current_model

        if not model:
            return {"messages": [AIMessage(content="Model not available.")]}

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
        conversation_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
        all_messages = [system_message] + conversation_messages

        # Get response from model
        response = model.invoke(all_messages)

        # Create clean response content
        response_content = str(response.content) if hasattr(response, 'content') else str(response)
        response_content += f"{tind_metadata}" if tind_metadata else ""
        response_messages: list[AnyMessage] = [AIMessage(content=response_content)]
        return {"messages": response_messages}

    def invoke(self,
               init_state: dict,
               config: RunnableConfig) -> dict[str, list[AnyMessage]]:
        """Invoke the graph manager with message_state."""
        return self.app.invoke(init_state, config)

    def update_state(self, config: RunnableConfig, message_state: dict) -> None:
        """Update the state of the graph manager."""
        self.app.update_state(config, message_state)

_GRAPH_MANAGER: Optional[GraphManager] = None
"""Managed, global GraphManager instance."""

def get_graph_manager() -> GraphManager:
    """Get the shared graph manager instance."""
    global _GRAPH_MANAGER  # pylint: disable=global-statement
    if _GRAPH_MANAGER is None:
        _GRAPH_MANAGER = GraphManager()
    return _GRAPH_MANAGER
