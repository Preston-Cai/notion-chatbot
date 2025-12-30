"""
RAG Agent implementation.
"""

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_chroma import Chroma

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain.messages import AIMessage
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import Optional
from pprint import pprint

from src.utils.big_context import read_big_context
from src.utils.third_party_judges import judge_tool_necessity
from src.file_config import DB_DIR

# Edit system prompt here
SYSTEM_PROMPT = """
You are a chatbot that can chat and help.
Big picture context (background info) have been provided to you (e.g. info about our division's current mssion - FINCH).

A tool might be available (or maybe not) to retrive context specific to FINCH and UTAT. Do NOT exploit it unless absolutely necessary.
If the retrieval tool cannot be used because its limit is reached, stop calling the tool,
provide the best possible answer using only the context already available.

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
    """
    
    # Private Instance Attributes
    #   - _compiled_agents: a list of compiled agents created by `create_agent`
    #   - _checkpointer: memory checkpointer that the agents and third-party judges will share
    retrieve_limit: int = 3
    _compiled_agents: list[CompiledStateGraph]
    _check_pointer: InMemorySaver
    
    def __init__(self, retrieve_limit: int = 3) -> None:
        self.retrieve_limit = retrieve_limit
        self._compiled_agents = []
        self._check_pointer = InMemorySaver()
    
    @staticmethod
    @tool(description="retrieve context specific to Space Systems division of UTAT")
    def _retrieve_context(query: str, num_docs: int = 10) -> tuple[str, list[Document]]:
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
        
        print("Tool called: _retrieve_context")

        load_dotenv()
        key = os.environ.get("OPENAI_API_KEY")

        # Create embeddings
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=key)

        # Load chroma database
        vector_store = Chroma(
            collection_name="my_collection",
            embedding_function=embeddings,
            persist_directory=DB_DIR,
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
        
        # For debugging/development only
        # print("First document: ", docs[0])
        # print("Retrieve_context: ", text)

        return text, docs
    
    def _instantiate_agents(self, model_name: str = "gpt-4o") -> None:
        """Populate self._compiled_agents with available opitons.
        model_name specifies the model to use to create agents.
        
        Preconditions:
          - model_name must be a valid OpenAI LLM model name. Visit
          https://platform.openai.com/docs/pricing for a list of models.
        """    
        # Load api key
        load_dotenv()
        key = os.environ.get("OPENAI_API_KEY")

        # Instantiate model
        model = ChatOpenAI(
            model=model_name,
            api_key=key
            )

        # Create two agents, one with the tool, the other with no tool, both sharing the same memory
        agent_with_tool = create_agent(
            model=model,
            checkpointer=self._check_pointer,
            system_prompt=SYSTEM_PROMPT,
            response_format=ToolStrategy(ResponseFormat),
            middleware=[ToolCallLimitMiddleware(    # limit tool calls
                tool_name="_retrieve_context",
                run_limit=self.retrieve_limit
            )],
            tools=[self._retrieve_context],
        )

        agent_no_tool = create_agent(
            model=model,
            checkpointer=self._check_pointer,
            system_prompt=SYSTEM_PROMPT,
            response_format=ToolStrategy(ResponseFormat),
        )

        self._compiled_agents.extend([agent_with_tool, agent_no_tool])

    def simulate_chat_loop(self, debug: bool = False) -> None:
        """Simulate a chat session for the user.
        Enable debug will stream all updates of the agent,
        except ones with step `tools` (to prevent printing long retrieved docs).
        """      
        try:
            while True:
                # Ask for user input
                user_prompt = input("---> Enter your prompt: ")
                msg = ({"messages": [
                                {"role": "system", "content": f"Big picture context: {read_big_context()}"},
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                        {"configurable": {"thread_id": "1"}})
                
                # A third-party LLM to decide whether context retrieval is necessary
                necessary, necessity_score = judge_tool_necessity(user_prompt, self._check_pointer)
                print("Context retrieval necessity score:", necessity_score)
                # If so, use the agent with tool. Otherwise, use the agent without tool.
                if necessary:
                    agent = self._compiled_agents[0]
                    print("Switched to agent with tool.")
                else:
                    agent = self._compiled_agents[1]
                    print("Switched to agent without tool.")

                if not debug:
                    # Invoke agent
                    result = agent.invoke(*msg)
                    
                    # Structured response
                    print('-' * 30 + " Bot's Response " + '-' * 30 + "----\n", 
                        result['structured_response'].message)
                    print('-' * 30 + " Sources " + '-' * 30 + "----\n", 
                        result['structured_response'].sources)
                    
                # verbose streaming mode (for debugging)
                else:
                    for chunk in agent.stream(
                        *msg,
                        stream_mode="updates",
                    ):
                        for step, data in chunk.items():
                            if step != "tools": 
                                print(f"step: {step}")
                                print(f"chunk data: {pprint(data)}")

        except KeyboardInterrupt:
            print("\n#### Conversation Ended ####")
            
    def get_response(self, prompt: str) -> ResponseFormat:
        """Get bot's structured response given a user prompt."""
        msg = ({"messages": [
                                {"role": "system", "content": f"Big picture context: {read_big_context()}"},
                                {"role": "user", "content": prompt},
                            ],
                        },
                        {"configurable": {"thread_id": "1"}})
                
        # A third-party LLM to decide whether context retrieval is necessary
        necessary, necessity_score = judge_tool_necessity(prompt, self._check_pointer)
        print("Context retrieval necessity score:", necessity_score)
        # If so, use the agent with tool. Otherwise, use the agent without tool.
        if necessary:
            agent = self._compiled_agents[0]
            print("Switched to agent with tool.")
        else:
            agent = self._compiled_agents[1]
            print("Switched to agent without tool.")

        # Invoke agent
        result = agent.invoke(*msg)
        
        return result.get("structured_response")

if __name__ == '__main__':
    chatbot = RAGChat(retrieve_limit=2)
    chatbot._instantiate_agents(model_name="gpt-4o")
    
    chatbot.simulate_chat_loop(debug=True)
    
    # response = chatbot.get_response("Hello")
    # print(response.message)