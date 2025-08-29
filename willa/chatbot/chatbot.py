"""Implements the Chatbot class for Willa."""

import os
import uuid
from pprint import pprint

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.config import RunnableConfig
from langchain_core.vectorstores.base import VectorStore
from langgraph.checkpoint.memory import MemorySaver
# from langgraph.checkpoint.memory import InMemorySaver
# from langgraph.checkpoint.postgres import PostgresSaver
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

    def __init__(self, vector_store: VectorStore, model: BaseChatModel, thread_id: str = None, conversation_thread: list[dict] = None):
        """Create a new Willa chatbot instance.

        :param VectorStore vector_store: The vector store to use for searching.
        :param BaseChatModel model: The LLM to use for processing.
        :param str thread_id: The ID of the thread for this conversation.
        :param list[dict] conversation_thread: conversation thread from chainlit data_layer
        """
        self.vector_store = vector_store
        self.model = model
        self.thread_id = thread_id or str(uuid.uuid4())
        self.conversation_thread = conversation_thread or []

        #TODO: figure out how to get conversation_thread into state["messages"]

        # Create LangGraph workflow
        workflow = StateGraph(state_schema=MessagesState)
        workflow.add_node("chatbot", self._call_model)
        workflow.add_edge(START, "chatbot")

        memory = MemorySaver()
        self.app = workflow.compile(checkpointer=memory)

        if thread_id:
            self._restore_conversation_history()

    def _restore_conversation_history(self):
        """Restore conversation history for the existing thread_id from data layer."""
        try:
            config: RunnableConfig = {
                "configurable": {"thread_id": self.thread_id}
            }
            
            # Try to get the current state for this thread
            # This will automatically restore any existing conversation history
            # that was previously saved with this thread_id
            current_state = self.app.get_state(config)
            
            if current_state and current_state.values.get("messages"):
                print(f"Restored {len(current_state.values['messages'])} messages for thread {self.thread_id}")
            else:
                print(f"No existing conversation history found for thread {self.thread_id}")
                
        except Exception as e:
            print(f"Warning: Could not restore conversation history for thread {self.thread_id}: {e}")

    def _call_model(self, state: MessagesState):
        """Process the conversation state and generate response."""
        messages = state["messages"]
        # pprint(messages)
        # Get latest human message
        latest_message = messages[-1] if messages else None
        if not latest_message or not hasattr(latest_message, 'content'):
            return {"messages": [AIMessage(content="I'm sorry, I didn't receive a question.")]}

        #TODO: Decide on whether or not to use full conversation history for similarity search...
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
        response_content = response.content + tind_metadata if hasattr(response, 'content') else str(response) + tind_metadata

        return {"messages": [AIMessage(content=response_content)]}

    def ask(self, question: str) -> str:
        """Ask a question of this Willa chatbot instance.

        :param str question: The question to ask.
        :returns str: The answer given by the model.
        """
        config: RunnableConfig = {
            "configurable": {"thread_id": self.thread_id}
        }

        result = self.app.invoke(
            {"messages": [HumanMessage(content=question)]},
            config
        )

        # Return the last AI message in content
        ai_message = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        return ai_message[-1].content if ai_message else "I'm sorry, I couldn't generate a response."
