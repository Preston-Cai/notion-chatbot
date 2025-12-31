"""
experiement with native chroma

see how to make chroma db recognize langchain chroma db directory and open it,
rather than craeting one.

Result: probably doesn't recognize. must create one from scratch.
"""

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_chroma import Chroma
import chromadb

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain.messages import AIMessage
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import Optional

from src.utils.big_context import read_big_context
from src.utils.third_party_judges import judge_tool_necessity
from src.file_config import DB_DIR

# Edit system prompt here
SYSTEM_PROMPT = """
You are a chatbot that can chat and help.
Big picture context (background info) have been provided to you (e.g. info about our division's current mssion - FINCH).

A tool might be available (or maybe not) to retrive context specific to FINCH and UTAT. Do NOT exploit it unless absolutely necessary.
If the retrieval tool cannot be used because its limit is reached, provide the best possible answer
using only the context already available. Do not leave your response empty.

You can choose to provide URL sources in your answer or leave sources field as None.
"""

# Define output schema
class ResponseFormat(BaseModel):
    """Response schema for the LLM.
    Instance attributes:
      - message: LLM's final message output.
      - sources: URL sources of the retrieve context that contributed to the final response.
    """
    message: str
    sources: Optional[list[str]]
        

class RAGChat:
    """An RAG Chatbot.
    
    Instance Attributes:
      - retrieve_limit: the maximum number to call the tool `retrieve_context`.
      - seen_ids: document ids that have been retrieved in previous runs under a single chat session.
      
    """
    retrieve_limit: int = 2
    seen_ids: set
    
    def __init__(self, retrieve_limit: int = 2) -> None:
        self.retrieve_limit = retrieve_limit
        self.seen_ids = set()
    
    @staticmethod
    # @tool(description="retrieve context specific to Space Systems division of UTAT")
    def retrieve_context(query: str, num_docs: int = 10) -> tuple[str, list[Document]]:
        """
        Retrieve domain-specific context from ChromaDB. Only for Space Systems division questions.
        """
        print("Tool called: retrieve_context")

        load_dotenv()
        key = os.environ.get("OPENAI_API_KEY")

        # Create OpenAI embedding function for ChromaDB
        from chromadb.utils import embedding_functions
        embed_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=key,
            model_name="text-embedding-3-small"
        )

        import chromadb
        from chromadb.config import Settings


        client = chromadb.Client(Settings(
                                    persist_directory=str(DB_DIR)
                                ))

    
        collection = client.get_collection(name="my_collection")

        # Query ChromaDB for nearest neighbors
        results = collection.query(
            query_texts=[query],
            n_results=num_docs
        )
        print("retrieved results: ", results)

        # ChromaDB returns lists of lists; wrap results into LangChain Document objects
        docs = [
            Document(
                page_content=doc_text,
                metadata=metadata
            )
            for doc_text, metadata in zip(results["documents"][0], results["metadatas"][0])
        ]

        # Serialize to a single string
        text = "\n\n".join(
            f"Source: {doc.metadata}\nContent: {doc.page_content}"
            for doc in docs
        )
        
        print("Retrieved:", text)

        return text, docs


    def chat_loop(self) -> None:
        """Activate a chat session for the user.
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
                run_limit=self.retrieve_limit
            )],
            tools=[self.retrieve_context],
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
                user_prompt = input(">>>> Enter your prompt: ")
                msg = ({"messages": [
                                {"role": "system", "content": f"Big picture context: {read_big_context()}"},
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                        {"configurable": {"thread_id": "1"}})
                
                # A third-party LLM to decide whether context retrieval is necessary
                necessary, necessity_score = judge_tool_necessity(user_prompt, memory)
                print("Context retrieval necessity score:", necessity_score)
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
                print('-' * 35 + " Bot's Response " + '-' * 35 + "----\n", 
                    result['structured_response'].message)
                print('-' * 35 + " Sources " + '-' * 35 + "----\n", 
                    result['structured_response'].sources)

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
            print("\n#### Conversation Ended ####")

if __name__ == '__main__':
    chatbot = RAGChat()
    chatbot.retrieve_context("hello world")