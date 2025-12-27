from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
import os

from big_context import read_big_context


class OutputSchema(BaseModel):
    """The output schema of the third-party judge."""
    necessity: bool

def judge_tool_necessity(query: str) -> bool:
    """
    Given a query, judge whether context retrieval is necessary.
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
            "whether it's necessary to retrieve the organization's notion pages for generation."
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

    print(result.necessity)

    return result.necessity


if __name__ == '__main__':
    judge_tool_necessity(input("Enter your query: "))