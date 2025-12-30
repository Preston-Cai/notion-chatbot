"""
Third-party independent judges to facilitate the main RAG and enforce reliable decision making.
"""

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
from langchain.agents import create_agent

from dotenv import load_dotenv
from pydantic import BaseModel
import os

from src.utils.big_context import read_big_context


SYSTEM_PROMPT = """You are a helper assistant for an RAG agent. You job is to judge, given the user's prompt 
and the context that the agent already possesses, whether it's necessary and how necessary 
it is to retrieve specific information from the Space Systems - UTAT notion workplace for generation.
"""

class OutputSchema(BaseModel):
    """The output schema of the third-party judge.
    
    Representation Invariants:
      - 0 <= self.necessity_score <= 100
    """
    necessity: bool
    necessity_score: int

def judge_tool_necessity(query: str, memory: InMemorySaver) -> tuple[bool, int]:
    """
    Given a query, independently judge whether context retrieval is necessary and how necessary it is.
    
    Preconditions:
      - memory should be the same memory object that the main RAG agent is using.
    """
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")

    model = ChatOpenAI(
        model="gpt-4o",
        api_key=key
    )
    
    judge = create_agent(
        model=model,
        checkpointer=memory,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(OutputSchema),
    )
    
    msg = ({"messages": [
                            {"role": "system", "content": f"""This is the context that is
                             already given to the RAG agent: {read_big_context()}"""},
                            {"role": "system", "content": f"This is the user's prompt: {query}"},
                        ],
                    }, 
           {"configurable": {"thread_id": "2"}})    # Cannot have the same thread_id as the main RAG agent
                                                    # Otherwise, there will be conflict in response.
    
    result = judge.invoke(*msg)["structured_response"]

    print("Context retrieval necessary?", result.necessity)
    print("How necessary?", result.necessity_score)

    return result.necessity, result.necessity_score


if __name__ == '__main__':
    judge_tool_necessity(input("Enter your query: "), memory=InMemorySaver())