from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_chroma import Chroma

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool

from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Edit system prompt here
SYSTEM_PROMPT = """You are an AI assistant for UTAT (University of Toronto Aerospace Team)
Space Systems division. Your role is to answer user's question about the divison's notion page.
A tool is given to you to retrive relevant context. You probably want to use that tool if anything 
asked is unknown. 
Note that the retrieved text can be very fragmented, so use your own knowledge to complement your answers when needed.
However, DON'T make up specific facts about the internal affairs of the organization. Say it explicitly if you don't know about something.
"""

# Define output schema
class ResponseFormat(BaseModel):
    """Response schema for the llm.
    """
    message: str


@tool(ResponseFormat="content_and_artifact")
def retrive_context(query: str, num_docs: int = 5) -> tuple[str, list[Document]]:
    """
    Embed user query, similarity search, and retrieve relevant docs (num_docs many).
    Parse docs into string. Return a tuple: 
    a list of docs in langchain's doc object format, and the serialized string.
    """
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")

    # Create embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=key)
    print("embeddings created")

    # Load chroma database
    vector_store = Chroma(
        collection_name="my_collection",
        embedding_function=embeddings,
        persist_directory="./chroma_langchain_db",
    )
    print("chroma successfully loaded.")

    # Retrieve docs
    docs = vector_store.similarity_search_by_vector(
        embedding=embeddings.embed_query(query), 
        k=num_docs   # Number of docs to return
    )

    # Parse docs
    text = "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.content}"
        for doc in docs
    )

    print("Retrieve_context: ", text)

    return text, docs


def chat_loop():
    """Activate a chat session for the user."""

    # Load api key
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")

    # Instantiate model
    model = ChatOpenAI(
        model="gpt-5-nano",
        api_key=key
    )

    # Create an agent
    agent = create_agent(
        model=model,
        checkpointer=InMemorySaver(),  # Create agent short term memory
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(ResponseFormat),
        tools=[retrive_context]
    )

    try:
        while True:
            # Ask for user input
            user_prompt = input("Enter your prompt: ")

            # Invoke agent
            result = agent.invoke(
                {
                    "messages": [
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": notion_text},
                    ],
                },
                {"configurable": {"thread_id": "1"}}
            )

            print("ChatGPT's Response: ", result['structured_response'].message)
    except KeyboardInterrupt:
        print("Conversation ended.")