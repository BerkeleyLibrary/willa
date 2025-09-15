"""Manages the shared state and workflow for Willa chatbots."""
from typing import Any, Optional, Annotated, NotRequired
from typing_extensions import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ChatMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.vectorstores.base import VectorStore
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import AnyMessage
from langmem.short_term import SummarizationNode # type: ignore

from willa.config import CONFIG, get_lance, get_model
from willa.tind import format_tind_context

with open(CONFIG['PROMPT_TEMPLATE'], encoding='utf-8') as f:
    _SYS_PROMPT: str = f.read()
    """The system prompt text."""


class WillaChatbotState(TypedDict):
    """State for the Chatbot LangGraph workflow."""
    messages: Annotated[list[AnyMessage], add_messages]
    filtered_messages: NotRequired[list[AnyMessage]]
    summarized_messages: NotRequired[list[AnyMessage]]
    docs_context: NotRequired[str]
    search_query: NotRequired[str]
    tind_metadata: NotRequired[str]
    context: NotRequired[dict[str, Any]]


class GraphManager:  # pylint: disable=too-few-public-methods
    """Manages the shared LangGraph workflow for all chatbot instances."""

    def __init__(self) -> None:
        self.memory = InMemorySaver()
        self._vector_store: Optional[VectorStore] = get_lance()
        self._model: Optional[BaseChatModel] = get_model()
        self.app = self._create_workflow()

    def _create_workflow(self) -> CompiledStateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(state_schema=WillaChatbotState)

        # summarization node assumes same model as chat response generation
        summarization_node = SummarizationNode(max_tokens=int(CONFIG.get('MAX_TOKENS', '500')),
                                               model=self._model,
                                               input_messages_key="filtered_messages",
                                               output_messages_key="summarized_messages")

        # Add nodes
        workflow.add_node("filter_messages", self._filter_messages)
        workflow.add_node("summarize", summarization_node)
        workflow.add_node("prepare_search", self._prepare_search_query)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges
        workflow.add_edge(START, "filter_messages")
        workflow.add_edge("filter_messages", "summarize")
        workflow.add_edge("summarize", "prepare_search")
        workflow.add_edge("prepare_search", "retrieve_context")
        workflow.add_edge("retrieve_context", "generate_response")

        return workflow.compile(checkpointer=self.memory)

    def _filter_messages(self, state: WillaChatbotState) -> dict[str, list[AnyMessage]]:
        """Filter out TIND messages from the conversation history."""
        messages = state["messages"]

        filtered = [msg for msg in messages if 'tind' not in msg.response_metadata]
        return {"filtered_messages": filtered}

    def _prepare_search_query(self, state: WillaChatbotState) -> dict[str, str]:
        """Prepare search query from conversation context."""
        messages = (state["summarized_messages"]
               if state.get("summarized_messages")
               else state["messages"])

        # summarization may include a system message as well as any human or ai messages
        search_query = '\n'.join(str(msg.content) for msg in messages if hasattr(msg, 'content'))
        return {"search_query": search_query}

    def _retrieve_context(self, state: WillaChatbotState) -> dict[str, str]:
        """Retrieve relevant context from vector store."""
        search_query = state.get("search_query", "")
        vector_store = self._vector_store

        if not search_query or not vector_store:
            return {"docs_context": "", "tind_metadata": ""}

        # Search for relevant documents
        matching_docs = vector_store.similarity_search(search_query)

        # Format context and metadata
        docs_context = '\n\n'.join(doc.page_content for doc in matching_docs)
        tind_metadata = format_tind_context.get_tind_context(matching_docs)

        return {"docs_context": docs_context, "tind_metadata": tind_metadata}

    def _generate_response(self, state: WillaChatbotState) -> dict[str, list[AnyMessage]]:
        """Generate response using the model."""
        messages = state["messages"]
        summarized_conversation = state.get("summarized_messages", messages)
        docs_context = state.get("docs_context", "")
        tind_metadata = state.get("tind_metadata", "")
        model = self._model

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
            context=docs_context,
            question=latest_message.content
        ))

        # Combine system prompt with summarized conversation history
        all_messages = summarized_conversation + [system_message]

        # Get response from model
        response = model.invoke(all_messages)

        # Create clean response content
        response_content = str(response.content) if hasattr(response, 'content') else str(response)
        response_messages: list[AnyMessage] = [AIMessage(content=response_content),
                                               ChatMessage(content=tind_metadata, role='TIND',
                                                           response_metadata={'tind': True})]
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
