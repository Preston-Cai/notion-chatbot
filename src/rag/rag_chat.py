"""
RAG Agent implementation.
"""

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_chroma import Chroma

from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import ToolCallLimitMiddleware, after_model, SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain.messages import AIMessage, RemoveMessage, ToolMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import Optional
from pprint import pprint

from src.utils.big_context import read_big_context
from src.utils.third_party_judges import judge_tool_necessity
from src.file_config import DB_DIR

# Edit system prompt here
SYSTEM_PROMPT = f"""
You are a chatbot that can chat and help.
Any message starting with the sentence "Here is a summary of the conversation to date" 
is not the user's real question, and should be treated as context.

A tool is given to you to retrive context specific to FINCH and UTAT (UofT Aerospace Team).
Only use it when necessary (i.e. can't answer the question without further context).

There is a tool call limit for each "user message → response" cycle. 
If a message displays "Tool call limit exceeded. Do not call '_retrieve_context' again",
stop calling that tool for that cycle.
However, that limit is reset for the next cycle, so you are free to use it for a different user prompt.

You can choose to provide URL sources in your answer or leave sources field as None.

Here is the big-picture context (background info, e.g. info about our division's current mssion - FINCH): 
{read_big_context()}
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
    retrieve_limit: int = 2
    _compiled_agents: list[CompiledStateGraph]
    _check_pointer: InMemorySaver
    
    def __init__(self, retrieve_limit: int = 2) -> None:
        self.retrieve_limit = retrieve_limit
        self._compiled_agents = []
        self._check_pointer = InMemorySaver()
    
    @staticmethod
    @after_model
    def _log_history(state: AgentState, runtime: Runtime) -> dict | None:
        """Log two pieces of info from the graph state:
          - current message history statistics, and
          - the last 4 LLM API calls input tokens
          
        This helps monitor summarization middleware behavior and request sizes.
        """
        print("middleware used: _log_messages.")
        messages = state["messages"]
        
        print("------ Message History Stats ------")
        print("Number of messages:", len(messages))
        # print("Msg types:", [type(msg) for msg in messages])
        
        # # For debugging only
        # print("Content of messages so far:")
        # for msg in messages:
        #     print(f"{type(msg)} === {msg.content}")
        
        print("Last 5 LLM API calls input tokens:", 
              [AI_msg.usage_metadata.get("input_tokens") for AI_msg in messages 
               if isinstance(AI_msg, AIMessage)][-5:])
   
    @staticmethod
    @tool(description="retrieve context specific to Space Systems division of UTAT")
    def _retrieve_context(query: str, num_docs: int = 5) -> tuple[str, list[Document]]:
        """
        A function to retrieve domain-specific context. Use it **only when the user's question
        cannot be answer directly from the context already provided**. DO NOT use it for greeting, small talk,
        or something unrelated to the Space Systems division of the UTAT org.

        Args:
            query: Search terms to look for
            num_docs: Maximum number of results to retrieve
        """
        # Private docstring (the agent doesn't see)
        # Embed a query, similarity search, and retrieve relevant docs (num_docs many). Parse docs into string. 
        # Return a tuple: a list of docs in langchain's doc object format, and the serialized string.
        
        print("Tool called: _retrieve_context; called value: k =", num_docs)

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
        
        print("Total number of characters in retrieved text:", len(text))

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
        
        # Middleware: summarize old messages
        summarizer = SummarizationMiddleware(
            model="gpt-4o",
            trigger=[
                ("tokens", 8000),  # safe for my gpt-4o rate limit: 30,000 tpm
                ("fraction", 0.8)  # 80% of context window
            ],
            keep=("tokens", 500),
        )
        
        # Middleware: limit tool calls
        tool_call_limiter = ToolCallLimitMiddleware(
            tool_name="_retrieve_context",
            run_limit=self.retrieve_limit,
        )

        agent_with_tool = create_agent(
            model=model,
            checkpointer=self._check_pointer,
            system_prompt=SYSTEM_PROMPT,
            response_format=ToolStrategy(ResponseFormat),
            middleware=[
                tool_call_limiter,
                summarizer,
                self._log_history  # See messsage history and input tokens
            ],
            tools=[self._retrieve_context],
        )

        # agent_no_tool = create_agent(
        #     model=model,
        #     checkpointer=self._check_pointer,
        #     system_prompt=SYSTEM_PROMPT,
        #     response_format=ToolStrategy(ResponseFormat),
        #     middleware=[
        #         # self._delete_old_messages,  # delete early messages
        #         summarizer,     # Summarize old messages
        #         self._log_history  # See current messsage history

        #     ],
        # )

        self._compiled_agents.extend([agent_with_tool,
                                    #   agent_no_tool,
                                      ])

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
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                        {"configurable": {"thread_id": "1"}})
                
                print("User message:", user_prompt)
                
                print("Note: Third-party judges disabled. Default to agent with tool.")
                agent = self._compiled_agents[0]

                if not debug:
                    # Invoke agent
                    response = agent.invoke(*msg).get("structured_response")
                    
                    parts = [
                        response.message,
                    ]
                    # Properly print links
                    if response.sources is not None:
                        parts.append('\n' + '-' * 50 + " Sources " + '-' * 50)
                        parts.extend(response.sources)
                    result = '\n'.join(parts)
                    print(result)
                    
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
                                {"role": "user", "content": prompt},
                            ],
                        },
                        {"configurable": {"thread_id": "1"}})
        
        print("User message:", prompt)
                
        # # A third-party LLM to decide whether context retrieval is necessary
        # necessary, necessity_score = judge_tool_necessity(prompt, self._check_pointer)
        # print("Context retrieval necessity score:", necessity_score)
        # # If so, use the agent with tool. Otherwise, use the agent without tool.
        # if necessary:
        #     agent = self._compiled_agents[0]
        #     print("Switched to agent with tool.")
        # else:
        #     agent = self._compiled_agents[1]
        #     print("Switched to agent without tool.")

        print("Note: Third-party judges disabled. Default to agent with tool.")
        agent = self._compiled_agents[0]
        
        # Invoke agent
        response = agent.invoke(*msg).get("structured_response")
        
        return response

if __name__ == '__main__':
    chatbot = RAGChat(retrieve_limit=2)
    chatbot._instantiate_agents(model_name="gpt-4o")
    
    chatbot.simulate_chat_loop(debug=False)
    
    # response = chatbot.get_response("Hello")
    # print(response.message)