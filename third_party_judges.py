from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
import os

from big_context import read_big_context


class OutputSchema(BaseModel):
    """The output schema of the third-party judge.
    
    Representation Invariants:
      - 0 <= self.necessity_score <= 100
    """
    necessity: bool
    necessity_score: int

def judge_tool_necessity(query: str) -> tuple[bool, int]:
    """
    Given a query, judge whether context retrieval is necessary and how necessary it is.
    """
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")

    model = ChatOpenAI(
            model="gpt-5-nano",
            api_key=key,
            )
    
    structured_model = model.with_structured_output(OutputSchema)
    
    msg = [
        (
            "system",
            "You are a helper assistant for an RAG agent. You job is to judge, "
            "given the user's prompt and the context that the agent already possesses, "
            "whether it's necessary and how necessary it is to retrieve specific information from the Space Systems - UTAT "
            "notion workplace for generation."
        ),
        (
            "system",
            f"This is the context that is already given to the RAG agent: {read_big_context()}"
        ),
        ("system", f"This is the user's prompt: {query}"),
    ]
    
    result = structured_model.invoke(
        input=msg
    )

    print("Necessary?", result.necessity)
    print("How necessary?", result.necessity_score)

    return result.necessity, result.necessity_score


if __name__ == '__main__':
    judge_tool_necessity(input("Enter your query: "))