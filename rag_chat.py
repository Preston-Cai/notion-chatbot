"""
RAG Agent implementation.

Next steps:
1. Finish scraping all pages and add them to vector store.
2. Add feature: decide dynamically retrieval k value and tool call limit based on necessity score
produced by the third-party judge. Must move `create_agent` into the chat loop and create new agents
in real time that shares the same checkpointer, since `create_agent` returns `CompiledGraphState` object,
which cannot be naively mutated.
"""

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_chroma import Chroma

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain.messages import AIMessage
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from big_context import read_big_context
from third_party_judges import judge_tool_necessity

# Edit system prompt here
SYSTEM_PROMPT = """
You are a chatbot that can chat and help.
Big picture context (background info) have been provided to you (e.g. info about our division's current mssion - FINCH).

A tool is given to you to retrive context specific to FINCH and UTAT. Do NOT exploit it unless absolutely necessary.
If the retrieval tool cannot be used because its limit is reached, provide the best possible answer
using only the context already available. Do not leave your response empty.
"""

# Define output schema
class ResponseFormat(BaseModel):
    """Response schema for the llm.
    """
    message: str
        

@tool(description="retrieve context specific to Space Systems division of UTAT")
def retrieve_context(query: str, num_docs: int = 10) -> tuple[str, list[Document]]:
    """
    A function to retrieve domain-specific context. Use it **only when the user's question
    cannot be answer directly from the context already provided**. DO NOT use it for greeting, small talk,
    or something unrelated to the Space Systems division of the UTAT org.

    Args:
        query: Search terms to look for
        num_docs: Maximum number of results to retrieve
    """
    # private docstring (the agent doesn't see)
    # Embed a query, similarity search, and retrieve relevant docs (num_docs many). Parse docs into string. 
    # Return a tuple: a list of docs in langchain's doc object format, and the serialized string.
    
    # For development purpose only
    print("Tool retrieve_context activated.")

    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")

    # Create embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=key)

    # Load chroma database
    vector_store = Chroma(
        collection_name="my_collection",
        embedding_function=embeddings,
        persist_directory="./chroma_langchain_db",
    )

    # Retrieve docs
    docs = vector_store.similarity_search_by_vector(
        embedding=embeddings.embed_query(query), 
        k=num_docs   # Number of docs to return
    )

    # Parse docs
    text = "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}"
        for doc in docs
    )

    # print("Retrieve_context: ", text)

    return text, docs


def chat_loop(retrieve_limit: int = 3) -> None:
    """Activate a chat session for the user.
    retrieve_limit is the maximum number to call the tool `retrieve_context`.
    """

    # Load api key
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")

    # Instantiate model
    model = ChatOpenAI(
        model="gpt-5-nano",
        api_key=key
        )

    # Create agent short term memory
    memory = InMemorySaver()

    # Create two agents, one with the tool, the other with no tool, both sharing the same memory
    agent_with_tool = create_agent(
        model=model,
        checkpointer=memory,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(ResponseFormat),
        middleware=[ToolCallLimitMiddleware(    # limit tool calls
            tool_name="retrieve_context",
            run_limit=retrieve_limit
        )],
        tools=[retrieve_context],
    )

    agent_no_tool = create_agent(
        model=model,
        checkpointer=memory,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(ResponseFormat),
    )
            
    try:
        while True:
            # Ask for user input
            user_prompt = input("$$$ Enter your prompt: ")
            msg = ({"messages": [
                            {"role": "system", "content": f"Big picture context: {read_big_context()}"},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                    {"configurable": {"thread_id": "1"}})
            
            # A third-party LLM to decide whether context retrieval is necessary
            necessary, necessity_score = judge_tool_necessity(user_prompt)
            print("Context retrieval necessity score: ", necessity_score)
            # If so, use the agent with tool. Otherwise, use the agent without tool.
            if necessary:
                agent = agent_with_tool
                print("Switched to agent with tool.")
            else:
                agent = agent_no_tool
                print("Switched to agent without tool.")

          
            # Invoke agent
            result = agent.invoke(*msg)

            # Structured response
            print("----- Bot's Response -----\n", result['structured_response'].message)

            # Hard-coded structured response
            # Warning: First comment out response_format in create_agent!!
            # print("Bot's Response -----\n", 
            #        [entry for entry in result['messages'] 
            #         if isinstance(entry, AIMessage)][-1].content) 
                
            # verbose streaming mode
            # Warning: First comment out response format in create_agent!!
            # for event in agent.stream(
            #     *msg,
            #     stream_mode="values",
            # ):
            #     event["messages"][-1].pretty_print()


    except KeyboardInterrupt:
        print("\n#### Conversation ended ####")

if __name__ == '__main__':
    chat_loop(retrieve_limit=2)