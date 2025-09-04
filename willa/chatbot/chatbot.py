"""Implements the Chatbot class for Willa."""

import os
import uuid
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.config import RunnableConfig
from langchain_core.vectorstores.base import VectorStore
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph

import willa.config  # pylint: disable=W0611
from willa.tind import format_tind_context

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
        workflow = StateGraph(state_schema=MessagesState)
        workflow.add_node("chatbot", self._call_model)
        workflow.add_edge(START, "chatbot")

        memory = InMemorySaver()
        self.app = workflow.compile(checkpointer=memory)

        if self.previous_conversation:
            self._initialize_conversation_state()

    def _initialize_conversation_state(self) -> None:
        """Initialize conversation state with the existing messages from the data layer."""
        self.app.update_state(self.config, {"messages": self.previous_conversation})
        print(f"Initialized conversation with {len(self.previous_conversation)} messages "
              f"for thread {self.thread_id}")

    def _call_model(self, state: MessagesState) -> dict:
        """Process the conversation state and generate response."""
        messages = state["messages"]
        # pprint(messages)
        # Get latest human message
        latest_message = messages[-1] if messages else None
        if not latest_message or not hasattr(latest_message, 'content'):
            return {"messages": [AIMessage(content="I'm sorry, I didn't receive a question.")]}

        #TODO: Decide on whether or not to use full conversation history for similarity search... # pylint: disable=W0511
        # Search for relevant context
        matching_docs = self.vector_store.similarity_search(latest_message.content)
        tind_metadata = format_tind_context.get_tind_context(matching_docs)
        context = '\n\n'.join(doc.page_content for doc in matching_docs)

        # Format the prompt with context and question
        formatted_messages = PROMPT.format_messages(
            question=latest_message.content,
            context=context
        )

        # Combine system prompt with conversation history
        all_messages = formatted_messages + messages

        # Get response from model
        response = self.model.invoke(all_messages)

        # Add TIND metadata to response
        response_content = (response.content + tind_metadata
                          if hasattr(response, 'content')
                          else str(response) + tind_metadata)

        # TODO: remove TIND metadata from the content and have it be a system message # pylint: disable=W0511
        return {"messages": [AIMessage(content=response_content)]}

    def ask(self, question: str) -> str:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns str: The answer given by the model.
        """

        result = self.app.invoke(
            {"messages": [HumanMessage(content=question)]},
            self.config
        )

        # Return the last AI message in content
        ai_message = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if ai_message:
            return ai_message[-1].content
        return "I'm sorry, I couldn't generate a response."
