"""Manages the shared state and workflow for Willa chatbots."""
from typing import Any, Optional, Annotated, NotRequired
from typing_extensions import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ChatMessage, HumanMessage, AIMessage
from langchain_core.vectorstores.base import VectorStore
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import AnyMessage
from langmem.short_term import SummarizationNode # type: ignore
from willa.config import CONFIG, get_lance, get_model, get_langfuse_prompt
from willa.tind import format_tind_context

class WillaChatbotState(TypedDict):
    """State for the Chatbot LangGraph workflow."""
    messages: Annotated[list[AnyMessage], add_messages]
    filtered_messages: NotRequired[list[AnyMessage]]
    summarized_messages: NotRequired[list[AnyMessage]]
    search_query: NotRequired[str]
    tind_metadata: NotRequired[str]
    documents: NotRequired[list[Any]]


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
        summarization_node = SummarizationNode(
            max_tokens=int(CONFIG['SUMMARIZATION_MAX_TOKENS']),
            model=self._model,
            input_messages_key="filtered_messages",
            output_messages_key="summarized_messages"
        )

        # Add nodes
        workflow.add_node("filter_messages", self._filter_messages)
        workflow.add_node("summarize", summarization_node)
        workflow.add_node("prepare_search", self._prepare_search_query)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("prepare_for_generation", self._prepare_for_generation)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges
        workflow.add_edge("filter_messages", "summarize")
        workflow.add_edge("summarize", "prepare_search")
        workflow.add_edge("prepare_search", "retrieve_context")
        workflow.add_edge("retrieve_context", "prepare_for_generation")
        workflow.add_edge("prepare_for_generation", "generate_response")

        workflow.set_entry_point("filter_messages")
        workflow.set_finish_point("generate_response")

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

        # if summarization fails or some other issue, truncate to the last 2048 characters
        if len(search_query) > 2048:
            search_query = search_query[-2048:]

        return {"search_query": search_query}

    def _retrieve_context(self, state: WillaChatbotState) -> dict[str, str | list[Any]]:
        """Retrieve relevant context from vector store."""
        search_query = state.get("search_query", "")
        vector_store = self._vector_store

        if not search_query or not vector_store:
            return {"tind_metadata": "", "documents": []}

        # Search for relevant documents
        retriever = vector_store.as_retriever(search_kwargs={"k": int(CONFIG['K_VALUE'])})
        matching_docs = retriever.invoke(search_query)
        formatted_documents = [
            {
                "id": f"{i}_{doc.metadata.get('tind_metadata', {}).get('tind_id', [''])[0]}",
                "page_content": doc.page_content,
                "title": doc.metadata.get('tind_metadata', {}).get('title', [''])[0],
                "project": doc.metadata.get('tind_metadata', {}).get('isPartOf', [''])[0],
                "tind_link": format_tind_context.get_tind_url(
                    doc.metadata.get('tind_metadata', {}).get('tind_id', [''])[0])
            }
            for i, doc in enumerate(matching_docs, 1)
        ]

        # Format tind metadata
        tind_metadata = format_tind_context.get_tind_context(matching_docs)

        return {"tind_metadata": tind_metadata, "documents": formatted_documents}

    def _prepare_for_generation(self, state: WillaChatbotState) -> dict[str, list[AnyMessage]]:
        """Prepare the current and past messages for response generation."""
        messages = state["messages"]
        summarized_conversation = state.get("summarized_messages", messages)

        if not any(isinstance(msg, HumanMessage) for msg in messages):
            return {"messages": [AIMessage(content="I'm sorry, I didn't receive a question.")]}

        prompt = get_langfuse_prompt()
        system_messages = prompt.invoke({})

        if hasattr(system_messages, "messages"):
            all_messages = summarized_conversation + system_messages.messages
        else:
            all_messages = summarized_conversation + [system_messages]

        return {"messages": all_messages}

    def _generate_response(self, state: WillaChatbotState) -> dict[str, list[AnyMessage]]:
        """Generate response using the model."""
        tind_metadata = state.get("tind_metadata", "")
        model = self._model
        documents = state.get("documents", [])
        messages = state["messages"]

        if not model:
            return {"messages": [AIMessage(content="Model not available.")]}

        # Get response from model
        response = model.invoke(
            messages,
            additional_model_request_fields={"documents": documents}
            )

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


_GRAPH_MANAGER: Optional[GraphManager] = None  # pylint: disable=invalid-name
"""Managed, global GraphManager instance."""


def get_graph_manager() -> GraphManager:
    """Get the shared graph manager instance."""
    global _GRAPH_MANAGER  # pylint: disable=global-statement
    if _GRAPH_MANAGER is None:
        _GRAPH_MANAGER = GraphManager()
    return _GRAPH_MANAGER
